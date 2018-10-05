#!/usr/bin/env python
import pandas as pd
import numpy as np

from camille.process import rolling

def test_rolling():
    df = pd.DataFrame(list(range(100)))
    rolled = rolling.process(df)

    assert np.allclose(100, len(rolled))
    assert np.allclose(sum(range(90,100))/10.,
                rolled[0][99])
