import datetime
import csv


class EventLogger:

    def __init__(self):
        self.events = []

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
        self._print(entry)

    def _print(self, entry):
        msg = f"[{entry['time']}] Train {entry['train_id']} {entry['event']} at {entry['location']}"
        if entry['reason']:
            msg += f" | Reason: {entry['reason']}"
        print(msg)

    def export(self, filename="train_logs.csv"):
        with open(filename, mode="w", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=["time", "train_id", "event", "location", "reason"])
            writer.writeheader()
            writer.writerows(self.events)