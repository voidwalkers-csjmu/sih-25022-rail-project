import heapq
import math
import random
from typing import Dict, Tuple, List, Optional
from .trains import Train
from .infrastructure import Section, Station, Block, Disruption
from .logger import EventLogger
from .analytics import average_delay, throughput

class Simulator:
    # Constants for random event generation
    RANDOM_EVENT_CHECK_INTERVAL_S = 30  # Check for a random event every 30 minutes
    RANDOM_EVENT_PROBABILITY = 0.10       # 10% chance of an event happening at each check
    MIN_DISRUPTION_DURATION_S = 6       # 10 minutes
    MAX_DISRUPTION_DURATION_S = 10      # 60 minutes

    def __init__(self, stations: Dict[str, Station], sections: Dict[Tuple[str, str], Section]):
        self.time = 0
        self.event_queue: List[Tuple[int, int, str, Train, dict]] = []
        self.stations = stations
        self.sections = sections
        self.block_occupancy: Dict[str, str] = {}
        self.section_reservations: Dict[Tuple[str, str], str] = {}
        self.hold_events: Dict[str, int] = {}
        self.waiting_at_block: Dict[str, Tuple[Train, dict]] = {}
        self.waiting_for_platform: Dict[str, List[Tuple[Train, dict]]] = {} 
        self.trains: List[Train] = [] 
        self.logger = EventLogger()
        self.event_counter = 0
        self.is_disruption_active = False # ADD THIS LINE

    def schedule(self, time: int, event: str, train: Train, meta: dict):
        self.event_counter += 1
        heapq.heappush(self.event_queue, (time, self.event_counter, event, train, meta or {}))

    def run(self):
        while self.event_queue:
            try:
                time, _, event, train, meta = heapq.heappop(self.event_queue)
                self.time = time
                
                # BUGFIX: The previous check here was faulty and has been removed.
                
                handler = getattr(self, f"handle_{event}", None)
                if handler:
                    handler(train, meta)
                else:
                    # ADD A PRINT STATEMENT to see the mystery event
                    print(f"DEBUG: Unknown event found: '{event}' with meta: {meta}")
                    
                    # FIX THE LOGGER to handle events with no train
                    log_id = train.train_id if train else "System"
                    self.logger.log(log_id, 'UNKNOWN_EVENT', event, reason=f"Meta: {meta}")

                if self.trains and all(t.status == 'finished' for t in self.trains):
                    print("\nAll trains have finished their journeys. Ending simulation.")
                    break
            except IndexError:
                break
        self.report()

    def handle_generate_train(self, train: Train, meta: dict):
        """Adds a train to the active simulation and schedules its departure."""
        self.trains.append(train)
        self.logger.log(train.train_id, 'GENERATE_TRAIN', train.route[0], reason=f"Scheduled for departure at T={train.depart_time_s}s")
        self.schedule(self.time, 'depart', train, {})

    def _calculate_block_transit(
        self, train: Train, section: Section, block: Block, 
        entry_speed_ms: float, target_speed_ms: Optional[float] = None
    ) -> Tuple[int, float]:
        block_len_m = block.length_km * 1000
        transit_time = float('inf')
        
        if target_speed_ms is not None:

            max_speed_ms = section.vmax_kmph * (1000 / 3600)
            entry_speed_ms = min(entry_speed_ms, max_speed_ms)
            decel = train.base_deceleration_ms2
            dist_to_brake_m = (entry_speed_ms**2 - target_speed_ms**2) / (2 * decel) if decel > 0 else float('inf')

            if dist_to_brake_m >= block_len_m:
                exit_speed_sq = entry_speed_ms**2 - 2 * decel * block_len_m
                exit_speed_ms = math.sqrt(max(0, exit_speed_sq))
                transit_time = int((entry_speed_ms - exit_speed_ms) / decel) if decel > 0 else float('inf')
                return (max(1, transit_time), exit_speed_ms)
            else:
                cruise_dist_m = block_len_m - dist_to_brake_m
                time_to_cruise_s = cruise_dist_m / entry_speed_ms if entry_speed_ms > 0 else float('inf')
                time_to_brake_s = (entry_speed_ms - target_speed_ms) / decel if decel > 0 else float('inf')
                transit_time = int(time_to_cruise_s + time_to_brake_s)
                return (max(1, transit_time), target_speed_ms)

        max_speed_ms = min(train.vmax_kmph, section.vmax_kmph) * (1000 / 3600)
        accel = train.acceleration_ms2

        if entry_speed_ms >= max_speed_ms:
            transit_time = int(block_len_m / max_speed_ms) if max_speed_ms > 0 else float('inf')
            return (max(1, transit_time), max_speed_ms)

        dist_to_accel_m = (max_speed_ms**2 - entry_speed_ms**2) / (2 * accel) if accel > 0 else float('inf')

        if dist_to_accel_m >= block_len_m:
            exit_speed_sq = entry_speed_ms**2 + 2 * accel * block_len_m
            exit_speed_ms = math.sqrt(exit_speed_sq)
            transit_time = int((exit_speed_ms - entry_speed_ms) / accel) if accel > 0 else float('inf')
            return (max(1, transit_time), exit_speed_ms)
        else:
            time_to_accel_s = (max_speed_ms - entry_speed_ms) / accel if accel > 0 else float('inf')
            cruise_dist_m = block_len_m - dist_to_accel_m
            time_to_cruise_s = cruise_dist_m / max_speed_ms if max_speed_ms > 0 else float('inf')
            transit_time = int(time_to_accel_s + time_to_cruise_s)
            return (max(1, transit_time), max_speed_ms)

    def _get_single_line_path_sections(self, train: Train, start_section_idx: int) -> List[Tuple[str, str]]:
        path_sections = []
        for i in range(start_section_idx, len(train.route) - 1):
            u, v = train.route[i], train.route[i+1]
            section = self.sections.get((u, v))
            if not section or section.line_type != 'single':
                break
            path_sections.append((u, v))
            dest_station = self.stations.get(v)
            if dest_station and (dest_station.num_loops > 0 or dest_station.is_junction):
                break
        return path_sections

    def handle_depart(self, train: Train, meta: dict):
        section_idx = meta.get('section_idx', 0)
        
        if section_idx > 0:
            depart_station_code = train.route[section_idx]
            depart_station = self.stations.get(depart_station_code)
            if depart_station and train.train_id in depart_station.occupied_platforms:
                depart_station.occupied_platforms.remove(train.train_id)
                self.logger.log(train.train_id, 'DEPART_STATION', depart_station_code, reason="Platform freed")

                if self.waiting_for_platform.get(depart_station_code) and self.waiting_for_platform[depart_station_code]:
                    self.waiting_for_platform[depart_station_code].sort(key=lambda x: x[0].priority)
                    waiting_train, waiting_meta = self.waiting_for_platform[depart_station_code].pop(0)
                    self.logger.log(waiting_train.train_id, 'PLATFORM_AVAILABLE', depart_station_code, reason=f"Granted by priority {waiting_train.priority}")
                    self.schedule(self.time, 'enter_station', waiting_train, waiting_meta)
        else:
            train.status = 'running'
            self.logger.log(train.train_id, 'DEPART_JOURNEY_START', train.route[0])

        if len(train.route) > section_idx + 1:
            next_meta = {'section_idx': section_idx, 'block_idx': 0, 'entry_speed_ms': 0.0}
            self.schedule(self.time, 'enter_block', train, next_meta)

    def handle_enter_block(self, train: Train, meta: dict):
        section_idx, block_idx = meta['section_idx'], meta['block_idx']
        entry_speed_ms = meta.get('entry_speed_ms', 0.0)
        
        u, v = train.route[section_idx], train.route[section_idx + 1]
        section = self.sections.get((u, v))

        if not section or not section.blocks:
            self._move_to_next_section(train, section_idx, entry_speed_ms, meta)
            return
        
        # --- ADD THIS BLOCK ---
    # Log if the train is entering a disrupted section for the first time.
        if block_idx == 0 and section.active_disruptions:
            original_speed = section.original_vmax_kmph
            current_speed = section.vmax_kmph
            self.logger.log(
                train.train_id, 
                'AFFECTED_BY_DISRUPTION', 
                f"section {section.u}-{section.v}",
                f"Speed limited to {current_speed:.0f} km/h (original: {original_speed:.0f} km/h)"
            )
    # --- END OF ADDED BLOCK ---
        if block_idx == 0 and section.line_type == 'single':
            if not meta.get('reserved_path_sections'):
                path_sections = self._get_single_line_path_sections(train, section_idx)
                is_path_clear = True
                for sec_u, sec_v in path_sections:
                    if self.section_reservations.get((sec_u, sec_v)) or self.section_reservations.get((sec_v, sec_u)):
                        is_path_clear = False
                        break
                    section_to_check = self.sections.get((sec_u, sec_v))
                    for block in section_to_check.blocks:
                        if self.block_occupancy.get(block.block_id):
                            is_path_clear = False
                            break
                    if not is_path_clear:
                        break
                
                if not is_path_clear:
                    self.logger.log(train.train_id, 'HOLD_FOR_CROSSING', u, reason="Single-line path is reserved/occupied")
                    if train.train_id not in self.hold_events: # Start the hold timer
                        self.hold_events[train.train_id] = self.time
                    meta['entry_speed_ms'] = 0.0
                    self.schedule(self.time + 60, 'enter_block', train, meta)
                    return

                if path_sections:
                    dest = path_sections[-1][1]
                    self.logger.log(train.train_id, 'RESERVE_PATH', f"{u}->{dest}", reason="Path is clear")
                    for sec_u, sec_v in path_sections:
                        self.section_reservations[(sec_u, sec_v)] = train.train_id
                    meta['reserved_path_sections'] = path_sections

        block = section.blocks[block_idx]

        signal_aspect = 'green'
        if self.block_occupancy.get(block.block_id): signal_aspect = 'red'
        elif block_idx + 1 < len(section.blocks):
            if self.block_occupancy.get(section.blocks[block_idx + 1].block_id): signal_aspect = 'yellow'

        # The new, corrected line
        if signal_aspect == 'red':
            if train.train_id not in self.hold_events:
                self.hold_events[train.train_id] = self.time
                reason = "Signal is Red" if signal_aspect == 'red' else "Waiting at Yellow Signal"
                self.logger.log(train.train_id, 'HOLD', f"before {block.block_id}", reason=reason)
            self.waiting_at_block[block.block_id] = (train, meta)
            return

        if train.train_id in self.hold_events:
            wait_time = self.time - self.hold_events.pop(train.train_id)
            last_log = self.logger.get_last_event_for_train(train.train_id)
            if last_log and last_log['event'] == 'HOLD_FOR_CROSSING':
                train.delays["crossing"] += wait_time
            else:
                train.delay_s["signal"] += wait_time
            self.logger.log(train.train_id, 'RELEASE', f"from before {block.block_id}", reason=f"Waited {wait_time}s")

        self.block_occupancy[block.block_id] = train.train_id
        # NEW LOGIC: Only set a braking target if the train is actually moving.
        target_speed = None
        if signal_aspect == 'yellow' and entry_speed_ms > 0.1: # Check if speed > 0
            target_speed = 0.0
        run_time, exit_speed_ms = self._calculate_block_transit(train, section, block, entry_speed_ms, target_speed_ms=target_speed)
        
        exit_meta = meta.copy()
        exit_meta.update({'block_idx': block_idx, 'exit_speed_ms': exit_speed_ms})
        self.schedule(self.time + run_time, 'exit_block', train, exit_meta)

    def handle_exit_block(self, train: Train, meta: dict):
        section_idx, block_idx = meta['section_idx'], meta['block_idx']
        exit_speed_ms = meta.get('exit_speed_ms', 0.0)
        
        u, v = train.route[section_idx], train.route[section_idx + 1]
        section = self.sections[(u, v)]
        block = section.blocks[block_idx]

        self.logger.log(train.train_id, 'EXIT_BLOCK_FRONT', block.block_id)
        
        if exit_speed_ms > 0.1:
            clearance_time_s = max(1, int(train.length_m / exit_speed_ms))
        else:
            clearance_time_s = max(5, int(math.sqrt(2 * train.length_m / train.acceleration_ms2)))
        
        self.schedule(self.time + clearance_time_s, 'free_block', train, {'block_to_free': block, 'section': section, 'block_idx': block_idx})

        if block_idx + 1 < len(section.blocks):
            next_meta = meta.copy()
            next_meta.update({'block_idx': block_idx + 1, 'entry_speed_ms': exit_speed_ms})
            self.schedule(self.time, 'enter_block', train, next_meta)
        else:
            self._move_to_next_section(train, section_idx, exit_speed_ms, meta)

    def handle_free_block(self, train: Train, meta: dict):
        block = meta['block_to_free']
        section = meta['section']
        block_idx = meta['block_idx']

        if self.block_occupancy.get(block.block_id) == train.train_id:
            del self.block_occupancy[block.block_id]
            self.logger.log(train.train_id, 'FREE_BLOCK_REAR', block.block_id)

            if block_idx > 0:
                prev_block = section.blocks[block_idx - 1]
                if prev_block.block_id in self.waiting_at_block:
                    waiting_train, waiting_meta = self.waiting_at_block.pop(prev_block.block_id)
                    self.logger.log(waiting_train.train_id, 'SIGNAL_UPDATE', f"for {prev_block.block_id}", reason="Block ahead cleared")
                    self.schedule(self.time, 'resume_check', waiting_train, waiting_meta)
    
    def handle_resume_check(self, train: Train, meta: dict):
        self.logger.log(train.train_id, 'RESUME_CHECK', f"at block {meta['block_idx']}", reason="Re-evaluating signal")
        self.schedule(self.time, 'enter_block', train, meta)

    def _move_to_next_section(self, train: Train, current_section_idx: int, final_speed_ms: float, meta: dict):
        path_to_release = meta.get('reserved_path_sections')
        if path_to_release:
            u, v = path_to_release[-1]
            if v == train.route[current_section_idx + 1]:
                 self.logger.log(train.train_id, 'RELEASE_PATH', f"Path ending at {v}")
                 for sec_u, sec_v in path_to_release:
                     if self.section_reservations.get((sec_u, sec_v)) == train.train_id: del self.section_reservations[(sec_u, sec_v)]
                 meta['reserved_path_sections'] = None

        if current_section_idx + 1 >= len(train.route) - 1:
            self.schedule(self.time, 'arrive', train, meta)
        else:
            next_meta = meta.copy()
            next_meta.update({'section_idx': current_section_idx + 1, 'final_speed_ms': final_speed_ms})
            self.schedule(self.time, 'enter_station', train, next_meta)
    
    def handle_enter_station(self, train: Train, meta: dict):
        station_code = train.route[meta['section_idx']]
        station = self.stations.get(station_code)

        if train.train_id in self.hold_events:
            wait_time = self.time - self.hold_events.pop(train.train_id)
            train.delays["platform"] += wait_time
            self.logger.log(train.train_id, 'RELEASE_FROM_PLATFORM_HOLD', station_code, reason=f"Waited {wait_time}s")

        if len(station.occupied_platforms) < station.num_platforms:
            station.occupied_platforms.append(train.train_id)
            
            dwell = int(random.normalvariate(station.dwell_mean_s, station.dwell_std_dev_s))
            dwell = max(15, dwell)
            
            self.logger.log(train.train_id, 'ARRIVE_STATION', station_code, reason=f"Platform available, Dwell:{dwell}s")
            
            depart_meta = {'section_idx': meta['section_idx']}
            self.schedule(self.time + dwell, 'depart', train, depart_meta)
        else:
            if train.train_id not in self.hold_events:
                self.hold_events[train.train_id] = self.time
            
            if station_code not in self.waiting_for_platform:
                self.waiting_for_platform[station_code] = []
            
            self.waiting_for_platform[station_code].append((train, meta))
            self.logger.log(train.train_id, 'HOLD_FOR_PLATFORM', station_code, reason="All platforms occupied")

    # In simulator.py

    def handle_arrive(self, train: Train, meta: dict):
        dest_station_code = train.route[-1]
        dest_station = self.stations.get(dest_station_code)
        train.status = 'finished'

        # --- START OF NEW LOGIC ---
        if dest_station:
            # Step 1: Briefly occupy the platform to correctly model resource usage.
            # This is crucial for the logic to work.
            if train.train_id not in dest_station.occupied_platforms:
                dest_station.occupied_platforms.append(train.train_id)

            # Step 2: Immediately free the platform.
            if train.train_id in dest_station.occupied_platforms:
                dest_station.occupied_platforms.remove(train.train_id)
                self.logger.log(train.train_id, 'FREE_PLATFORM_ON_ARRIVAL', dest_station_code)

                # Step 3: Nudge the next waiting train, if any.
                waiting_list = self.waiting_for_platform.get(dest_station_code)
                if waiting_list:
                    waiting_list.sort(key=lambda x: x[0].priority)
                    waiting_train, waiting_meta = waiting_list.pop(0)
                    self.logger.log(waiting_train.train_id, 'PLATFORM_AVAILABLE', dest_station_code, f"Granted to {waiting_train.train_id}")
                    self.schedule(self.time, 'enter_station', waiting_train, waiting_meta)
        # --- END OF NEW LOGIC ---

        # Release any reserved single-line paths
        path_to_release = meta.get('reserved_path_sections')
        if path_to_release:
            self.logger.log(train.train_id, 'RELEASE_PATH', "Final release on arrival")
            for sec_u, sec_v in path_to_release:
                if self.section_reservations.get((sec_u, sec_v)) == train.train_id:
                    del self.section_reservations[(sec_u, sec_v)]

        self.logger.log(train.train_id, 'ARRIVE_JOURNEY_END', dest_station_code, f"Total delay={train.delay_s}s")
    # in simulator.py, after handle_arrive and before report

    def handle_start_disruption(self, train: Train, meta: dict):
        # When a disruption starts, flip the switch to ON
        # self.is_disruption_active = True # IMPORTANT
        
        disruption: Disruption = meta['disruption_data']
        section_key = (disruption.section_u, disruption.section_v)
        
        for key in [section_key, section_key[::-1]]:
            if key in self.sections:
                section = self.sections[key]
                section.active_disruptions.append(disruption)
                section.recalculate_vmax()
                # if section.original_vmax_kmph is None:
                #     section.original_vmax_kmph = section.vmax_kmph
                
                # section.vmax_kmph *= disruption.speed_factor
                self.logger.log("System", "DISRUPTION_START", f"{key[0]}-{key[1]}", f"Speed now {section.vmax_kmph:.0f} km/h")


    def handle_end_disruption(self, train: Train, meta: dict):
        # When a disruption ends, flip the switch to OFF
        # self.is_disruption_active = False # IMPORTANT

        # 
        disruption_to_end: Disruption = meta['disruption_data']
        section_key = (disruption_to_end.section_u, disruption_to_end.section_v)

        for key in [section_key, section_key[::-1]]:
            if key in self.sections:
                section = self.sections[key]
                # Remove the specific disruption from the list
                section.active_disruptions = [d for d in section.active_disruptions if d != disruption_to_end]
                # Ask the section to update its own speed
                section.recalculate_vmax()
                self.logger.log("System", "DISRUPTION_END", f"{key[0]}-{key[1]}", f"Speed now {section.vmax_kmph:.0f} km/h")
        
    def handle_check_for_random_event(self, train: Train, meta: dict):
        # FIRST, check if a disruption is already active. If so, do nothing.
        # if self.is_disruption_active:
        #     return

        # Always schedule the next check
        self.schedule(self.time + self.RANDOM_EVENT_CHECK_INTERVAL_S, 'check_for_random_event', None, {})

        if random.random() < self.RANDOM_EVENT_PROBABILITY:
            # The new, corrected filter that targets ANY section
            all_section_keys = [k for k, s in self.sections.items() if k[0] < k[1]]
            if not all_section_keys:
                return
            
            section_u, section_v = random.choice(all_section_keys)
            duration = random.randint(self.MIN_DISRUPTION_DURATION_S, self.MAX_DISRUPTION_DURATION_S)
            # print(f"DEBUG: New disruption created. Time={self.time}, Duration={duration}, End Time={self.time + duration}")
            speed_factor = round(random.uniform(0.2, 0.7), 2)
            
            disruption = Disruption(
                section_u=section_u, section_v=section_v,
                start_time_s=self.time, end_time_s=self.time + duration,
                speed_factor=speed_factor
            )

            self.logger.log("System", "RANDOM_EVENT", f"{section_u}-{section_v}", f"New disruption for {duration}s")
            
            self.schedule(self.time, 'start_disruption', None, {'disruption_data': disruption})
            self.schedule(self.time + duration, 'end_disruption', None, {'disruption_data': disruption})

    def report(self):
        print("\n" + "="*20 + " SIMULATION REPORT " + "="*20)
        
        all_trains_in_sim = sorted(self.trains, key=lambda t: t.train_id)
        finished_trains = [t for t in all_trains_in_sim if t.status == 'finished']
        
        print("\n--- Overall Summary ---")
        print(f"Total trains generated: {len(all_trains_in_sim)}")
        print(f"Finished trains: {len(finished_trains)}")
        print(f"Total simulation time: {self.time}s ({self.time/3600:.2f} hours)")

        # --- NEW: Throughput Calculation ---
        if self.time > 0:
            network_throughput = throughput(len(finished_trains), self.time)
            print(f"Network Throughput: {network_throughput:.2f} trains/hour")
        
        # --- NEW: Per-Train Delay Report ---
        if finished_trains:
            print("\n--- Per-Train Delay Report ---")
            total_system_delay = 0
            for train in finished_trains:
                total_delay = sum(train.delay_s.values())
                total_system_delay += total_delay
                
                # Create a formatted string for the breakdown, e.g., "Signal: 90s, Platform: 31s"
                delay_breakdown = ", ".join(
                    f"{reason.title()}: {time}s" for reason, time in train.delay_s.items() if time > 0
                )
                if not delay_breakdown:
                    delay_breakdown = "No delays"
                print(f"  - {train.train_id} (Priority: {train.priority}): {train.delay_s}s delay")
            # Using your analytics function for the average
            avg_delay = average_delay(finished_trains)
            print(f"\nAverage delay for finished trains: {avg_delay:.1f}s")
        
        unfinished_trains = [t for t in all_trains_in_sim if t.status != 'finished']
        if unfinished_trains:
            print("\n--- Unfinished Trains ---")
            for t in unfinished_trains:
                print(f"  - {t.train_id} (Status: {t.status})")

        self.logger.export("simulation_events.csv")
        print("\n[Logs saved to simulation_events.csv]")
        print("="*61)