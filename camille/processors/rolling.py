from pandas import DataFrame

def process(df, **kwargs):
    options = ('window', 'interpolation')
    if not all([key in options for key in kwargs.keys()]):
        raise ValueError('Unknown argument(s) {}'.format(kwargs.keys() - options))
    window = kwargs.get('window', 10)
    interpolation = kwargs.get('interpolation', 'triang')
    return DataFrame(df.rolling(window, win_type=interpolation).mean())
