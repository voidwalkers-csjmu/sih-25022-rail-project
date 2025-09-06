import os
from .simulator import Simulator
from .utils import generate_blocks_for_infrastructure
from .data_loader import load_stations, load_sections, load_trains

# Define the base directory for data files
BASE = os.path.join(os.path.dirname(__file__), 'data')

def run_scenario():
    """Main function to set up and run the simulation."""
    
    # --- Step 1: Load all raw data ---
    stations = load_stations(os.path.join(BASE, 'stations.csv'))
    sections = load_sections(os.path.join(BASE, 'sections.csv'))
    # This list now represents all possible trains for the scenario
    all_possible_trains = load_trains(os.path.join(BASE, 'trains.csv'))

    # --- Step 2: Dynamically generate the blocks for the infrastructure ---
    generate_blocks_for_infrastructure(sections, all_possible_trains)

    # --- Step 3: Initialize and run the simulation ---
    # The simulator now starts with an empty list of active trains
    sim = Simulator(stations, sections)
    
    # MODIFIED: Schedule a 'generate_train' event for each train
    # This will introduce them into the simulation at their departure time.
    for t in all_possible_trains:
        sim.schedule(t.depart_time_s, 'generate_train', t, {})

    sim.run()

if __name__ == "__main__":
    run_scenario()