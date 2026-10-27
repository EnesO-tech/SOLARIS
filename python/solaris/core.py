"""
Created on Fri Sep 11 16:10:39 2026

@author: eneso
"""
import copy
import math

G0 = 9.80665
R_AIR = 287.05287
I_SC = 1361.0
D2R = math.pi / 180.0


def isa(h):
    h = max(-500.0, min(float(h), 32000.0))
    if h <= 11000.0:
        T = 288.15 - 0.0065 * h
        p = 101325.0 * (T / 288.15) ** (G0 / (0.0065 * R_AIR))
    elif h <= 20000.0:
        T = 216.65
        p = 22632.06 * math.exp(-G0 * (h - 11000.0) / (R_AIR * T))
    else:
        T = 216.65 + 0.001 * (h - 20000.0)
        p = 5474.889 * (T / 216.65) ** (-G0 / (0.001 * R_AIR))
    return T, p, p / (R_AIR * T)


def declination(day):
    return 23.44 * D2R * math.sin(2 * math.pi * (284 + day) / 365.0)


def sun(day, hour, lat_deg):
    d = declination(day)
    phi = lat_deg * D2R
    w = (hour - 12.0) * 15.0 * D2R
    s = math.sin(phi) * math.sin(d) + math.cos(phi) * math.cos(d) * math.cos(w)
    el = math.asin(max(-1.0, min(1.0, s)))
    az = math.atan2(math.sin(w), math.cos(w) * math.sin(phi) - math.tan(d) * math.cos(phi))
    return el, az


def extraterrestrial(day):
    return I_SC * (1.0 + 0.033 * math.cos(2 * math.pi * day / 365.0))


def irradiance(day, hour, lat_deg, h, clearness=1.0):
    el, az = sun(day, hour, lat_deg)
    if el <= 0:
        return 0.0, el, az
    i0 = extraterrestrial(day)
    el_deg = el / D2R
    am = 1.0 / (math.sin(el) + 0.50572 * (6.07995 + el_deg) ** -1.6364)
    p_ratio = isa(h)[1] / 101325.0
    i_dn = i0 * 0.7 ** ((am * p_ratio) ** 0.678)
    g = i_dn * math.sin(el) * (1.0 + 0.1 * p_ratio)
    return g * clearness, el, az


def daily_extraterrestrial_horizontal(day, lat_deg):
    d = declination(day)
    phi = lat_deg * D2R
    x = -math.tan(phi) * math.tan(d)
    ws = math.acos(max(-1.0, min(1.0, x)))
    return 24 * 3600 / math.pi * extraterrestrial(day) * (math.cos(phi) * math.cos(d) * math.sin(ws) + ws * math.sin(phi) * math.sin(d))


class Plane:
    def __init__(self, cfg):
        self.cfg = copy.deepcopy(cfg)
        a = cfg['airframe']
        self.b = float(a['span_m'])
        self.AR = float(a['aspect_ratio'])
        self.S = self.b * self.b / self.AR
        self.cd0 = float(a['cd0'])
        self.e = float(a['oswald'])
        self.clmax = float(a.get('cl_max', 1.3))
        self.k = 1.0 / (math.pi * self.AR * self.e)
        self.k_struct = float(a.get('k_struct', 0.44))
        self.m_struct = float(a['struct_mass_kg']) if a.get('struct_mass_kg') else self.k_struct * self.b ** 3.1 * self.AR ** -0.25 / G0
        s = cfg.get('solar', {})
        self.f_panel = float(s.get('area_fraction', 0.8)) if s.get('enabled', True) else 0.0
        self.A_panel = self.f_panel * self.S
        self.eta_cell = float(s.get('cell_efficiency', 0.22))
        self.eta_mppt = float(s.get('mppt_efficiency', 0.97))
        self.camber = float(s.get('camber_factor', 0.9))
        self.m_panel = self.A_panel * float(s.get('areal_mass_kgm2', 0.45))
        self.p_peak = self.A_panel * self.eta_cell * 1000.0
        self.m_mppt = self.p_peak * float(s.get('mppt_kg_per_w', 0.00042))
        bt = cfg['battery']
        self.m_bat = float(bt['mass_kg'])
        self.e_spec = float(bt['specific_energy_whkg'])
        self.E = self.m_bat * self.e_spec * 3600.0
        self.eta_chg = float(bt.get('charge_efficiency', 0.95))
        self.eta_dis = float(bt.get('discharge_efficiency', 0.95))
        self.soc_min = float(bt.get('soc_min', 0.05))
        self.soc0 = float(bt.get('soc0', 1.0))
        self.c_max = float(bt.get('max_c_rate', 1.0))
        p = cfg['propulsion']
        self.eta_prop = float(p['eta_propeller'])
        self.eta_drive = float(p['eta_motor']) * float(p.get('eta_gearbox', 1.0)) * float(p.get('eta_controller', 0.97))
        self.n_motors = int(p.get('n_motors', 1))
        self.m_av = float(cfg['systems']['avionics_mass_kg'])
        self.p_av = float(cfg['systems']['avionics_power_w'])
        self.m_pl = float(cfg['systems']['payload_mass_kg'])
        self.p_pl = float(cfg['systems']['payload_power_w'])
        self.cl_mode = a.get('cl_mode', 'min_power')
        self.cl_user = float(a.get('cl_cruise', 0.8))
        m_wo_prop = self.m_struct + self.m_panel + self.m_mppt + self.m_bat + self.m_av + self.m_pl
        k_prop = float(p.get('kg_per_w', 0.008))
        margin = float(p.get('power_margin', 2.5))
        m = m_wo_prop
        for _ in range(60):
            mission = cfg.get('mission', {})
            hmax = float(mission.get('alt_max_m', mission.get('alt_m', 1000.0)))
            pl = self.p_level(m, hmax)[0] / (self.eta_prop * self.eta_drive)
            m_new = m_wo_prop + k_prop * pl * margin
            if abs(m_new - m) < 1e-12:
                break
            m = m_new
        self.m_prop = m - m_wo_prop
        self.mass = m
        self.p_motor_max = self.m_prop / k_prop if k_prop > 0 else 1e9

    def cl_cruise(self):
        if self.cl_mode == 'user':
            return min(self.cl_user, 0.95 * self.clmax)
        return min(math.sqrt(3.0 * self.cd0 / self.k), 0.9 * self.clmax)

    def p_level(self, m, h):
        rho = isa(h)[2]
        cl = self.cl_cruise()
        cd = self.cd0 + self.k * cl * cl
        v = math.sqrt(2.0 * m * G0 / (rho * self.S * cl))
        return m * G0 * v * cd / cl, v, cl, cd

    def breakdown(self):
        return [
            {'name': 'Structure', 'kg': self.m_struct},
            {'name': 'Solar cells', 'kg': self.m_panel},
            {'name': 'MPPT', 'kg': self.m_mppt},
            {'name': 'Battery', 'kg': self.m_bat},
            {'name': 'Propulsion', 'kg': self.m_prop},
            {'name': 'Avionics', 'kg': self.m_av},
            {'name': 'Payload', 'kg': self.m_pl},
        ]


def simulate(cfg, record=True, plane=None):
    pl = plane or Plane(cfg)
    ms = cfg['mission']
    day = float(ms['day_of_year'])
    lat = float(ms['latitude_deg'])
    days = float(ms.get('days', 2))
    dt = float(ms.get('dt_s', 300.0))
    t0 = float(ms.get('start_hour', 6.0))
    clear = float(ms.get('clearness', 1.0))
    h_min = float(ms.get('alt_m', 1000.0))
    alt_store = bool(ms.get('altitude_storage', False))
    h_max = float(ms.get('alt_max_m', h_min)) if alt_store else h_min
    m = pl.mass
    E = pl.E
    e = pl.soc0 * E
    h = h_min
    n = int(round(days * 24 * 3600 / dt))
    e_solar = e_used = e_waste = e_in = e_out = 0.0
    p_chg_max = pl.c_max * E / 3600.0
    min_soc = pl.soc0
    soc_full_time = 0.0
    S = {k: [] for k in ('t_h', 'hour', 'day', 'irr', 'p_solar', 'p_req', 'p_prop', 'soc', 'alt', 'v', 'sun_el', 'sun_az', 'mode', 'p_waste')}
    soc_day = []
    spd = max(1, int(round(24 * 3600 / dt)))
    for i in range(n):
        if i % spd == 0:
            soc_day.append(e / E if E > 0 else 0.0)
        th = t0 + i * dt / 3600.0
        hour = th % 24.0
        d = day + math.floor(th / 24.0)
        g, el, az = irradiance(((d - 1) % 365) + 1, hour, lat, h, clear)
        p_sun = pl.A_panel * pl.eta_cell * pl.eta_mppt * pl.camber * g
        p_mech, v, cl, cd = pl.p_level(m, h)
        p_prop = p_mech / (pl.eta_prop * pl.eta_drive)
        p_sys = pl.p_av + pl.p_pl
        mode = 'level'
        dh = 0.0
        net = p_sun - p_prop - p_sys
        waste = 0.0
        if net >= 0:
            room = (E - e) / pl.eta_chg / dt if E > 0 else 0.0
            p_c = min(net, p_chg_max / pl.eta_chg if E > 0 else 0.0, room)
            e_new = e + p_c * pl.eta_chg * dt
            e_in += p_c * dt
            rest = net - p_c
            if rest > 1e-12 and alt_store and h < h_max:
                rate = rest * pl.eta_prop * pl.eta_drive / (m * G0)
                dh = min(rate * dt, h_max - h)
                used = dh * m * G0 / (pl.eta_prop * pl.eta_drive) / dt
                rest -= used
                p_prop += used
                mode = 'climb'
            waste = max(0.0, rest)
            e = e_new
        else:
            if alt_store and h > h_min:
                sink = p_mech / (m * G0)
                dh = -min(sink * dt, h - h_min)
                frac = -dh / (sink * dt) if sink > 0 else 1.0
                need = p_sys - p_sun + (1.0 - frac) * p_prop
                p_prop = (1.0 - frac) * p_prop
                mode = 'glide'
            else:
                need = -net
            if need > 0:
                e -= need / pl.eta_dis * dt
                e_out += need / pl.eta_dis * dt
            else:
                room = (E - e) / pl.eta_chg / dt if E > 0 else 0.0
                p_c = min(-need, room)
                e += p_c * pl.eta_chg * dt
                e_in += p_c * dt
                waste = -need - p_c
        h += dh
        e_solar += p_sun * dt
        e_used += (p_prop + p_sys) * dt
        e_waste += waste * dt
        soc = e / E if E > 0 else 0.0
        min_soc = min(min_soc, soc)
        if E > 0 and soc >= 0.999 and p_sun > 0:
            soc_full_time += dt
        if record:
            S['t_h'].append(th - t0)
            S['hour'].append(hour)
            S['day'].append(d)
            S['irr'].append(g)
            S['p_solar'].append(p_sun)
            S['p_req'].append(p_prop + p_sys)
            S['p_prop'].append(p_prop)
            S['soc'].append(soc)
            S['alt'].append(h)
            S['v'].append(v)
            S['sun_el'].append(el / D2R)
            S['sun_az'].append(az / D2R)
            S['mode'].append(mode)
            S['p_waste'].append(waste)
    soc_end = e / E if E > 0 else 0.0
    soc_day.append(soc_end)
    survives = min_soc >= pl.soc_min - 1e-12
    cyc = soc_day[-1] - soc_day[-2] if len(soc_day) >= 2 else soc_end - pl.soc0
    perpetual = bool(survives and cyc >= -1e-3)
    p_mech, v, cl, cd = pl.p_level(m, h_min)
    endurance_h = None
    if not perpetual:
        endurance_h = None
        if record:
            for k, s in enumerate(S['soc']):
                if s < pl.soc_min:
                    endurance_h = S['t_h'][k]
                    break
    summary = {
        'perpetual': perpetual, 'survives': bool(survives), 'mass_kg': pl.mass, 'span_m': pl.b, 'wing_area_m2': pl.S, 'panel_area_m2': pl.A_panel,
        'p_peak_w': pl.p_peak, 'battery_wh': pl.E / 3600.0, 'min_soc': min_soc, 'soc_end': soc_end, 'soc_cycle_change': cyc,
        'night_margin': min_soc - pl.soc_min, 'excess_time_h': soc_full_time / 3600.0 / max(days, 1e-9), 'v_cruise_mps': v, 'cl_cruise': cl,
        'ld': cl / cd, 'p_level_w': p_mech / (pl.eta_prop * pl.eta_drive) + pl.p_av + pl.p_pl, 'e_solar_kwh': e_solar / 3.6e6,
        'e_used_kwh': e_used / 3.6e6, 'e_waste_kwh': e_waste / 3.6e6, 'e_bat_in_kwh': e_in / 3.6e6, 'e_bat_out_kwh': e_out / 3.6e6,
        'e_bat_delta_kwh': (e - pl.soc0 * E) / 3.6e6, 'alt_end_m': h, 'endurance_h': endurance_h, 'wing_loading': pl.mass * G0 / pl.S,
        'daily_irradiation_kwhm2': daily_extraterrestrial_horizontal(day, lat) / 3.6e6,
    }
    return {'summary': summary, 'series': S if record else None, 'mass': pl.breakdown()}


def margin(cfg):
    r = simulate(cfg, record=False)['summary']
    return r['night_margin'] if r['soc_cycle_change'] >= -1e-3 else min(r['night_margin'], r['soc_cycle_change'])


class Multicopter:
    def __init__(self, cfg):
        self.n = int(cfg['n_rotors'])
        self.D = float(cfg['rotor_diameter_m'])
        self.A = self.n * math.pi * self.D ** 2 / 4.0
        self.fm = float(cfg['figure_of_merit'])
        self.eta = float(cfg['eta_motor_esc'])
        self.cda = float(cfg['cd_area_m2'])
        self.p_av = float(cfg['avionics_power_w'])
        self.m_empty = float(cfg['empty_mass_kg'])
        self.m_bat = float(cfg['battery_mass_kg'])
        self.e_spec = float(cfg['specific_energy_whkg'])
        self.soc_use = float(cfg.get('usable_fraction', 0.8))
        self.h = float(cfg.get('alt_m', 0.0))

    def power(self, payload, v):
        rho = isa(self.h)[2]
        m = self.m_empty + self.m_bat + payload
        W = m * G0
        D = 0.5 * rho * v * v * self.cda
        T = math.sqrt(W * W + D * D)
        vh2 = T / (2.0 * rho * self.A)
        vi = math.sqrt((-v * v + math.sqrt(v ** 4 + 4.0 * vh2 * vh2)) / 2.0)
        return (T * vi / self.fm + D * v) / self.eta + self.p_av

    def hover_power(self, payload):
        return self.power(payload, 0.0)

    def energy_j(self):
        return self.m_bat * self.e_spec * 3600.0 * self.soc_use
