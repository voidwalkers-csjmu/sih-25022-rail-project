import datetime
import csv
from typing import Dict, List, Any # It's good practice to import types

class EventLogger:

    def __init__(self):
        self.events = []
        self.events_by_train: Dict[str, List[Dict[str, Any]]] = {}


    def log(self, train_id, event_type, location, reason=None):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = {
        "time": timestamp,
        "train_id": train_id,
        "event": event_type,
        "location": location,
        "reason": reason
        }
        self.events.append(entry)
        if train_id not in self.events_by_train:
            self.events_by_train[train_id] = []
        self.events_by_train[train_id].append(entry)
        self._print(entry)

    def _print(self, entry):
        msg = f"[{entry['time']}] Train {entry['train_id']} {entry['event']} at {entry['location']}"
        if entry['reason']:
            msg += f" | Reason: {entry['reason']}"
        print(msg)

    def get_last_event_for_train(self, train_id):
        """
        Returns the most recent event log object for a given train.
        Returns None if no events are found for that train.
        """
        if train_id in self.events_by_train and self.events_by_train[train_id]:
            return self.events_by_train[train_id][-1]
        return None
    
    def export(self, filename="train_logs.csv"):
        with open(filename, mode="w", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=["time", "train_id", "event", "location", "reason"])
            writer.writeheader()
            writer.writerows(self.events)