import pandas as pd


def process(deltatemp):
    atm_stb = deltatemp.apply(_atm_stb)
    atm_stb.rename('atm_stb', inplace=True)
    return atm_stb


def _atm_stb(delta_temp):
    if 5.0 <= delta_temp         : return 'Very Unstable'
    if 2.5 <= delta_temp <   5.0 : return 'Unstable'
    if 0.5 <= delta_temp <   2.5 : return 'Slightly Unstable'
    if -0.5 < delta_temp <   0.5 : return 'Neutral'
    if -2.5 < delta_temp <= -0.5 : return 'Slightly Stable'
    if -5.0 < delta_temp <= -2.5 : return 'Stable'
    if        delta_temp <= -5.0 : return 'Very Stable'

