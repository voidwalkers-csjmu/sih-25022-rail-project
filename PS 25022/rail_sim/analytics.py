  # throughput, utilization, delay reports
from typing import List
from .trains import Train

def average_delay(trains: List[Train]) -> float:
    """Calculates the average total delay for a list of trains."""
    if not trains:
        return 0.0
    
    # CHANGED: This now correctly sums the values from the delay dictionary for each train.
    total_delay = sum(sum(t.delay_s.values()) for t in trains)
    
    return total_delay / len(trains)

def throughput(num_trains: int, time_window_s: int) -> float:
    if time_window_s == 0:
        return 0.0
    return (num_trains * 3600) / time_window_s
 