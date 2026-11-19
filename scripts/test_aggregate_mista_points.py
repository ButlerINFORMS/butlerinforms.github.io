import unittest

from aggregate_mista_points import AggregationError, aggregate_records, records_from_values


HEADERS = [
    "Submission ID",
    "Submitted at",
    "work_group",
    "expected_points",
    "First Name",
    "Last Name",
    "Butler Email",
    "Confirm Butler Email",
    "Public leaderboard choice",
    "Custom Alias",
    "Date of Completion",
    "Approve",
]


def make_row(
    submission_id,
    submitted_at,
    group,
    points,
    email,
    choice,
    alias,
    completion,
    approve="Yes",
    first_name="Ada",
    last_name="Student",
    confirm_email=None,
):
    return [
        submission_id,
        submitted_at,
        group,
        points,
        first_name,
        last_name,
        email,
        confirm_email or email,
        choice,
        alias,
        completion,
        approve,
    ]


class AggregateMistaPointsTests(unittest.TestCase):
    def test_sums_approved_points_by_email_round_and_category(self):
        records = records_from_values(
            [
                HEADERS,
                make_row(
                    "s1",
                    "2026-11-01 09:00",
                    "Learning",
                    "10",
                    " A@Butler.edu ",
                    "Display an alias",
                    "FirstAlias",
                    "2026-11-01",
                ),
                make_row(
                    "s2",
                    "2026-11-02 09:00",
                    "Applied",
                    "20",
                    "a@butler.edu",
                    "Display an alias",
                    "LaterAlias",
                    "2026-11-02",
                ),
                make_row(
                    "s3",
                    "2026-11-03 09:00",
                    "Skills",
                    "30",
                    "a@butler.edu",
                    "Display an alias",
                    "LaterAlias",
                    "2026-11-03",
                    approve="No",
                ),
            ]
        )

        result = aggregate_records(records)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].display_name, "FirstAlias")
        self.assertEqual(result[0].learning, 10)
        self.assertEqual(result[0].skills, 0)
        self.assertEqual(result[0].applied, 20)
        self.assertEqual(result[0].total, 30)

    def test_latest_opt_out_prevents_public_listing(self):
        records = records_from_values(
            [
                HEADERS,
                make_row(
                    "s1",
                    "2026-11-01 09:00",
                    "Learning",
                    "10",
                    "a@butler.edu",
                    "Display an alias",
                    "Alias",
                    "2026-11-01",
                ),
                make_row(
                    "s2",
                    "2026-11-02 09:00",
                    "Applied",
                    "20",
                    "a@butler.edu",
                    "Do not list me publicly",
                    "",
                    "2026-11-02",
                ),
            ]
        )

        self.assertEqual(aggregate_records(records), [])

    def test_approved_row_with_invalid_group_blocks_publication(self):
        records = records_from_values(
            [
                HEADERS,
                make_row(
                    "s1",
                    "2026-11-01 09:00",
                    "Activity",
                    "10",
                    "a@butler.edu",
                    "Display an alias",
                    "Alias",
                    "2026-11-01",
                ),
            ]
        )

        with self.assertRaisesRegex(AggregationError, "invalid work_group"):
            aggregate_records(records)

    def test_email_confirmation_mismatch_blocks_publication(self):
        records = records_from_values(
            [
                HEADERS,
                make_row(
                    "s1",
                    "2026-11-01 09:00",
                    "Learning",
                    "10",
                    "a@butler.edu",
                    "Display an alias",
                    "Alias",
                    "2026-11-01",
                    confirm_email="b@butler.edu",
                ),
            ]
        )

        with self.assertRaisesRegex(AggregationError, "does not match"):
            aggregate_records(records)

    def test_completion_outside_configured_round_blocks_publication(self):
        records = records_from_values(
            [
                HEADERS,
                make_row(
                    "s1",
                    "2026-11-01 09:00",
                    "Learning",
                    "10",
                    "a@butler.edu",
                    "Display an alias",
                    "Alias",
                    "2027-04-17",
                ),
            ]
        )

        with self.assertRaisesRegex(AggregationError, "outside the configured rounds"):
            aggregate_records(records)


if __name__ == "__main__":
    unittest.main()
