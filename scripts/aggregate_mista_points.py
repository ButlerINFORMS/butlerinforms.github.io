"""Aggregate approved MISTA points and publish opted-in totals to Google Sheets.

The script uses a Google service account supplied through
GOOGLE_APPLICATION_CREDENTIALS. Share the source sheet with that account as a
viewer and the leaderboard sheet as an editor. Keep the key file outside this
repository.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping, Sequence


SOURCE_SHEET_ID = "1HlXXvMf-PvvksYqv2HHyrZuFnmVuhZQCNoSbMyiqPHc"
LEADERBOARD_SHEET_ID = "1BlNN77ZmCUuLGggB5kmkws8XMzlvLSeqpZnkEQHzMjk"
SOURCE_WORKSHEET = "Sheet1"
LEADERBOARD_WORKSHEET = "Sheet1"

GROUPS = ("Learning", "Skills", "Applied")
ROUND_WINDOWS = (
    ("Fall 2026", date(2026, 8, 26), date(2026, 12, 23)),
    ("Spring 2027", date(2026, 12, 24), date(2027, 4, 16)),
)
OPT_IN_CHOICES = {
    "display my chosen name",
    "display an alias",
}
OPT_OUT_CHOICE = "do not list me publicly"
OUTPUT_HEADERS = [
    "Round",
    "Display Name",
    "Learning",
    "Skills",
    "Applied",
    "Total Points",
]
REQUIRED_HEADERS = {
    "submitted at",
    "work group",
    "expected points",
    "first name",
    "last name",
    "butler email",
    "confirm butler email",
    "public leaderboard choice",
    "custom alias",
    "date of completion",
    "approve",
}


class AggregationError(ValueError):
    """Raised when source data cannot be safely aggregated."""


@dataclass(frozen=True)
class LeaderboardRow:
    round_name: str
    display_name: str
    learning: int
    skills: int
    applied: int

    @property
    def total(self) -> int:
        return self.learning + self.skills + self.applied

    def as_values(self) -> list[Any]:
        return [
            self.round_name,
            self.display_name,
            self.learning,
            self.skills,
            self.applied,
            self.total,
        ]


def _normalized_header(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").replace("_", " ").strip()).casefold()


def _normalized_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def _normalized_email(value: Any) -> str:
    return _normalized_text(value).casefold()


def _parse_datetime(value: Any, *, field: str, row_number: int) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, date):
        parsed = datetime.combine(value, time.min)
    elif isinstance(value, (int, float, Decimal)):
        # Google Sheets date serials use 1899-12-30 as their epoch.
        parsed = datetime(1899, 12, 30) + timedelta(days=float(value))
    else:
        text = _normalized_text(value)
        if not text:
            raise AggregationError(f"Row {row_number}: {field} is required.")
        parsed = None
        for date_format in (
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%d",
            "%m/%d/%Y %H:%M:%S",
            "%m/%d/%Y %H:%M",
            "%m/%d/%Y",
        ):
            try:
                parsed = datetime.strptime(text, date_format)
                break
            except ValueError:
                continue
        if parsed is None:
            try:
                parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
            except ValueError as error:
                raise AggregationError(
                    f"Row {row_number}: invalid {field} value."
                ) from error
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


def _parse_points(value: Any, row_number: int) -> int:
    text = _normalized_text(value).replace(",", "")
    try:
        points = Decimal(text)
    except InvalidOperation as error:
        raise AggregationError(
            f"Row {row_number}: expected_points must be a whole number."
        ) from error
    if not points.is_finite() or points < 0 or points != points.to_integral_value():
        raise AggregationError(
            f"Row {row_number}: expected_points must be a non-negative whole number."
        )
    return int(points)


def records_from_values(values: Sequence[Sequence[Any]]) -> list[dict[str, Any]]:
    if not values:
        raise AggregationError("The source worksheet is empty.")
    headers = [_normalized_header(value) for value in values[0]]
    if not any(headers):
        raise AggregationError("The source worksheet has no header row.")
    if len(set(header for header in headers if header)) != len(
        [header for header in headers if header]
    ):
        raise AggregationError("The source worksheet has duplicate column headers.")
    missing_headers = REQUIRED_HEADERS.difference(headers)
    if missing_headers:
        missing = ", ".join(sorted(missing_headers))
        raise AggregationError(
            f"The source worksheet is missing required columns: {missing}."
        )

    records: list[dict[str, Any]] = []
    for source_row_number, row in enumerate(values[1:], start=2):
        if not any(_normalized_text(value) for value in row):
            continue
        record = {
            headers[index]: row[index] if index < len(row) else ""
            for index in range(len(headers))
            if headers[index]
        }
        record["__source_row_number__"] = source_row_number
        records.append(record)
    return records


def _field(record: Mapping[str, Any], name: str) -> Any:
    return record.get(_normalized_header(name), "")


def _round_for_date(completion_date: date, row_number: int) -> str:
    for round_name, start, end in ROUND_WINDOWS:
        if start <= completion_date <= end:
            return round_name
    raise AggregationError(
        f"Row {row_number}: completion date is outside the configured rounds."
    )


def aggregate_records(records: Sequence[Mapping[str, Any]]) -> list[LeaderboardRow]:
    """Return opted-in per-email, per-round totals without exposing email addresses."""
    identity_rows: dict[str, list[tuple[datetime, int, Mapping[str, Any]]]] = (
        defaultdict(list)
    )
    totals: dict[tuple[str, str], dict[str, int]] = defaultdict(
        lambda: {group: 0 for group in GROUPS}
    )
    seen_submission_ids: set[str] = set()

    for position, record in enumerate(records, start=2):
        row_number = int(record.get("__source_row_number__", position))
        submission_id = _normalized_text(_field(record, "Submission ID"))
        if submission_id:
            if submission_id in seen_submission_ids:
                raise AggregationError(
                    f"Row {row_number}: duplicate Submission ID; resolve before publishing."
                )
            seen_submission_ids.add(submission_id)

        email = _normalized_email(_field(record, "Butler Email"))
        confirmed_email = _normalized_email(_field(record, "Confirm Butler Email"))
        if not email or not confirmed_email or email != confirmed_email:
            raise AggregationError(
                f"Row {row_number}: Butler Email is missing or does not match its confirmation."
            )

        submitted_at = _parse_datetime(
            _field(record, "Submitted at"),
            field="Submitted at",
            row_number=row_number,
        )
        identity_rows[email].append((submitted_at, row_number, record))

        approval = _normalized_text(_field(record, "Approve")).casefold()
        if not approval:
            continue
        if approval not in {"yes", "no"}:
            raise AggregationError(
                f"Row {row_number}: Approve must be Yes, No, or blank."
            )
        if approval != "yes":
            continue

        group_value = _normalized_text(_field(record, "work_group"))
        group = next(
            (
                allowed
                for allowed in GROUPS
                if group_value.casefold() == allowed.casefold()
            ),
            None,
        )
        if group is None:
            raise AggregationError(
                f"Row {row_number}: approved row has an invalid work_group; "
                "use Learning, Skills, or Applied."
            )

        completion = _parse_datetime(
            _field(record, "Date of Completion"),
            field="Date of Completion",
            row_number=row_number,
        )
        round_name = _round_for_date(completion.date(), row_number)
        points = _parse_points(_field(record, "expected_points"), row_number)
        totals[(email, round_name)][group] += points

    leaderboard: list[LeaderboardRow] = []
    for (email, round_name), points_by_group in totals.items():
        rows = sorted(identity_rows[email], key=lambda item: (item[0], item[1]))
        latest_choice = ""
        latest_choice_record: Mapping[str, Any] | None = None
        first_alias = ""
        first_name = ""
        last_name = ""

        for _, _, record in rows:
            choice = _normalized_text(
                _field(record, "Public leaderboard choice")
            ).casefold()
            if choice:
                latest_choice = choice
                latest_choice_record = record
            alias = _normalized_text(_field(record, "Custom Alias"))
            if alias and not first_alias:
                first_alias = alias

        if latest_choice == OPT_OUT_CHOICE or latest_choice not in OPT_IN_CHOICES:
            continue
        if latest_choice == "display an alias":
            display_name = first_alias
        else:
            if latest_choice_record is None:
                continue
            first_name = _normalized_text(_field(latest_choice_record, "First Name"))
            last_name = _normalized_text(_field(latest_choice_record, "Last Name"))
            display_name = " ".join(part for part in (first_name, last_name) if part)

        if not display_name:
            continue
        leaderboard.append(
            LeaderboardRow(
                round_name=round_name,
                display_name=display_name,
                learning=points_by_group["Learning"],
                skills=points_by_group["Skills"],
                applied=points_by_group["Applied"],
            )
        )

    round_order = {name: index for index, (name, _, _) in enumerate(ROUND_WINDOWS)}
    return sorted(
        leaderboard,
        key=lambda row: (
            round_order[row.round_name],
            -row.total,
            row.display_name.casefold(),
        ),
    )


def _load_gspread_client(credentials_path: str) -> Any:
    try:
        import gspread
    except ImportError as error:
        raise RuntimeError(
            "Missing dependency. Install with: python -m pip install -r scripts\\requirements.txt"
        ) from error
    if not os.path.isfile(credentials_path):
        raise FileNotFoundError(
            "Google service-account credentials were not found. Set "
            "GOOGLE_APPLICATION_CREDENTIALS to the key-file path."
        )
    return gspread.service_account(filename=credentials_path)


def sync_sheets(
    *,
    source_sheet_id: str,
    destination_sheet_id: str,
    source_worksheet: str,
    destination_worksheet: str,
    credentials_path: str,
    dry_run: bool,
) -> list[LeaderboardRow]:
    client = _load_gspread_client(credentials_path)
    source = client.open_by_key(source_sheet_id).worksheet(source_worksheet)
    destination = client.open_by_key(destination_sheet_id).worksheet(
        destination_worksheet
    )
    records = records_from_values(source.get_all_values())
    leaderboard = aggregate_records(records)
    values = [OUTPUT_HEADERS] + [row.as_values() for row in leaderboard]

    if dry_run:
        print(
            f"Validated {len(records)} intake rows; "
            f"would write {len(leaderboard)} leaderboard rows."
        )
        for row in values:
            print("\t".join(str(value) for value in row))
        return leaderboard

    previous_values = destination.get_all_values()
    last_row = max(1, len(previous_values))
    destination.batch_clear([f"A1:F{last_row}"])
    destination.update(
        range_name=f"A1:F{len(values)}",
        values=values,
        value_input_option="USER_ENTERED",
    )
    print(f"Published {len(leaderboard)} leaderboard rows.")
    return leaderboard


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Aggregate approved MISTA points and update the private leaderboard sheet."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and preview without writing.",
    )
    parser.add_argument("--source-id", default=SOURCE_SHEET_ID)
    parser.add_argument("--destination-id", default=LEADERBOARD_SHEET_ID)
    parser.add_argument("--source-tab", default=SOURCE_WORKSHEET)
    parser.add_argument("--destination-tab", default=LEADERBOARD_WORKSHEET)
    args = parser.parse_args(argv)

    credentials_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "")
    try:
        sync_sheets(
            source_sheet_id=args.source_id,
            destination_sheet_id=args.destination_id,
            source_worksheet=args.source_tab,
            destination_worksheet=args.destination_tab,
            credentials_path=credentials_path,
            dry_run=args.dry_run,
        )
    except (AggregationError, FileNotFoundError, RuntimeError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
