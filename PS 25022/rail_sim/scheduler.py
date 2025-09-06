 # scheduling logic (conflict resolution, crossing rules)
from infrastructure import Station, Section
from trains import Train

def can_enter_section(train: Train, section: Section, occupied: bool) -> bool:
    """Simple rule: if section is occupied, train must wait."""
    if occupied:
        return False
    return True

def decide_loop_use(train: Train, station: Station, higher_priority_train: bool) -> bool:
    """If a higher-priority train needs the main line, move to loop."""
    if station.has_loop and higher_priority_train:
        return True
    return False
