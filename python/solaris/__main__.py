"""
Created on Fri Sep 11 16:10:39 2026

@author: eneso
"""
import argparse
import sys
import time

from .core import simulate
from .presets import PRESETS, preset
from . import studies, validation


def main(argv=None):
    ap = argparse.ArgumentParser(prog='solaris', description='SOLARIS – solar aircraft and drone design studio')
    sub = ap.add_subparsers(dest='cmd', required=True)
    sub.add_parser('presets')
    r = sub.add_parser('run')
    r.add_argument('preset')
    s = sub.add_parser('size')
    s.add_argument('preset')
    sub.add_parser('validate')
    a = ap.parse_args(argv)
    if a.cmd == 'presets':
        for p in PRESETS:
            print('%-10s %s' % (p['id'], p['name']))
        return 0
    if a.cmd == 'run':
        s_ = simulate(preset(a.preset)['config'])['summary']
        print('mass %.2f kg · span %.1f m · level power %.1f W · min SOC %.2f · %s' % (s_['mass_kg'], s_['span_m'], s_['p_level_w'], s_['min_soc'], 'PERPETUAL' if s_['perpetual'] else 'not perpetual'))
        return 0
    if a.cmd == 'size':
        z = studies.size_min_span(preset(a.preset)['config'])
        print(('minimum span %.2f m with %.2f kg battery' % (z['span_m'], z['battery_kg'])) if z['ok'] else z['reason'])
        return 0
    if a.cmd == 'validate':
        t0 = time.perf_counter()
        res = validation.run()
        fail = 0
        for x in res:
            print(('  PASS  ' if x['ok'] else '  FAIL  ') + '[' + x['group'] + '] ' + x['name'] + '  (' + x['detail'] + ')')
            fail += 0 if x['ok'] else 1
        print('%d/%d checks passed in %.2f s' % (len(res) - fail, len(res), time.perf_counter() - t0))
        return 1 if fail else 0


if __name__ == '__main__':
    sys.exit(main())
