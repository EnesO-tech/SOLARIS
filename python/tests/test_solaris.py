"""
Created on Fri Sep 11 16:10:39 2026

@author: eneso
"""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from solaris import api, validation
from solaris.presets import COPTER, PRESETS

CHECKS = validation.run()


@pytest.mark.parametrize('check', CHECKS, ids=[c['group'] + ': ' + c['name'] for c in CHECKS])
def test_validation(check):
    assert check['ok'], check['detail']


@pytest.mark.parametrize('p', PRESETS, ids=[p['id'] for p in PRESETS])
def test_api_run(p):
    r = json.loads(api.run(json.dumps(p['config'])))
    assert r['ok'] and len(r['data']['series']['t_h']) > 10


def test_api_studies():
    cfg = json.dumps(PRESETS[1]['config'])
    ds = json.loads(api.design_space(cfg, 2.0, 5.0, 0.3, 2.0, 5))
    assert ds['ok'] and len(ds['data']['z']) == 5
    sm = json.loads(api.season_map(cfg))
    assert sm['ok'] and len(sm['data']['z']) == 15
    assert json.loads(api.copter(json.dumps(COPTER)))['ok']
    assert json.loads(api.presets())['ok'] and json.loads(api.schema())['ok']


def test_error_reported():
    r = json.loads(api.run('{}'))
    assert not r['ok']
