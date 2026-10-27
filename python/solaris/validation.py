"""
Created on Fri Sep 11 16:10:39 2026

@author: eneso
"""
import copy
import math

from .core import D2R, G0, Multicopter, Plane, daily_extraterrestrial_horizontal, declination, extraterrestrial, isa, simulate, sun
from .presets import COPTER, preset
from . import studies


def run():
    R = []

    def add(g, n, ok, d, ref):
        R.append({'group': g, 'name': n, 'ok': bool(ok), 'detail': d, 'ref': ref})

    for h, pr, rr in ((11000, 22632.1, 0.363918), (20000, 5474.89, 0.088035), (25000, 2511.02, 0.039466)):
        _, p, rho = isa(h)
        add('Atmosphere', 'ISA at %d m (geopotential)' % h, abs(p - pr) / pr < 2e-5 and abs(rho - rr) / rr < 2e-4, 'p = %.1f Pa, ρ = %.6f kg/m³' % (p, rho), 'ISO 2533')

    add('Sun', 'Declination: 0° at equinox (day 81), 23.44° at solstice (day 172)', abs(declination(81) / D2R) < 0.5 and abs(declination(172) / D2R - 23.44) < 0.01, '%.2f° / %.2f°' % (declination(81) / D2R, declination(172) / D2R), 'Cooper (1969)')
    worst = 0.0
    for lat in (0, 30, 47, 60):
        el, _ = sun(172, 12.0, lat)
        worst = max(worst, abs(el / D2R - (90 - abs(lat - declination(172) / D2R))))
    add('Sun', 'Noon elevation = 90° − |φ − δ| at four latitudes', worst < 1e-9, 'max error %.1e°' % worst, 'spherical astronomy')
    worst = 0.0
    for lat, day in ((0, 81), (47, 172), (47, 355), (65, 172)):
        n = 20000
        tot = 0.0
        for k in range(n):
            hr = 24.0 * (k + 0.5) / n
            el, _ = sun(day, hr, lat)
            if el > 0:
                tot += extraterrestrial(day) * math.sin(el) * 86400.0 / n
        an = daily_extraterrestrial_horizontal(day, lat)
        worst = max(worst, abs(tot - an) / an)
    add('Sun', 'Daily extraterrestrial irradiation: numeric integral = closed form', worst < 1e-5, 'max rel. error %.1e' % worst, 'Duffie & Beckman')

    def num_opt(pl, cap):
        m, h = pl.mass, 500.0
        rho = isa(h)[2]
        best, best_cl = 1e99, 0.0
        for k in range(1, 40001):
            cl = cap * k / 40000.0
            cd = pl.cd0 + pl.k * cl * cl
            p = m * G0 * math.sqrt(2 * m * G0 / (rho * pl.S * cl)) * cd / cl
            if p < best:
                best, best_cl = p, cl
        return best_cl
    cfg_hi = copy.deepcopy(preset('skysailor')['config'])
    cfg_hi['airframe']['cl_max'] = 3.0
    pl = Plane(cfg_hi)
    an = math.sqrt(3 * pl.cd0 / pl.k)
    nu = num_opt(pl, 0.9 * pl.clmax)
    add('Flight mechanics', 'Minimum-power lift coefficient: numeric optimum = √(3·CD0/k)', abs(nu - an) / an < 1e-3, 'numeric %.4f vs analytic %.4f' % (nu, an), 'flight mechanics')
    pl = Plane(preset('skysailor')['config'])
    nu = num_opt(pl, 0.9 * pl.clmax)
    add('Flight mechanics', 'If √(3·CD0/k) exceeds 0.9·CL_max, the optimum sits at the stall-margin limit', abs(nu - pl.cl_cruise()) < 1e-3 and abs(pl.cl_cruise() - 0.9 * pl.clmax) < 1e-12, 'CL = %.4f (limit %.4f)' % (nu, 0.9 * pl.clmax), 'flight mechanics')

    for pid in ('hale', 'skysailor'):
        s = simulate(preset(pid)['config'])['summary']
        bus = abs(s['e_solar_kwh'] + s['e_bat_out_kwh'] * 0.95 - s['e_used_kwh'] - s['e_bat_in_kwh'] - s['e_waste_kwh']) / s['e_solar_kwh']
        bat = abs(s['e_bat_delta_kwh'] - (s['e_bat_in_kwh'] * 0.95 - s['e_bat_out_kwh'])) / max(s['e_bat_in_kwh'], 1e-12)
        add('Conservation', 'Energy balance closed (%s): solar + battery = consumed + stored + curtailed' % pid, bus < 1e-9 and bat < 1e-9, 'bus %.1e, battery %.1e' % (bus, bat), 'energy conservation')

    c = copy.deepcopy(preset('mapping')['config'])
    c['mission']['dt_s'] = 10.0
    r = simulate(c)
    s = r['summary']
    pl = Plane(c)
    t_an = pl.E * (pl.soc0 - pl.soc_min) * pl.eta_dis / s['p_level_w'] / 3600.0
    add('Endurance', 'Battery-only endurance = E·ΔSOC·η / P', abs(s['endurance_h'] - t_an) < 0.01, 'simulation %.3f h vs analytic %.3f h' % (s['endurance_h'], t_an), 'energy method')

    mc = Multicopter(COPTER)
    rho = isa(COPTER['alt_m'])[2]
    W = (mc.m_empty + mc.m_bat + COPTER['payload_kg']) * G0
    p_an = W ** 1.5 / math.sqrt(2 * rho * mc.A) / mc.fm / mc.eta + mc.p_av
    add('Multicopter', 'Hover power from momentum theory: P = W^1.5 / (FM·√(2ρA))', abs(mc.hover_power(COPTER['payload_kg']) - p_an) / p_an < 1e-12, '%.3f W' % p_an, 'momentum theory')
    v = 40.0
    D = 0.5 * rho * v * v * mc.cda
    T = math.sqrt(W * W + D * D)
    vh2 = T / (2 * rho * mc.A)
    p_hi = (T * vh2 / v / mc.fm + D * v) / mc.eta + mc.p_av
    add('Multicopter', 'Fast forward flight: induced velocity → v_h²/V (Glauert)', abs(mc.power(COPTER['payload_kg'], v) - p_hi) / p_hi < 1e-3, '%.2f W vs %.2f W' % (mc.power(COPTER['payload_kg'], v), p_hi), 'Glauert')

    sk = simulate(preset('skysailor')['config'])['summary']
    add('Plausibility', 'Sky-Sailor class at 47° N on 21 June: perpetual flight (flew 27 h in June 2008)', sk['perpetual'], 'min SOC %.2f, %.1f h/day of excess energy' % (sk['min_soc'], sk['excess_time_h']), 'Noth, ETH Zurich (2008)')
    cs = copy.deepcopy(preset('skysailor')['config'])
    cs['mission']['day_of_year'] = 355
    w = simulate(cs)['summary']
    add('Plausibility', 'Same aircraft on 21 December: no perpetual flight', not w['perpetual'], 'min SOC %.2f' % w['min_soc'], 'physics')

    sz = studies.size_min_span(preset('skysailor')['config'], lo=1.0, hi=8.0, n=16)
    smaller = copy.deepcopy(sz['config'])
    smaller['airframe']['span_m'] = sz['span_m'] * 0.95
    bm, mg = studies.best_battery(smaller)
    add('Sizing', 'Minimum span is perpetual, 5 % smaller span is not', sz['ok'] and sz['result']['summary']['perpetual'] and mg < 0, 'b_min = %.2f m, battery %.2f kg' % (sz['span_m'], sz['battery_kg']), 'sizing loop')
    return R
