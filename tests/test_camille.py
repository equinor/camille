#!/usr/bin/env python
import unittest
import pandas as pd

class TestCamille(unittest.TestCase):

    def test_rolling(self):
        from camille import rolling
        df = pd.DataFrame(list(range(100)))
        rolled = rolling.process(df)
        self.assertEqual(100, len(rolled))
        self.assertEqual(sum(range(90,100))/10.,
                         rolled[0][99])


if __name__ == '__main__':
    unittest.main()
