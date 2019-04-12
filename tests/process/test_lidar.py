from camille.process.lidar import sample_hgt, process
from datetime import datetime, timedelta
from hypothesis import given, example, settings, reproduce_failure
from hypothesis.strategies import builds, floats, integers
from itertools import count
from math import acos, atan2, cos, pi, radians, sin, tan
from pytest import approx
from pytz import utc
import numpy as np
import pandas as pd


elevation = list(map(radians, [5.0, 5.0, -5.0, -5.0]))
telescope = list(map(radians, [-15.0, 15.0, -15.0, 15.0]))
zenith = [acos(cos(elevation[i]) * cos(telescope[i])) for i in range(4)]
azimuth = [atan2(sin(elevation[i]), tan(telescope[i])) for i in range(4)]
hub_hgt = 100


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
        loc[2] += hub_hgt

        # Sanity check
        assert loc[2] == approx(
            sample_hgt(beam, hub_hgt, 0, distance, p, r, a, z))

        _, wnd = windfield(loc)
        rws = np.dot(-wnd, los)

        # Sanity check
        assert rws > 0

        return timestamp, beam, rws, 1, self.pitch, self.roll

    def __repr__(self):
        return 'lidar_simulator({}, {})'.format(self.pitch, self.roll)


class windfield_function:
    def __init__(self, direction, ref_speed, shear_coeff=0.0):
        self.direction = direction
        self.ref_speed = ref_speed
        self.shear_coeff = shear_coeff

    def __call__(self, pnt):
        hgt = pnt[2]
        u = self.ref_speed * pow(hgt / hub_hgt, self.shear_coeff)
        return u, u * self.direction

    def __repr__(self):
        return 'windfield_function({}, {}, {})'.format(
            self.direction,
            self.ref_speed,
            self.shear_coeff
        )


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


windspeeds = floats(min_value=0.5, max_value=18.0)
directions = builds(uniform_dir, floats(min_value=-pi / 4, max_value=pi / 4))
angles = floats(min_value=-0.0872665, max_value=0.0872665)

windfields = builds(windfield_function, directions, windspeeds)
lidars = builds(lidar_simulator, angles, angles)

shear_coeffs = floats(min_value=0.143 / 2, max_value=0.143 * 2)
sheared_windfields = builds(
    windfield_function, directions, windspeeds, shear_coeffs)
# shear_coefficient is inaccurate with roll, could be addressed
flat_lidars = builds(lidar_simulator, angles)

distances = integers(min_value=50, max_value=400)

processor_input = builds(
    generate_input, windfields, lidars, distances)
sheared_processor_input = builds(
    generate_input, sheared_windfields, flat_lidars, distances)


@given(processor_input)
@settings(deadline=None)
def test_lidar(args):
    dist, windfield, _, df = args
    processed = process(
        df,
        dist,
        hub_hgt=hub_hgt,
        lidar_hgt=0,
        pitch_offset=0,
        roll_offset=0,
        extra_columns=['shear_coeff'],
    )

    ref_speed, _ = windfield(np.array([dist, 0, hub_hgt]))
    for _, row in processed.iterrows():
        assert row.shear_coeff == approx(0)
        assert row.hws == approx(ref_speed)


@given(sheared_processor_input)
@settings(deadline=None)
def test_lidar_sheared_windfield(args):
    dist, windfield, _, df = args
    processed = process(
        df,
        dist,
        hub_hgt=hub_hgt,
        lidar_hgt=0,
        pitch_offset=0,
        roll_offset=0,
        extra_columns=['shear_coeff'],
    )

    ref_speed, _ = windfield(np.array([dist, 0, hub_hgt]))
    ref_shear = windfield.shear_coeff
    for _, row in processed.iterrows():
        assert row.shear_coeff == approx(ref_shear)
        assert row.hws == approx(ref_speed)
