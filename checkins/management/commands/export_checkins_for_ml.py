from django.core.management.base import BaseCommand
from checkins.models import CheckIn
import csv
from pathlib import Path


class Command(BaseCommand):
    """
    Management command to export check-in data to a CSV file
    for later use in simple ML experiments (offline training).
    """

    help = "Export check-ins into checkins_dataset.csv for ML training."

    def handle(self, *args, **options) -> None:
        """
        Handle is called when the command is executed.
        It writes a CSV file with one row per CheckIn instance.
        """
        # define the output file path in the project root directory
        output_path = Path("checkins_dataset.csv")

        # open the CSV file for writing (overwrites if it already exists)
        with output_path.open("w", newline="") as f:
            writer = csv.writer(f)

            # write CSV header row (column names)
            writer.writerow(
                [
                    "mood",  # integer mood rating (e.g. 1–5)
                    "status",  # string status (e.g. 'ok', 'at_risk', 'blocked')
                    "hrv_rmssd",  # HRV RMSSD in ms (can be blank)
                    "completed",  # label: 1 if OK/completed, 0 otherwise
                ]
            )

            # iterate through all CheckIn records in the database
            for chk in CheckIn.objects.all():
                # define the binary label for ML:
                # 1 = OK/completed, 0 = not-ok (at risk, blocked, etc.)
                completed = 1 if chk.status == "ok" else 0

                # safely handle optional HRV field (None -> empty string)
                hrv_value = (
                    chk.hrv_rmssd if getattr(chk, "hrv_rmssd", None) is not None else ""
                )

                # write one CSV row per check-in
                writer.writerow(
                    [
                        chk.mood,
                        chk.status,
                        hrv_value,
                        completed,
                    ]
                )

        # print success message in the terminal
        self.stdout.write(
            self.style.SUCCESS(
                f"Export complete! File created: {output_path.resolve()}"
            )
        )
