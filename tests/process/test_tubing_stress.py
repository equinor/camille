from camille.process import tubing_stress
import pandas as pd
import numpy as np
from math import radians, cos, sin
from pandas.util.testing import assert_series_equal
from hypothesis import given
import hypothesis.strategies as st


def _create_series(data):
    index = pd.date_range(start='1/1/2018', periods=len(data))
    return pd.Series(data=data, name='stress', index=index)


positive_number = st.integers(min_value=1, max_value=1e6) \
                | st.floats(allow_nan=False,
                            allow_infinity=False,
                            min_value=1e-2,
                            max_value=1e6)

angle = st.integers(min_value=0, max_value=360) \
      | st.floats(min_value=0, max_value=360, allow_nan=False)

tension = st.builds(_create_series, st.lists(positive_number, max_size=5))


@given(angle1=angle,
       angle2=angle,
       angle3=angle,
       north=tension,
       south=tension,
       east=tension,
       west=tension,
       crs_thickness=positive_number,
       crs_diameter=positive_number)
def test_offset_should_invert_angle(angle1, angle2, angle3,
                                    north, south, east, west,
                                    crs_thickness, crs_diameter):

    result1 = tubing_stress(north, south, east, west,
                            angle=angle1 + angle3,
                            level_offset=angle1,
                            crs_thickness=crs_thickness,
                            crs_diameter=crs_diameter)

    result2 = tubing_stress(north, south, east, west,
                            angle=angle2 + angle3,
                            level_offset=angle2,
                            crs_thickness=crs_thickness,
                            crs_diameter=crs_diameter)

    assert_series_equal(result1, result2)


measure_offset = st.integers(min_value=-89, max_value=89) \
               | st.floats(min_value=-89, max_value=89, allow_nan=False)


@given(tension=tension,
       direction=angle,
       measure_offset=measure_offset,
       crs_thickness=positive_number,
       crs_diameter=positive_number)
def test_stress_direction(tension, direction, measure_offset,
                          crs_thickness, crs_diameter):

    direction_r = radians(direction)
    zero_tension = _create_series(np.zeros(tension.size))

    if cos(direction_r) >= 0:
        north = cos(direction_r) * tension
        south = zero_tension
    else:
        south = - cos(direction_r) * tension
        north = zero_tension

    if sin(direction_r) >= 0:
        east = sin(direction_r) * tension
        west = zero_tension
    else:
        west = - sin(direction_r) * tension
        east = zero_tension

    positive_direction = tubing_stress(north, south, east, west,
                                       angle=direction + measure_offset,
                                       level_offset=0,
                                       crs_thickness=crs_thickness,
                                       crs_diameter=crs_diameter)

    negative_direction = tubing_stress(north, south, east, west,
                                       angle=direction + 180 + measure_offset,
                                       level_offset=0,
                                       crs_thickness=crs_thickness,
                                       crs_diameter=crs_diameter)

    assert (positive_direction > 0).all()
    assert (negative_direction < 0).all()
    assert_series_equal(positive_direction, -negative_direction)


@given(tension=tension,
       direction=angle,
       crs_thickness=positive_number,
       crs_diameter=positive_number)
def test_zero(tension, direction, crs_thickness, crs_diameter):

    zero = _create_series(np.zeros(tension.size))

    result = tubing_stress(tension, tension, tension, tension,
                           angle=direction,
                           level_offset=0,
                           crs_thickness=crs_thickness,
                           crs_diameter=crs_diameter)

    assert_series_equal(result, zero)
