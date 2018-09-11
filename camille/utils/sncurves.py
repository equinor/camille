import numpy as np
from scipy.interpolate import interp1d

def sn_curve( stress, t=0, tref=None, k=None, logA=None, m=None ):
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
