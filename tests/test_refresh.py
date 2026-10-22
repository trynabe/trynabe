import copy
import io
import json
import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRATCH = ROOT / 'test-results'
SCRATCH.mkdir(exist_ok=True)
sys.path.insert(0, str(ROOT / 'scripts'))
import refresh_profile as refresh


def calendar_html(total=10, missing_tooltip=False, duplicate=False):
    parts = [f'<h2 id="js-contribution-activity-description">{total}\n contributions in the last year</h2>']
    for i in range(365):
        day = (date(2025, 10, 23) + timedelta(days=i)).isoformat()
        count = 7 if i == 2 else 3 if i == 364 else 0
        level = 4 if count == 7 else 1 if count else 0
        cell = f'<td id="day-{i}" data-date="{day}" data-level="{level}"></td>'
        parts.append(cell)
        if duplicate and i == 0:
            parts.append(cell)
        if not (missing_tooltip and i == 2):
            parts.append(f'<tool-tip for="day-{i}">{count if count else "No"} contributions on October 22nd.</tool-tip>')
    return ''.join(parts)


class RefreshTests(unittest.TestCase):
    def test_reads_exact_github_counts_and_intensity_levels(self):
        days = refresh.parse_calendar(calendar_html())
        self.assertEqual(len(days), 365)
        self.assertEqual(sum(d['count'] for d in days), 10)
        self.assertEqual(days[2], {'date': '2025-10-25', 'count': 7, 'level': 4})
        self.assertEqual(days[-1]['level'], 1)

    def test_refuses_incomplete_duplicate_and_inconsistent_calendars(self):
        for html in (calendar_html(total=99), calendar_html(missing_tooltip=True), calendar_html(duplicate=True), '<html>Unavailable</html>'):
            with self.subTest(html=html[:100]), self.assertRaises(ValueError):
                refresh.parse_calendar(html)

    def test_fetch_uses_no_personal_credentials(self):
        with patch.object(refresh.urllib.request, 'urlopen', return_value=io.BytesIO(calendar_html().encode())) as request:
            self.assertEqual(len(refresh.fetch_calendar()), 365)
            req = request.call_args.args[0]
            self.assertEqual(req.full_url, 'https://github.com/users/trynabe/contributions')
            self.assertFalse(req.has_header('Authorization'))

    def test_no_change_retains_timestamp_and_files(self):
        days = refresh.parse_calendar(calendar_html())
        with tempfile.TemporaryDirectory(dir=SCRATCH) as directory:
            root = Path(directory)
            with patch.object(refresh, 'fetch_calendar', return_value=days):
                self.assertTrue(refresh.refresh(root))
                before = (root / 'contributions.json').read_bytes()
                self.assertFalse(refresh.refresh(root))
                self.assertEqual((root / 'contributions.json').read_bytes(), before)

    def test_new_activity_updates_counts_without_double_counting(self):
        days = refresh.parse_calendar(calendar_html())
        with tempfile.TemporaryDirectory(dir=SCRATCH) as directory:
            root = Path(directory)
            with patch.object(refresh, 'fetch_calendar', return_value=days):
                refresh.refresh(root)
            changed = copy.deepcopy(days)
            changed[-1].update(count=8, level=4)
            with patch.object(refresh, 'fetch_calendar', return_value=changed):
                self.assertTrue(refresh.refresh(root))
            data = json.loads((root / 'contributions.json').read_text(encoding='utf8'))
            self.assertEqual(data['stats']['total'], 15)
            self.assertEqual(data['days'][-1]['count'], 8)

    def test_fetch_failure_preserves_last_successful_assets(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as directory:
            root = Path(directory)
            (root / 'contributions.json').write_bytes(b'last successful snapshot')
            with patch.object(refresh, 'fetch_calendar', side_effect=ValueError('incomplete')), self.assertRaises(ValueError):
                refresh.refresh(root)
            self.assertEqual((root / 'contributions.json').read_bytes(), b'last successful snapshot')


if __name__ == '__main__':
    unittest.main()
