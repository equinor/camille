def process(df, **kwargs):
    options = ['window', 'interpolation']
    if not all([key in options for key in kwargs.keys()]):
        raise ArgumentError('Unknown argument(s) {}'.format(kwargs.keys() - options))
    window = kwargs.get('window', 10)
    interpolation = kwargs.get('interpolation', 10')
    return df.rolling(window, win_type=interpolation)
