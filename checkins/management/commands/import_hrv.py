from __future__ import annotations

# imports
import csv
from pathlib import Path
from typing import Optional
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from checkins.models import BiometricsDaily

# dynamically get the active User model
User = get_user_model()


# define custom management command for importing HRV data
class Command(BaseCommand):
    # short help text displayed in Django CLI
    help = "Import per-day HRV metrics (RMSSD/SDNN/resting HR) from CSV."

    # define command-line arguments
    def add_arguments(self, parser):
        # required CSV file path
        parser.add_argument("csv_path", type=str)

        # optional username for single-user imports
        parser.add_argument(
            "--username",
            type=str,
            default=None,
            help="Username to apply rows to if no 'username' column exists.",
        )

    # main logic executed when the command runs
    def handle(self, *args, **options):
        csv_path = Path(options["csv_path"])  # resolve path to CSV file
        default_username: Optional[str] = options["username"]

        # verify file existence
        if not csv_path.exists():
            raise CommandError(f"File not found: {csv_path}")

        # note: we don't preload a User object; we validate per-row below
        created, updated = 0, 0  # counters for reporting

        # open and read CSV file
        with csv_path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            # normalize field names (case-insensitive mapping)
            field_map = {k.lower().strip(): k for k in reader.fieldnames or []}

            # small helper to fetch values safely from CSV rows
            def get(row, key, default=None):
                src = field_map.get(key)
                if src is None:
                    return default
                v = row.get(src, "").strip()
                return v or default

            # perform database updates in a single transaction
            with transaction.atomic():
                for row in reader:
                    # determine username per row (from CSV or fallback)
                    username = get(row, "username", default_username)
                    if not username:
                        raise CommandError(
                            "No username provided in row and no --username fallback given."
                        )
                    try:
                        user = User.objects.get(username=username)
                    except User.DoesNotExist:
                        raise CommandError(f"User not found from CSV: {username}")

                    # parse date string (expected format: YYYY-MM-DD)
                    date_str = get(row, "date")
                    if not date_str:
                        self.stderr.write("Skipping row without date.")
                        continue

                    try:
                        from datetime import date as _date

                        y, m, d = map(int, date_str.split("-"))
                        day = _date(y, m, d)
                    except Exception as e:
                        self.stderr.write(f"Bad date '{date_str}': {e}")
                        continue

                    # helper for safe float parsing
                    def parse_float(x):
                        try:
                            return float(x) if x not in (None, "") else None
                        except Exception:
                            return None

                    # parse HRV and heart rate values
                    rmssd = parse_float(get(row, "rmssd"))
                    sdnn = parse_float(get(row, "sdnn"))
                    resting_hr = parse_float(get(row, "resting_hr"))

                    # upsert (update or create) biometrics record for the day
                    obj, is_created = BiometricsDaily.objects.update_or_create(
                        user=user,
                        date=day,
                        defaults=dict(rmssd=rmssd, sdnn=sdnn, resting_hr=resting_hr),
                    )

                    # increment counters for reporting
                    if is_created:
                        created += 1
                    else:
                        updated += 1

        # final success message printed to console
        self.stdout.write(
            self.style.SUCCESS(
                f"HRV import complete: {created} created, {updated} updated"
            )
        )
