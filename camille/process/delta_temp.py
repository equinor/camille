def process(amb, sea):
    delta_temp  = sea.resample('20T').mean() - amb.resample('20T').mean()
    delta_temp.rename('delta_temp', inplace=True)
    return delta_temp

