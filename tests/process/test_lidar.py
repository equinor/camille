from camille.core import sample_hgt
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
    def __init__(self, pitch=0, roll=0):
        self.pitch = pitch
        self.roll = roll

    def __call__(self, windfield, timestamp, distance, beam):
        d = distance / cos(zenith[beam])
        z = zenith[beam]
        a = azimuth[beam]
        p = self.pitch
        r = self.roll
        rot = np.array([[cos(p),  sin(p) * sin(r), -sin(p) * cos(r)],
                        [     0,           cos(r),           sin(r)],
                        [sin(p), -cos(p) * sin(r),  cos(p) * cos(r)]])
        los = rot @ np.array([cos(z),
                              sin(z) * cos(a),
                              sin(z) * sin(a)])
        loc = los * d
        loc[2] += lidar_hgt

        # Sanity check
        assert loc[2] == approx(sample_hgt(lidar_hgt, distance, p, r, a, z))

        _, wnd = windfield(loc)
        rws = np.dot(-wnd, los)

        return timestamp, beam, rws, 1, self.pitch, self.roll

    def __repr__(self):
        return 'lidar_simulator({}, {})'.format(self.pitch, self.roll)


class windfield_function:
    def __init__(self, direction, ref_speed, shear=0.0, veer=0.0):
        self.direction = direction
        self.ref_speed = ref_speed
        self.shear = shear
        self.veer = veer

    def __call__(self, pnt):
        hgt = pnt[2]
        u = self.ref_speed * pow(hgt / lidar_hgt, self.shear)
        veer_offset = self.veer * (lidar_hgt - hgt)
        rot = np.array([[ cos(veer_offset), sin(veer_offset), 0],
                        [-sin(veer_offset), cos(veer_offset), 0],
                        [                0,                0, 1]])
        return u, rot @ self.direction * u

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
        'los_id', 'radial_windspeed', 'status', 'pitch', 'roll'
    ])

    time = (start_date + timedelta(seconds=1) * i for i in range(n))
    beam = (i % 4 for i in count())

    for t, b in zip(time, beam):
        timestamp, los_id, radial_windspeed, status, pitch, roll = (
            lidar(windfield, t, distance, b))
        df.loc[timestamp] = los_id, radial_windspeed, status, pitch, roll
    return distance, windfield, lidar, df


def uniform_dir(alpha):
    return np.array([-cos(alpha), sin(alpha), 0.0])


distances = integers(min_value=50, max_value=400)
directions = builds(uniform_dir, floats(min_value=-pi / 4, max_value=pi / 4))
angles = floats(min_value=-0.0872665, max_value=0.0872665)
windspeeds = floats(min_value=0.5, max_value=18.0)

windfields = builds(windfield_function, directions, windspeeds)
lidars = builds(lidar_simulator, angles, angles)
# shear is inaccurate with roll, could be addressed
flat_lidars = builds(lidar_simulator, angles)

shears = floats(min_value=0.143 / 2, max_value=0.143 * 2)
veers = floats(min_value=-0.0314159, max_value=0.0314159) # +- 1.8 deg / m
sheared_veering_windfields = builds(
    windfield_function, directions, windspeeds, shear=shears, veer=veers)

processor_input = builds(
    generate_input, windfields, lidars, distances)
sheared_veering_processor_input = builds(
    generate_input, sheared_veering_windfields, flat_lidars, distances)

def process_with_args(dist, df):
    out = camille.lidar.windfield_desc(df, dist, lidar_hgt, 0)
    out['speed'] = out.speed_lwr
    out['dir'] = out.dir_lwr
    out['height'] = out.height_lwr
    out['hws'] = camille.lidar.extrapolate_windspeed(out, lidar_hgt)
    out['hwd'] = camille.lidar.extrapolate_winddirection(out, lidar_hgt)
    return out


@given(processor_input)
@settings(deadline=None)
def test_lidar(args):
    dist, windfield, _, df = args
    processed = process_with_args(dist, df)

    ref_speed, _ = windfield(np.array([dist, 0, lidar_hgt]))
    ref_direction = windfield.yaw_direction()
    for _, row in processed.iterrows():
        assert row.shear == approx(0)
        assert row.veer == approx(0)
        assert row.hwd == approx(ref_direction)
        assert row.hws == approx(ref_speed)


@given(sheared_veering_processor_input)
@settings(deadline=None)
def test_lidar_sheared_veering_windfield(args):
    dist, windfield, _, df = args
    processed = process_with_args(dist, df)

    ref_speed, _ = windfield(np.array([dist, 0, lidar_hgt]))
    ref_direction = windfield.yaw_direction()
    ref_shear = windfield.shear
    ref_veer = windfield.veer
    for _, row in processed.iterrows():
        assert row.shear == approx(ref_shear)
        assert row.veer == approx(ref_veer)
        assert row.hwd == approx(ref_direction)
        assert row.hws == approx(ref_speed)
