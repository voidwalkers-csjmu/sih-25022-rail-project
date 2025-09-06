from rail_sim.infrastructure import Station, Section
from rail_sim.trains import Train
from rail_sim.simulator import Simulator

# Define stations
stations = {
    "A": Station("A", has_loop=True, dwell_mean_s=20, name = 'Bangalore City'),
    "B": Station("B", has_loop=False, dwell_mean_s=30, name = 'Hubbali'),
}

# Define sections
sections = {
    ("A", "B"): Section("A", "B", length_km=10, vmax_kmph=60, line_type = 'single', clearance_buffer_s=15),
    ("B", "A"): Section("B", "A", length_km=10, vmax_kmph=60, line_type= 'single', clearance_buffer_s=15),
}

# Define trains
train1 = Train("T1", ["A", "B"], priority= 1)
train2 = Train("T2", ["A", "B"])

# Initialize simulator
sim = Simulator(stations, sections)
sim.trains = [train1, train2]

# Schedule departures
sim.schedule(0, "depart", train1)
sim.schedule(5, "depart", train2)  # Slightly delayed to cause a hold
sim.run()