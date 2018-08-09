#!/usr/bin/env python
import os
import camille
import yaml

data_dir = os.path.dirname(os.path.abspath(__file__))+"/test_data/bazefetcher/"

def test_all_samples_inside_time_interval_are_loaded():
    conf = """
           tag: [.*HS2.*]
           start: 2018-05-06
           end: 2018-05-09
           processor:
             fft:
               inverse: False
           input:
             bazefetcher:
               base_folder: {}
           """.format( data_dir )
    conf = yaml.safe_load(conf)

    c = camille.load_config(conf)
    result = camille.run(c)

    assert result.size == 9

def test_time_interval_is_left_closed():
    conf = """
           tag: [.*HS2.*]
           start: 2018-05-06 00:00:00.036000
           end: 2018-05-09
           processor:
             fft:
               inverse: False
           input:
             bazefetcher:
               base_folder: {}
           """.format( data_dir )
    conf = yaml.safe_load(conf)

    c = camille.load_config(conf)
    result = camille.run(c)

    assert result.size == 9

def test_time_interval_is_right_open():
    conf = """
           tag: [.*HS2.*]
           start: 2018-05-06
           end: 2018-05-07 00:00:00.439000
           processor:
             fft:
               inverse: False
           input:
             bazefetcher:
               base_folder: {}
           """.format( data_dir )
    conf = yaml.safe_load(conf)

    c = camille.load_config(conf)
    result = camille.run(c)

    assert result.size == 8
