"""
Created on Fri Sep 11 16:10:39 2026

@author: eneso
"""
PRESETS = [
    {
        'id': 'hale', 'name': 'HALE solar drone · 25 m span (Zephyr class)',
        'description': 'High-altitude pseudo-satellite: flies in the stratosphere for weeks, climbs on solar surplus by day and glides down at night to save battery energy.',
        'config': {
            'airframe': {'span_m': 25.0, 'aspect_ratio': 20.0, 'cd0': 0.012, 'oswald': 0.9, 'cl_max': 1.3, 'struct_mass_kg': 24.0, 'cl_mode': 'min_power'},
            'solar': {'enabled': True, 'area_fraction': 0.8, 'cell_efficiency': 0.26, 'mppt_efficiency': 0.97, 'camber_factor': 0.9, 'areal_mass_kgm2': 0.25, 'mppt_kg_per_w': 0.0002},
            'battery': {'mass_kg': 24.0, 'specific_energy_whkg': 435.0, 'charge_efficiency': 0.95, 'discharge_efficiency': 0.95, 'soc_min': 0.05, 'soc0': 0.6, 'max_c_rate': 0.5},
            'propulsion': {'eta_propeller': 0.85, 'eta_motor': 0.92, 'eta_gearbox': 0.98, 'eta_controller': 0.97, 'kg_per_w': 0.0025, 'power_margin': 2.0, 'n_motors': 2},
            'systems': {'avionics_mass_kg': 3.0, 'avionics_power_w': 40.0, 'payload_mass_kg': 5.0, 'payload_power_w': 50.0},
            'mission': {'day_of_year': 172, 'latitude_deg': 30.0, 'alt_m': 17000.0, 'alt_max_m': 21000.0, 'altitude_storage': True, 'days': 3, 'dt_s': 300.0, 'start_hour': 6.0, 'clearness': 1.0},
        },
    },
    {
        'id': 'skysailor', 'name': 'Solar UAV · 3.2 m span (Sky-Sailor class)',
        'description': 'Small solar-powered fixed-wing UAV like the ETH Zurich Sky-Sailor, which flew 27 hours non-stop in June 2008.',
        'config': {
            'airframe': {'span_m': 3.2, 'aspect_ratio': 12.9, 'cd0': 0.016, 'oswald': 0.9, 'cl_max': 1.2, 'k_struct': 0.44, 'cl_mode': 'min_power'},
            'solar': {'enabled': True, 'area_fraction': 0.66, 'cell_efficiency': 0.169, 'mppt_efficiency': 0.97, 'camber_factor': 0.9, 'areal_mass_kgm2': 0.42, 'mppt_kg_per_w': 0.00042},
            'battery': {'mass_kg': 1.05, 'specific_energy_whkg': 230.0, 'charge_efficiency': 0.95, 'discharge_efficiency': 0.95, 'soc_min': 0.05, 'soc0': 1.0, 'max_c_rate': 1.0},
            'propulsion': {'eta_propeller': 0.80, 'eta_motor': 0.85, 'eta_gearbox': 0.97, 'eta_controller': 0.97, 'kg_per_w': 0.008, 'power_margin': 2.5, 'n_motors': 1},
            'systems': {'avionics_mass_kg': 0.15, 'avionics_power_w': 1.5, 'payload_mass_kg': 0.05, 'payload_power_w': 0.5},
            'mission': {'day_of_year': 172, 'latitude_deg': 47.0, 'alt_m': 500.0, 'alt_max_m': 1500.0, 'altitude_storage': False, 'days': 2, 'dt_s': 300.0, 'start_hour': 8.0, 'clearness': 1.0},
        },
    },
    {
        'id': 'mapping', 'name': 'Mapping drone · 2.4 m span, battery only',
        'description': 'Electric survey drone without solar cells – the classic endurance question: how long can it map with one battery?',
        'config': {
            'airframe': {'span_m': 2.4, 'aspect_ratio': 9.0, 'cd0': 0.035, 'oswald': 0.85, 'cl_max': 1.3, 'k_struct': 0.6, 'cl_mode': 'min_power'},
            'solar': {'enabled': False, 'area_fraction': 0.0, 'cell_efficiency': 0.2, 'mppt_efficiency': 0.97, 'camber_factor': 0.9, 'areal_mass_kgm2': 0.42, 'mppt_kg_per_w': 0.00042},
            'battery': {'mass_kg': 1.2, 'specific_energy_whkg': 250.0, 'charge_efficiency': 0.95, 'discharge_efficiency': 0.95, 'soc_min': 0.15, 'soc0': 1.0, 'max_c_rate': 2.0},
            'propulsion': {'eta_propeller': 0.70, 'eta_motor': 0.85, 'eta_gearbox': 1.0, 'eta_controller': 0.97, 'kg_per_w': 0.008, 'power_margin': 3.0, 'n_motors': 1},
            'systems': {'avionics_mass_kg': 0.3, 'avionics_power_w': 6.0, 'payload_mass_kg': 0.6, 'payload_power_w': 8.0},
            'mission': {'day_of_year': 172, 'latitude_deg': 47.0, 'alt_m': 120.0, 'alt_max_m': 120.0, 'altitude_storage': False, 'days': 1, 'dt_s': 60.0, 'start_hour': 8.0, 'clearness': 1.0},
        },
    },
]

COPTER = {'n_rotors': 4, 'rotor_diameter_m': 0.38, 'figure_of_merit': 0.62, 'eta_motor_esc': 0.82, 'cd_area_m2': 0.035, 'avionics_power_w': 12.0, 'empty_mass_kg': 1.6, 'battery_mass_kg': 0.9, 'specific_energy_whkg': 220.0, 'usable_fraction': 0.8, 'alt_m': 300.0, 'payload_kg': 0.5, 'max_payload_kg': 2.0}


def preset(pid):
    for p in PRESETS:
        if p['id'] == pid:
            return p
    raise KeyError(pid)
