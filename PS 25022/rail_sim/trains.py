from dataclasses import dataclass
from typing import List

@dataclass
class Train:
    train_id: str
    category: str
    priority: int
    vmax_kmph: float
    # ADDED: The train's acceleration capability in meters/sec^2
    # A powerful passenger train might be ~0.5, a heavy goods train ~0.2
    acceleration_ms2: float
    base_deceleration_ms2: float
    length_m: int # ADDED: Length of trains in meters
    route: List[str]
    depart_time_s: int = 0
    # REMOVED: These will be managed in the simulator's meta dictionary
    # current_index: int = 0 
    delay_s: int = 0
    status: str = "waiting"