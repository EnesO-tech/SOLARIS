"""
Created on Fri Sep 11 16:10:39 2026

@author: eneso
"""
import copy
import json
import math

from .core import Plane, isa, simulate
from .presets import COPTER, PRESETS
from . import studies

SCHEMA = [
    {'id': 'airframe', 'label': 'Airframe', 'fields': [
        {'path': 'airframe.span_m', 'label': 'Wingspan', 'unit': 'm', 'step': 0.1},
        {'path': 'airframe.aspect_ratio', 'label': 'Aspect ratio', 'unit': '–', 'step': 0.5},
        {'path': 'airframe.cd0', 'label': 'Zero-lift drag CD0', 'unit': '–', 'step': 0.001},
        {'path': 'airframe.oswald', 'label': 'Oswald factor', 'unit': '–', 'step': 0.01},
        {'path': 'airframe.cl_max', 'label': 'CL max', 'unit': '–', 'step': 0.05},
        {'path': 'airframe.k_struct', 'label': 'Structure coefficient (Noth)', 'unit': '–', 'step': 0.02},
        {'path': 'airframe.struct_mass_kg', 'label': 'Structure mass (0 = model)', 'unit': 'kg', 'step': 0.5},
    ]},
    {'id': 'solar', 'label': 'Solar cells', 'fields': [
        {'path': 'solar.enabled', 'label': 'Solar cells on wing', 'type': 'bool'},
        {'path': 'solar.area_fraction', 'label': 'Covered wing area', 'unit': '–', 'step': 0.02},
        {'path': 'solar.cell_efficiency', 'label': 'Cell efficiency', 'unit': '–', 'step': 0.005},
        {'path': 'solar.areal_mass_kgm2', 'label': 'Areal mass', 'unit': 'kg/m²', 'step': 0.01},
        {'path': 'solar.camber_factor', 'label': 'Camber / incidence factor', 'unit': '–', 'step': 0.01},
    ]},
    {'id': 'battery', 'label': 'Battery', 'fields': [
        {'path': 'battery.mass_kg', 'label': 'Battery mass', 'unit': 'kg', 'step': 0.05},
        {'path': 'battery.specific_energy_whkg', 'label': 'Specific energy', 'unit': 'Wh/kg', 'step': 5},
        {'path': 'battery.soc_min', 'label': 'Minimum state of charge', 'unit': '–', 'step': 0.01},
        {'path': 'battery.soc0', 'label': 'Initial state of charge', 'unit': '–', 'step': 0.05},
        {'path': 'battery.max_c_rate', 'label': 'Max. charge rate', 'unit': 'C', 'step': 0.1},
    ]},
    {'id': 'propulsion', 'label': 'Propulsion', 'fields': [
        {'path': 'propulsion.eta_propeller', 'label': 'Propeller efficiency', 'unit': '–', 'step': 0.01},
        {'path': 'propulsion.eta_motor', 'label': 'Motor efficiency', 'unit': '–', 'step': 0.01},
        {'path': 'propulsion.kg_per_w', 'label': 'Propulsion mass per watt', 'unit': 'kg/W', 'step': 0.0005},
        {'path': 'propulsion.n_motors', 'label': 'Motors', 'unit': '–', 'step': 1},
    ]},
    {'id': 'systems', 'label': 'Avionics & payload', 'fields': [
        {'path': 'systems.avionics_mass_kg', 'label': 'Avionics mass', 'unit': 'kg', 'step': 0.05},
        {'path': 'systems.avionics_power_w', 'label': 'Avionics power', 'unit': 'W', 'step': 0.5},
        {'path': 'systems.payload_mass_kg', 'label': 'Payload mass', 'unit': 'kg', 'step': 0.05},
        {'path': 'systems.payload_power_w', 'label': 'Payload power', 'unit': 'W', 'step': 0.5},
    ]},
    {'id': 'mission', 'label': 'Mission & sun', 'fields': [
        {'path': 'mission.latitude_deg', 'label': 'Latitude', 'unit': '°', 'step': 1},
        {'path': 'mission.day_of_year', 'label': 'Day of year', 'unit': 'd', 'step': 1},
        {'path': 'mission.alt_m', 'label': 'Flight altitude', 'unit': 'm', 'step': 100},
        {'path': 'mission.altitude_storage', 'label': 'Store energy as altitude', 'type': 'bool'},
        {'path': 'mission.alt_max_m', 'label': 'Max. altitude (storage)', 'unit': 'm', 'step': 100},
        {'path': 'mission.days', 'label': 'Simulated days', 'unit': 'd', 'step': 1},
        {'path': 'mission.start_hour', 'label': 'Start (solar time)', 'unit': 'h', 'step': 0.5},
        {'path': 'mission.clearness', 'label': 'Sky clearness', 'unit': '–', 'step': 0.05},
    ]},
]

COPTER_SCHEMA = [
    {'path': 'n_rotors', 'label': 'Rotors', 'unit': '–', 'step': 1},
    {'path': 'rotor_diameter_m', 'label': 'Rotor diameter', 'unit': 'm', 'step': 0.01},
    {'path': 'figure_of_merit', 'label': 'Figure of merit', 'unit': '–', 'step': 0.01},
    {'path': 'eta_motor_esc', 'label': 'Motor + ESC efficiency', 'unit': '–', 'step': 0.01},
    {'path': 'cd_area_m2', 'label': 'Drag area CdA', 'unit': 'm²', 'step': 0.005},
    {'path': 'empty_mass_kg', 'label': 'Empty mass (no battery)', 'unit': 'kg', 'step': 0.1},
    {'path': 'battery_mass_kg', 'label': 'Battery mass', 'unit': 'kg', 'step': 0.05},
    {'path': 'specific_energy_whkg', 'label': 'Specific energy', 'unit': 'Wh/kg', 'step': 5},
    {'path': 'payload_kg', 'label': 'Payload', 'unit': 'kg', 'step': 0.1},
    {'path': 'avionics_power_w', 'label': 'Avionics power', 'unit': 'W', 'step': 1},
    {'path': 'alt_m', 'label': 'Altitude', 'unit': 'm', 'step': 100},
]


def _clean(o):
    if isinstance(o, dict):
        return {k: _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_clean(v) for v in o]
    if isinstance(o, float):
        return o if math.isfinite(o) else None
    return o


def _out(o):
    return json.dumps({'ok': True, 'data': _clean(o)})


def _err(e):
    return json.dumps({'ok': False, 'error': str(e)})


def _geom(cfg):
    p = Plane(cfg)
    return {'span_m': p.b, 'aspect_ratio': p.AR, 'panel_fraction': p.f_panel, 'battery_kg': p.m_bat, 'mass_kg': p.mass, 'n_motors': p.n_motors}


def presets():
    try:
        return _out({'planes': PRESETS, 'copter': COPTER})
    except Exception as e:
        return _err(e)


def schema():
    try:
        return _out({'groups': SCHEMA, 'copter': COPTER_SCHEMA})
    except Exception as e:
        return _err(e)


def run(cfg_json):
    try:
        cfg = json.loads(cfg_json)
        r = simulate(cfg)
        r['geometry'] = _geom(cfg)
        return _out(r)
    except Exception as e:
        return _err(e)


def design_space(cfg_json, s0, s1, b0, b1, n):
    try:
        cfg = json.loads(cfg_json)
        n = max(4, min(int(n), 30))
        spans = [s0 + (s1 - s0) * k / (n - 1) for k in range(n)]
        bats = [b0 + (b1 - b0) * k / (n - 1) for k in range(n)]
        c = copy.deepcopy(cfg)
        c['mission']['days'] = 2
        return _out(studies.design_space(c, spans, bats))
    except Exception as e:
        return _err(e)


def season_map(cfg_json):
    try:
        cfg = json.loads(cfg_json)
        c = copy.deepcopy(cfg)
        c['mission']['days'] = 2
        lats = [5.0 * k for k in range(15)]
        days = [1 + 365 * k / 24.0 for k in range(25)]
        return _out(studies.season_map(c, lats, [round(d) for d in days]))
    except Exception as e:
        return _err(e)


def size(cfg_json):
    try:
        r = studies.size_min_span(json.loads(cfg_json))
        if r.get('ok'):
            r['result']['geometry'] = _geom(r['config'])
        return _out(r)
    except Exception as e:
        return _err(e)


def copter(cc_json):
    try:
        return _out(studies.copter_study(json.loads(cc_json)))
    except Exception as e:
        return _err(e)


def validate():
    try:
        from . import validation
        return _out(validation.run())
    except Exception as e:
        return _err(e)
