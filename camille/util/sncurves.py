import numpy as np
from scipy.interpolate import interp1d

def sn_curve( stress, k=None, logA=None, m=None, t=0, tref=25.0 ):
    """SN Curve

    Computes the number of stress cycles before failure for the given stress.

    Parameters
    ----------
    stress : float or list of float
        Stress range [MPa]
    k : float
        Thickness exponent on fatigue strength
    logA : float or list of float
        Intercept of log N axis
    m : float or list of float
        Negative inverse slope of S-N curve
    t : float, optional
        Thickness [mm] through which a crack will most likely grow. t = tref is
        used for t < tref
    tref : float, optional
        Reference thickness [mm]

    Returns
    -------
    float or list of floats
        Number of stress cycles before failure

    """
    alpha = max( (t/tref)**k, 1  )
    stress = np.array(stress) * alpha

    try:
        x = np.zeros(len(logA)+1)
        y = np.zeros(len(logA)+1)

        [x[0],x[-1]] = [ 12, -9 ]
        [y[0],y[-1]] = [ logA[0] - m[0]*12, logA[-1] + m[-1]*9 ]

        for i in range(len(logA)-1, 0, -1):
            x[i] = ( logA[i] - logA[i-1] ) / ( m[i] - m[i-1] )
            y[i] = logA[i] - m[i] * x[i]

    except TypeError:
        x = np.array([ 12, -9 ])
        y = np.array([ logA - m*12, logA + m*9 ])

    interp = interp1d( x, y, kind='linear', fill_value='extrapolate' )

    return 10 ** interp( np.log10(stress) )
