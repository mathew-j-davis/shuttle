import json
import os
from datetime import datetime, timedelta
from status_log import StatusLog

class FileTracker:
    def __init__(self, log_file_path, max_volume_per_day, max_count_per_day):
        self.status_log = StatusLog(log_file_path)
        self.max_volume_per_day = max_volume_per_day
        self.max_count_per_day = max_count_per_day
        self.log_data = self.status_log.get_log_data()

    def _reset_daily_counters(self):
        self.log_data["daily_file_count"] = 0
        self.log_data["daily_volume"] = 0
        self.log_data["last_reset_time"] = datetime.now().isoformat()
        self.status_log.update_log(-self.log_data["daily_file_count"], -self.log_data["daily_volume"])

    def update_counters(self, files_processed, volume_processed):
        last_reset_time = datetime.fromisoformat(self.log_data["last_reset_time"])
        if datetime.now() - last_reset_time >= timedelta(days=1):
            self._reset_daily_counters()

        new_file_count = self.log_data["daily_file_count"] + files_processed
        new_volume = self.log_data["daily_volume"] + volume_processed

        if new_file_count > self.max_count_per_day or new_volume > self.max_volume_per_day:
            raise Exception("Daily limit exceeded")

        self.log_data["daily_file_count"] = new_file_count
        self.log_data["daily_volume"] = new_volume
        self.status_log.update_log(files_processed, volume_processed)

    def get_log_data(self):
        return self.log_data

# Example usage
if __name__ == "__main__":
    tracker = FileTracker('/path/to/status_log.json', 1048576, 1000)  # Example limits
    # Simulate processing
    try:
        tracker.update_counters(10, 5000)  # Example processed files and volume
        print(tracker.get_log_data())
    except Exception as e:
        print(e)
