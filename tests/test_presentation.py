"""Display formatting cannot reinterpret timezone-free history or change IDs."""
import unittest
from paperbuilder.presentation import format_timestamp

class TimestampTests(unittest.TestCase):
    def test_aware_offsets_display_explicit_utc(self):
        self.assertEqual(format_timestamp('2026-10-25T18:46:47.500652+05:30'),
                         '25 Oct 2026 · 13:16 UTC')
        self.assertEqual(format_timestamp('2026-10-25T13:16:47Z'),
                         '25 Oct 2026 · 13:16 UTC')

    def test_unknown_or_naive_values_stay_verbatim(self):
        for value in ('unknown', '2026-10-25T13:16:47', '2026-99-99', ''):
            self.assertEqual(format_timestamp(value), value)
