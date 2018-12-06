from scipy import fftpack as fftp
from pandas import DataFrame


__functions = {
    'fft': fftp.fft,
    'ifft': fftp.ifft,
    'fft2': fftp.fft2,
    'ifft2': fftp.ifft2,
}


def process(df, inverse=False):
    """Process Fast Fourier transform

    Parameters
    ----------
    df : pandas.DataFrame
    inverse : bool, optional
        Transform will be inverse if True

    Returns
    -------
    pandas.DataFrame

    Examples
    --------

    Fourier transform `df`, inverse transform `spectrum`

    >>> df = pd.DataFrame(np.random.normal(size=(100)))
    >>> spectrum = process.fft(df, inverse=False)
    >>> signal = process.fft(spectrum, inverse=True).apply(np.real)
    >>> np.allclose(df, signal)
    True
    """
    dimensions = 2 if len(df.columns) > 1 else 1
    funcname = '{}fft{}'.format('i' if inverse else '',
                                '2' if dimensions == 2 else '')
    func = __functions[funcname]
    return DataFrame(func(df.values))
