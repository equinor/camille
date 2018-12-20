# Camille
[![Build Status](https://travis-ci.org/Statoil/camille.svg?branch=master)](https://travis-ci.org/Statoil/camille)
[![Codacy Badge](https://api.codacy.com/project/badge/Grade/61db6e0137e743db84041b1239436c39)](https://www.codacy.com/app/equinor_sib/camille?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=Statoil/camille&amp;utm_campaign=Badge_Grade)
[![Codacy Badge](https://api.codacy.com/project/badge/Coverage/61db6e0137e743db84041b1239436c39)](https://www.codacy.com/app/equinor_sib/camille?utm_source=github.com&utm_medium=referral&utm_content=Statoil/camille&utm_campaign=Badge_Coverage)
[![MutMut Badge](https://img.shields.io/badge/dynamic/json.svg?label=mutant%20survival%20rate&url=https%3A%2F%2Fs3-eu-west-1.amazonaws.com%2Fequinor-sib%2Fcamille%2Fmutmut_report.json&query=%24..survival_rate&colorB=blue&suffix=%20%25)](https://mutmut.readthedocs.io/en/latest/)
[![PyPI version](https://badge.fury.io/py/camille.svg)](https://badge.fury.io/py/camille)

A dataframe processing toolbox.

## Installation

```bash
pip install camille
```

## Usage

```python
import camille
import datetime
import pytz

bazefetcher_source = camille.source.bazefetcher('<bazefetcher_root_dir>')
bazefetcher_out = camille.output.bazefetcher('<bazefetcher_root_dir>')

begin = datetime.datetime(2017, 11, 1, tzinfo=pytz.utc )
end = datetime.datetime(2017, 11, 3, tzinfo=pytz.utc )

data = bazefetcher_source('<tag>', begin, end)

processed = camille.process.low_pass(data, sampling_rate=10, cutoff_freq=2)

bazefetcher_out('<tag>', start, end)
```
