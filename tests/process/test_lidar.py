from camille.core import sample_pos
from datetime import datetime, timedelta
from hypothesis import given, settings
from hypothesis.strategies import builds, floats, integers
from itertools import count
from math import acos, atan2, cos, pi, radians, sin, tan
from pytest import approx
from pytz import utc
import camille
import numpy as np
import pandas as pd


elevation = list(map(radians, [5.0, 5.0, -5.0, -5.0]))
telescope = list(map(radians, [-15.0, 15.0, -15.0, 15.0]))
zenith  = [acos(cos(e) * cos(t)) for e, t in zip(elevation, telescope)]
azimuth = [atan2(sin(e), tan(t)) for e, t in zip(elevation, telescope)]
lidar_hgt = 100


class lidar_simulator:
    def __init__(self, pitch=0, roll=0, surge=0, heave=0,
                 surge_velocity=0, sway_velocity=0, heave_velocity=0,
                 pitch_velocity=0, roll_velocity=0, yaw_velocity=0):
        self.pitch = pitch
        self.roll = roll
        self.surge = surge
        self.heave = heave
        self.surge_velocity = surge_velocity
        self.sway_velocity = sway_velocity
        self.heave_velocity = heave_velocity
        self.pitch_velocity = pitch_velocity
        self.roll_velocity = roll_velocity
        self.yaw_velocity = yaw_velocity

    def __call__(self, windfield, timestamp, distance, beam):
        d = distance / cos(zenith[beam])
        zn = zenith[beam]
        az = azimuth[beam]
        p = self.pitch
        r = self.roll
        surge = self.surge
        heave = self.heave

        T_local = np.array([[1, 0, 0,         0],
                            [0, 1, 0,         0],
                            [0, 0, 1, lidar_hgt],
                            [0, 0, 0,         1]])
        R_world = np.array([[cos(p),  sin(p) * sin(r), -sin(p) * cos(r), 0],
                            [     0,           cos(r),           sin(r), 0],
                            [sin(p), -cos(p) * sin(r),  cos(p) * cos(r), 0],
                            [     0,                0,                0, 1]])
        T_world = np.array([[1, 0, 0, surge],
                            [0, 1, 0,     0],
                            [0, 0, 1, heave],
                            [0, 0, 0,     1]])
        Transform = T_world @ R_world @ T_local

        L = np.array([cos(zn),
                      sin(zn) * cos(az),
                      sin(zn) * sin(az),
                      0])
        P = d * L + np.array([0, 0, 0, 1])

        line_of_sight_direction = Transform @ L
        measurement_position = Transform @ P

        I = np.array([self.surge_velocity, self.sway_velocity,
                      self.heave_velocity])

        Iw = -np.cross(np.array([self.roll_velocity,
                                 self.pitch_velocity,
                                 self.yaw_velocity]),
                       np.array([measurement_position[0],
                                 measurement_position[1],
                                 measurement_position[2]]))
        # Sanity check
        _ = sample_pos(lidar_hgt, distance, heave, surge, p, r, az, zn)

        assert measurement_position[0] == approx(_[0])
        assert measurement_position[1] == approx(_[1])
        assert measurement_position[2] == approx(_[2])

        _, wnd = windfield(measurement_position, inertial_frame=I + Iw)
        rws = np.dot(-wnd, line_of_sight_direction[:3])

        status = 1
        return (timestamp, beam, rws, status, self.surge, self.heave,
                self.pitch, self.roll, self.surge_velocity, self.sway_velocity,
                self.heave_velocity, self.pitch_velocity, self.roll_velocity,
                self.yaw_velocity)

    def __repr__(self):
        return (f'lidar_simulator(surge={self.surge}, heave={self.heave}, '
                f'pitch={self.pitch}, roll={self.roll}, '
                f'surge_velocity={self.surge_velocity}, '
                f'sway_velocity={self.sway_velocity}, '
                f'heave_velocity={self.heave_velocity}, '
                f'pitch_velocity={self.pitch_velocity}, '
                f'roll_velocity={self.roll_velocity}, '
                f'yaw_velocity={self.yaw_velocity})')


class windfield_function:
    def __init__(self, direction, ref_speed, shear=0.0, veer=0.0):
        self.direction = direction
        self.ref_speed = ref_speed
        self.shear = shear
        self.veer = veer

    def __call__(self, pnt, inertial_frame=None):
        hgt = pnt[2]
        spd = self.ref_speed * pow(hgt / lidar_hgt, self.shear)
        veer_offset = self.veer * (lidar_hgt - hgt)
        R = np.array([[cos(veer_offset), sin(veer_offset),  0],
                      [-sin(veer_offset), cos(veer_offset), 0],
                      [                0,                0, 1]])
        V = R @ self.direction * spd
        if inertial_frame is not None:
            # The wind vector is negative from the lidar's point of view.
            inertial_frame = -inertial_frame
            V -= inertial_frame
        return spd, V

    def __repr__(self):
        return (
            'windfield_function(direction={}, ref_speed={}, shear={}, veer={})'
            .format(
                self.direction,
                self.ref_speed,
                self.shear,
                self.veer,
        ))

    def yaw_direction(self):
        return atan2(-self.direction[1], -self.direction[0])


def generate_input(windfield,
                   lidar,
                   distance,
                   n=4,
                   start_date=datetime(2030, 1, 1, 12, tzinfo=utc)):
    df = pd.DataFrame(columns=[
        'los_id', 'radial_windspeed', 'status', 'surge', 'heave', 'pitch',
        'roll', 'surge_velocity', 'sway_velocity', 'heave_velocity',
        'pitch_velocity', 'roll_velocity', 'yaw_velocity'
    ])

    time = (start_date + timedelta(seconds=1) * i for i in range(n))
    beam = (i % 4 for i in count())
    for t, b in zip(time, beam):
        timestamp, *xs = lidar(windfield, t, distance, b)
        df.loc[timestamp] = xs
    return distance, windfield, lidar, df


def uniform_dir(alpha):
    return np.array([-cos(alpha), sin(alpha), 0.0])


distances = integers(min_value=50, max_value=400)
directions = builds(uniform_dir, floats(min_value=-pi / 4, max_value=pi / 4))
angles = floats(min_value=-0.0872665, max_value=0.0872665)
windspeeds = floats(min_value=0.5, max_value=18.0)
shears = floats(min_value=0.143 / 2, max_value=0.143 * 2)
veers = floats(min_value=-0.0314159, max_value=0.0314159)  # +- 1.8 deg / m
heaves = floats(min_value=-30.0, max_value=30.0)
surges = floats(min_value=-30.0, max_value=30.0)
velocities = floats(min_value=-5.0, max_value=5.0)
angular_velocities = floats(min_value=-5.0, max_value=5.0)


def windfields(directions, windspeeds, **kwargs):
    return builds(windfield_function, directions, windspeeds, **kwargs)


def lidars(**kwargs):
    return builds(lidar_simulator, **kwargs)


def processor_inputs(lidars, windfields):
    return builds(generate_input, windfields, lidars, distances)


def process_with_args(dist, df):
    out = camille.lidar.windfield_desc(df, dist, lidar_hgt, 0)
    out['speed'] = out.speed_lwr
    out['dir'] = out.dir_lwr
    out['height'] = out.height_lwr
    out['hws'] = camille.lidar.extrapolate_windspeed(out, lidar_hgt)
    out['hwd'] = camille.lidar.extrapolate_winddirection(out, lidar_hgt)
    return out


def scenario(case,
             ref_speed=lambda windfield, *args, **kwargs:
                 approx(windfield(*args, **kwargs)[0]),
             ref_direction=lambda windfield:
                 approx(windfield.yaw_direction()),
             ref_shear=lambda windfield: approx(windfield.shear),
             ref_veer=lambda windfield: approx(windfield.veer)):
    @given(case)
    @settings(deadline=None, print_blob=True)
    def test(args):
        dist, windfield, _, df = args
        processed = process_with_args(dist, df)

        p = np.array([dist, 0, lidar_hgt])
        for _, row in processed.iterrows():
            assert row.hws == ref_speed(windfield, p)
            assert row.hwd == ref_direction(windfield)
            assert row.shear == ref_shear(windfield)
            assert row.veer == ref_veer(windfield)
    return test


test_lidar_static = scenario(
    processor_inputs(
        lidars(pitch=angles, roll=angles),
        windfields(directions, windspeeds)),
    ref_shear=lambda _: approx(0),
    ref_veer=lambda _: approx(0))


test_lidar_no_inertia = scenario(
    processor_inputs(
        lidars(pitch=angles, roll=angles, surge=surges, heave=heaves),
        windfields(directions, windspeeds)),
    ref_shear=lambda _: approx(0),
    ref_veer=lambda _: approx(0))


test_lidar_linear_inertia = scenario(
    processor_inputs(
        lidars(pitch=angles,
               roll=angles,
               surge_velocity=velocities,
               sway_velocity=velocities,
               heave_velocity=velocities),
        windfields(directions, windspeeds)),
    ref_shear=lambda _: approx(0),
    ref_veer=lambda _: approx(0))


test_lidar_linear = scenario(
    processor_inputs(
        lidars(pitch=angles,
               roll=angles,
               surge=surges,
               heave=heaves,
               surge_velocity=velocities,
               sway_velocity=velocities,
               heave_velocity=velocities),
        windfields(directions, windspeeds)),
    ref_shear=lambda _: approx(0),
    ref_veer=lambda _: approx(0))


test_lidar_angular = scenario(
    processor_inputs(
        lidars(pitch=angles,
               roll=angles,
               pitch_velocity=angular_velocities,
               roll_velocity=angular_velocities,
               yaw_velocity=angular_velocities),
        windfields(directions, windspeeds)),
    ref_shear=lambda _: approx(0, abs=1.0e-10),
    ref_veer=lambda _: approx(0))


test_lidar_full = scenario(
    processor_inputs(
        lidars(pitch=angles,
               roll=angles,
               surge=surges,
               heave=heaves,
               surge_velocity=velocities,
               sway_velocity=velocities,
               heave_velocity=velocities,
               pitch_velocity=angular_velocities,
               roll_velocity=angular_velocities,
               yaw_velocity=angular_velocities),
        windfields(directions, windspeeds)),
    ref_shear=lambda _: approx(0, abs=1.0e-10),
    ref_veer=lambda _: approx(0))


test_lidar_sheared_veering_windfield = scenario(
    processor_inputs(
        lidars(pitch=angles,
               surge=surges,
               heave=heaves,
               surge_velocity=velocities,
               sway_velocity=velocities,
               heave_velocity=velocities,
               pitch_velocity=angular_velocities,
               roll_velocity=angular_velocities,
               yaw_velocity=angular_velocities),
        windfields(directions, windspeeds, shear=shears, veer=veers)))
