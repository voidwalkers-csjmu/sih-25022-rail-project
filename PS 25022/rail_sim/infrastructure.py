# rail_sim/infrastructure.py

from dataclasses import dataclass, field
from typing import List, Optional

# MOVED: Disruption dataclass now lives here to break the circular import.
@dataclass
class Disruption:
    section_u: str
    section_v: str
    start_time_s: int
    end_time_s: int
    speed_factor: float

@dataclass
class Block:
    """Represents a small, fixed-length piece of track protected by a signal."""
    block_id: str
    length_km: float
    signal_state: str = 'green'

@dataclass
class Station:
    code: str
    name: str
    has_loop: bool = True
    num_loops: int = 1
    num_platforms: int = 1
    max_train_len_m: int = 700
    is_junction: bool = False
    dwell_mean_s: int = 60
    dwell_std_dev_s: int = 5 
    occupied_platforms: List[str] = field(default_factory=list)

@dataclass
class Section:
    u: str
    v: str
    line_type: str
    length_km: float
    vmax_kmph: float
    signalling: str = "absolute"
    gradient: float = 0.0
    blocks: List[Block] = field(default_factory=list)
    # Fields to handle disruptions correctly
    original_vmax_kmph: Optional[float] = None
    active_disruptions: List[Disruption] = field(default_factory=list)