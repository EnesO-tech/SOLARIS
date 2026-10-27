"""
Created on Fri Sep 11 16:10:39 2026

@author: eneso
"""
import copy
import math

from .core import Multicopter, Plane, margin, simulate


def set_path(cfg, path, value):
    o = cfg
    ks = path.split('.')
    for k in ks[:-1]:
        o = o.setdefault(k, {})
    o[ks[-1]] = value


def design_space(cfg, spans, bats):
    grid = []
    for b in bats:
        row = []
        for s in spans:
            c = copy.deepcopy(cfg)
            c['airframe']['span_m'] = s
            c['battery']['mass_kg'] = b
            row.append(margin(c))
        grid.append(row)
    return {'x': spans, 'y': bats, 'z': grid}


def season_map(cfg, lats, days):
    grid = []
    for la in lats:
        row = []
        for d in days:
            c = copy.deepcopy(cfg)
            c['mission']['latitude_deg'] = la
            c['mission']['day_of_year'] = d
            row.append(margin(c))
        grid.append(row)
    return {'x': days, 'y': lats, 'z': grid}


def best_battery(cfg, lo=None, hi=None):
    m0 = float(cfg['battery']['mass_kg'])
    lo = 0.02 * m0 if lo is None else lo
    hi = 6.0 * m0 if hi is None else hi

    def f(b):
        c = copy.deepcopy(cfg)
        c['battery']['mass_kg'] = b
        return margin(c)
    g = (math.sqrt(5) - 1) / 2
    a, b_ = lo, hi
    c1, c2 = b_ - g * (b_ - a), a + g * (b_ - a)
    f1, f2 = f(c1), f(c2)
    for _ in range(28):
        if f1 > f2:
            b_, c2, f2 = c2, c1, f1
            c1 = b_ - g * (b_ - a)
            f1 = f(c1)
        else:
            a, c1, f1 = c1, c2, f2
            c2 = a + g * (b_ - a)
            f2 = f(c2)
    return (c1, f1) if f1 > f2 else (c2, f2)


def size_min_span(cfg, lo=0.8, hi=80.0, n=24):
    def best(span):
        c = copy.deepcopy(cfg)
        c['airframe']['span_m'] = span
        bm, mg = best_battery(c)
        c['battery']['mass_kg'] = bm
        return mg, c
    spans = [lo * (hi / lo) ** (k / (n - 1)) for k in range(n)]
    prev = None
    first = None
    for sp in spans:
        mg, c = best(sp)
        if mg >= 0:
            first = (sp, c)
            break
        prev = sp
    if first is None:
        return {'ok': False, 'reason': 'No perpetual flight possible between %.1f m and %.0f m span for this date, latitude and technology.' % (lo, hi)}
    hi_s, c_hi = first
    if prev is not None:
        lo_s = prev
        for _ in range(30):
            mid = 0.5 * (lo_s + hi_s)
            mg, c = best(mid)
            if mg >= 0:
                hi_s, c_hi = mid, c
            else:
                lo_s = mid
            if hi_s - lo_s < 0.005 * hi_s:
                break
    r = simulate(c_hi)
    return {'ok': True, 'span_m': hi_s, 'battery_kg': c_hi['battery']['mass_kg'], 'config': c_hi, 'result': r}


def copter_study(cc):
    mc = Multicopter(cc)
    pl = float(cc.get('payload_kg', 0.0))
    E = mc.energy_j()
    vs = [0.5 * k for k in range(0, 61)]
    curve = []
    for v in vs:
        p = mc.power(pl, v)
        curve.append({'v': v, 'p': p, 'endurance_min': E / p / 60.0, 'range_km': E / p * v / 1000.0})
    best_e = max(curve, key=lambda r: r['endurance_min'])
    best_r = max(curve, key=lambda r: r['range_km'])
    pmax = float(cc.get('max_payload_kg', 2.0))
    pls = [pmax * k / 20.0 for k in range(21)]
    payload = [{'payload_kg': x, 'hover_min': E / mc.hover_power(x) / 60.0} for x in pls]
    m = mc.m_empty + mc.m_bat + pl
    return {'curve': curve, 'payload': payload, 'hover_w': mc.hover_power(pl), 'hover_min': E / mc.hover_power(pl) / 60.0, 'best_endurance': best_e, 'best_range': best_r, 'mass_kg': m, 'disk_loading': m * 9.80665 / mc.A, 'energy_wh': E / 3600.0}
