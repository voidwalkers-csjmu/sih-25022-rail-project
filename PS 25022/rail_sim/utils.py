import math
from typing import List, Dict
from .infrastructure import Section, Block  # CHANGED: Added Block to the import
from .trains import Train

# Constants
GRAVITY_MS2 = 9.81

def calculate_min_block_length_m(train: Train, section: Section) -> float:
    """
    Calculates the minimum safe block length in meters based on physics
    for a given train and section profile.
    """
    # --- Step 1: Get Initial Values and Convert Units ---
    vmax_ms = section.vmax_kmph * (1000 / 3600)  # Convert km/h to m/s
    reaction_time_s = 2.5  # Standard 2.5 second driver reaction time
    safety_margin_m = 200  # 200-meter safety buffer

    # --- Step 2: Calculate Effective Deceleration ---
    gradient_angle = math.atan(section.gradient / 100.0)
    gradient_effect = GRAVITY_MS2 * math.sin(gradient_angle)
    
    # Effective deceleration = train's power - slope's effect.
    # A downhill slope (negative gradient) works against the brakes.
    effective_deceleration = train.base_deceleration_ms2 - gradient_effect
    
    # Ensure deceleration is always a positive value to avoid errors.
    effective_deceleration = max(effective_deceleration, 0.1)

    # --- Step 3: Calculate Distances ---
    reaction_distance_m = vmax_ms * reaction_time_s
    braking_distance_m = (vmax_ms ** 2) / (2 * effective_deceleration)

    # --- Step 4: Final Calculation ---
    total_stopping_distance = reaction_distance_m + braking_distance_m
    required_block_length = total_stopping_distance + safety_margin_m

    return round(required_block_length)

def generate_blocks_for_infrastructure(sections: Dict, trains: List[Train]):
    """
    Post-processes the loaded sections to dynamically create the blocks
    based on worst-case train performance.
    """
    print("Generating signal blocks for all sections...")
    for section_key, section in sections.items():
        if section.signalling == 'automatic':
            # Find the worst-case train for this section (the one needing the longest stopping distance)
            worst_case_length = 0
            for train in trains:
                # A simple check: does the train's max speed fit the section's speed limit?
                if train.vmax_kmph >= section.vmax_kmph:
                    length = calculate_min_block_length_m(train, section)
                    if length > worst_case_length:
                        worst_case_length = length

            # If no suitable train was found, use a default safe value
            if worst_case_length == 0:
                worst_case_length = 1000 # Default to 1km blocks

            # Now, divide the section into blocks of this calculated length
            num_blocks = math.ceil(section.length_km * 1000 / worst_case_length)
            block_length_km = section.length_km / num_blocks

            for i in range(num_blocks):
                block_id = f"{section.u}-{section.v}-B{i+1}"
                section.blocks.append(Block(block_id=block_id, length_km=block_length_km))
    print("Block generation complete.")
