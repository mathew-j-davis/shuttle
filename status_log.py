import json
import os
from datetime import datetime

class StatusLog:
    def __init__(self, log_file_path):
        self.log_file_path = log_file_path
        self.log_data = self._read_log()

    def _read_log(self):
        if not os.path.exists(self.log_file_path):
            return {"last_run_time": None, "total_files_processed": 0, "total_volume_processed": 0}
        with open(self.log_file_path, 'r') as file:
            return json.load(file)

    def update_log(self, files_processed, volume_processed):
        self.log_data["last_run_time"] = datetime.now().isoformat()
        self.log_data["total_files_processed"] += files_processed
        self.log_data["total_volume_processed"] += volume_processed
        self._write_log()

    def _write_log(self):
        with open(self.log_file_path, 'w') as file:
            json.dump(self.log_data, file)

    def get_log_data(self):
        return self.log_data

# Example usage
if __name__ == "__main__":
    status_log = StatusLog('/path/to/log_file.json')
    # Simulate processing
    files_processed = 10
    volume_processed = 5000  # in bytes
    status_log.update_log(files_processed, volume_processed)
    print(status_log.get_log_data())
