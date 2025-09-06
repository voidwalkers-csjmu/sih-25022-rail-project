from dataclasses import dataclass, field
from typing import List, Optional

# This Disruption class is correctly placed at the top.
@dataclass
class Disruption:
    """A simple data class to hold information about a network disruption."""
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
    
    # --- MODIFICATIONS FOR ROBUST DISRUPTION HANDLING ---
    
    # CHANGED: This now stores the permanent, true original speed.
    original_vmax_kmph: Optional[float] = field(init=False, default=None)
    
    # This list correctly tracks active disruptions.
    active_disruptions: List[Disruption] = field(default_factory=list)

    # ADDED: A special method to set the original speed after the object is created.
    def __post_init__(self):
        """Sets the original_vmax_kmph once, after the object is initialized."""
        self.original_vmax_kmph = self.vmax_kmph

    # ADDED: The core logic for recalculating the section's speed.
    def recalculate_vmax(self):
        """
        Calculates the current maximum speed based on the most severe
        active disruption on this section.
        """
        if not self.active_disruptions:
            # If no disruptions are active, restore the true original speed.
            self.vmax_kmph = self.original_vmax_kmph
            return

        # Find the lowest speed_factor (i.e., the biggest speed reduction).
        most_severe_factor = min(d.speed_factor for d in self.active_disruptions)
        
        # Apply the most severe disruption to the true original speed.
        self.vmax_kmph = self.original_vmax_kmph * most_severe_factor

