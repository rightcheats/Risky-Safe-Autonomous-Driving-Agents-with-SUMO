import csv
from pathlib import Path

class CsvExporter:
    """
    Exports csvs to csv_results/
    """
    def to_file(self, path: str, headers: list[str], rows: list[list]):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            writer.writerows(rows)