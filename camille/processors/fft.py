from scipy import fftpack as fftp
from pandas import DataFrame

__defaults = {
    'inverse': False,
}

__functions = {
    'fft': fftp.fft,
    'ifft': fftp.ifft,
    'fft2': fftp.fft2,
    'ifft2': fftp.ifft2,
}

def process(df, **kwargs):
    options = ('inverse')
    if not all(key in options for key in kwargs.keys()):
        raise ValueError('Unknown argument(s) {}'
                         .format(set(kwargs.keys()) - set(options)))

    inverse = kwargs.get('inverse', __defaults['inverse'])
    dimensions = 2 if len(df.columns) > 1 else 1

    funcname = '{}fft{}'.format('i' if inverse else '',
                                '2' if dimensions == 2 else '')
    func = __functions[funcname]

    return DataFrame(func(df.values))
