from math import pi

def process(series, diameter):
    """Calculate the stress induced from tension in the chain

    Parameters
    ----------
    series : pandas.Series
        Bridle tension [kN]
    diameter : int or float
        The diameter of the chain [mm]

    Returns
    -------
    pandas.Series
        Stress in the material induced from tension on the chain [MPa]
    """
    A = 2 * pi / 4 * (diameter * 1e-3) ** 2
    return 1e-3 * series / A
