  # throughput, utilization, delay reports
from typing import List
from trains import Train

def average_delay(trains: List[Train]) -> float:
    if not trains:
        return 0.0
    total = sum(t.delay_s for t in trains)
    return total / len(trains)

def throughput(num_trains: int, time_window_s: int) -> float:
    if time_window_s == 0:
        return 0.0
    return (num_trains * 3600) / time_window_s
 