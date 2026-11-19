# MISTA points aggregation

`aggregate_mista_points.py` reads the Tally intake worksheet, sums `expected_points` only for rows marked `Approve = Yes`, and writes one public-listing row per opted-in email and round. The output contains no email addresses or evidence links.

The script normalizes email addresses (trim + lowercase), requires the confirmation field to match, groups by email rather than alias, and uses the earliest nonblank `Custom Alias` for alias display. The most recent nonblank leaderboard choice controls whether a participant is listed; an explicit opt-out suppresses all their rows. Completion dates determine Fall 2026 or Spring 2027.

## Setup

1. Enable the Google Sheets API in a Google Cloud project and create a service account.
2. Keep its JSON key outside this repository and set `GOOGLE_APPLICATION_CREDENTIALS` to its path.
3. Restrict `MISTA_Points_Tracking` to intended reviewers; it contains private submission details and evidence links. Then share it with the service-account email as a viewer and `MISTA_Leaderboard` as an editor. Keep the leaderboard's sharing settings unchanged unless public access is explicitly approved.
4. Install the dependency:

   ```powershell
   python -m pip install -r scripts\requirements.txt
   ```

5. Preview first, then publish:

   ```powershell
   python scripts\aggregate_mista_points.py --dry-run
   python scripts\aggregate_mista_points.py
   ```

The script refuses to publish if an approved row has an invalid category, mismatched email confirmation, invalid point value, duplicate submission ID, or completion date outside the configured rounds. Correct the intake data and preview again. Update `ROUND_WINDOWS` before using it for later semesters.

Run the unit tests with:

```powershell
python -m unittest discover -s scripts -p "test_*.py"
```
