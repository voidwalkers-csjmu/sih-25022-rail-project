# rail_sim/data_loader.py

import csv
from typing import Dict, Tuple, List
# MODIFIED: Import Disruption from infrastructure now
from .infrastructure import Station, Section, Disruption
from .trains import Train
from dataclasses import replace

# REMOVED: The Disruption dataclass definition was moved to infrastructure.py

def load_stations(path: str) -> Dict[str, Station]:
    """Loads station data from a CSV file."""
    stations = {}
    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for r in reader:
            stations[r['code']] = Station(
                code=r['code'],
                name=r['name'],
                has_loop=r['has_loop'].strip().lower() in ('true','1','yes'),
                num_loops=int(r.get('num_loops') or 1),
                num_platforms=int(r.get('num_platforms') or 1),
                max_train_len_m=int(r.get('max_train_len_m') or 700),
                is_junction=r.get('is_junction','False').strip().lower() in ('true','1','yes'),
                dwell_mean_s=int(r.get('dwell_mean_s') or 60),
                dwell_std_dev_s=int(r.get('dwell_std_dev_s') or 5)
            )
    return stations

def load_sections(path: str) -> Dict[Tuple[str,str], Section]:
    """Loads track section data from a CSV file."""
    sections = {}
    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for r in reader:
            sec = Section(
                u=r['u'],
                v=r['v'],
                line_type=r['line_type'],
                length_km=float(r['length_km']),
                vmax_kmph=float(r['vmax_kmph']),
                signalling=r.get('signalling','absolute'),
                gradient=float(r.get('gradient', 0.0))
            )
            sections[(sec.u, sec.v)] = sec
            if sec.line_type == 'double':
                sections[(sec.v, sec.u)] = replace(sec, u=sec.v, v=sec.u, blocks=[])
    return sections

def load_trains(path: str) -> List[Train]:
    """Loads train data from a CSV file."""
    trains = []
    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for r in reader:
            route = r['route'].split('|')
            trains.append(Train(
                train_id=r['train_id'],
                category=r['category'],
                priority=int(r['priority']),
                vmax_kmph=float(r['vmax_kmph']),
                acceleration_ms2=float(r['acceleration_ms2']),
                base_deceleration_ms2=float(r['base_deceleration_ms2']),
                length_m=int(r['length_m']),
                route=route,
                depart_time_s=int(r.get('depart_time_s') or 0)
            ))
    return trains

def load_disruptions(path: str) -> List[Disruption]:
    """Loads disruption events from a CSV file."""
    disruptions = []
    try:
        with open(path, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for r in reader:
                disruptions.append(Disruption(
                    section_u=r['section_u'],
                    section_v=r['section_v'],
                    start_time_s=int(r['start_time_s']),
                    end_time_s=int(r['end_time_s']),
                    speed_factor=float(r['speed_factor'])
                ))
    except FileNotFoundError:
        print(f"Info: Disruption file not found at {path}. Running without scheduled disruptions.")
    return disruptions