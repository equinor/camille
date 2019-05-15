from math import cos, sin, radians, pi

def process(north, south, east, west,
            angle=None, level_offset=0,
            crs_thickness=None, crs_diameter=None):
    """

    Parameters
    ----------
    north : pandas.Series
        Bridle tension [kN]
    angle : int or float
    level_offset : int or float, optional
    crs_thickness : int or float
    crs_diameter : int or float

    Returns
    -------
    pandas.Series
    """
    angle = radians(angle)
    level_offset = radians(level_offset)

    Emod = 2.07e11 / 1e3
    ID = crs_thickness - 2 * crs_diameter * 1e-3
    I = pi / 64 * (crs_thickness**4 - ID**4)
    EI = Emod * I

    mom_y = (north - south) * 1e-6 * EI / ID
    mom_z = (east - west) * 1e-6 * EI / ID

    # Rotate to account for level offset
    mom_y, mom_z = [
        mom_y * cos(level_offset) - mom_z * sin(level_offset),
        mom_z * cos(level_offset) + mom_y * sin(level_offset)
    ]

    stress = 1e-3 * (mom_y * cos(angle) + mom_z * sin(angle)) / I * ID / 2

    return stress
