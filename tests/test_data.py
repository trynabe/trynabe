import copy
import importlib.util
import io
import json
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('update', ROOT / 'scripts/update_contributions.py')
update = importlib.util.module_from_spec(spec)
spec.loader.exec_module(update)


class DataTests(unittest.TestCase):
    def test_missing_calendar_day_breaks_streak(self):
        stats = update.compute_stats([{'date': '2026-02-27', 'count': 2}, {'date': '2026-03-01', 'count': 3}])
        self.assertEqual(stats['longestStreak'], 1)
        self.assertEqual(stats['currentStreak'], 1)

    def test_duplicate_dates_are_summed_and_sorted(self):
        stats = update.compute_stats([{'date': '2026-10-20', 'count': 2}, {'date': '2026-10-19', 'count': 1}, {'date': '2026-10-20', 'count': 3}])
        self.assertEqual(stats['total'], 6)
        self.assertEqual(stats['busiestCount'], 5)
        self.assertEqual(stats['longestStreak'], 2)
        self.assertEqual(stats['startDate'], '2026-10-19')

    def test_zero_calendar_has_no_busiest_day(self):
        stats = update.compute_stats([{'date': '2026-10-20', 'count': 0}])
        self.assertIsNone(stats['busiestDate'])
        self.assertEqual(stats['currentStreak'], 0)

    def test_impossible_date_rejected(self):
        with self.assertRaises(ValueError):
            update.compute_stats([{'date': '2026-02-30', 'count': 1}])

    def test_empty_calendar_is_safe(self):
        self.assertEqual(update.compute_stats([])['total'], 0)

    def test_yesterday_streak_and_leap_day(self):
        days = [{'date': '2024-02-28', 'count': 1}, {'date': '2024-02-29', 'count': 4}, {'date': '2024-03-01', 'count': 0}]
        stats = update.compute_stats(days)
        self.assertEqual(stats['longestStreak'], 2)
        self.assertEqual(stats['currentStreak'], 2)
        self.assertEqual(stats['currentTo'], '2024-02-29')

    def api(self, *, login='trynabe', total=3, count=3):
        return {'data': {'user': {'login': login, 'contributionsCollection': {'contributionCalendar': {
            'totalContributions': total, 'weeks': [{'contributionDays': [{'date': '2026-10-20', 'contributionCount': count, 'contributionLevel': 'FIRST_QUARTILE'}]}]
        }}}}}

    def fetch(self, response):
        with patch.object(update.urllib.request, 'urlopen', return_value=io.BytesIO(json.dumps(response).encode())):
            return update.fetch_github('trynabe', 'test-token-not-real')

    def test_graphql_rejects_wrong_account(self):
        with self.assertRaises(RuntimeError):
            self.fetch(self.api(login='somebody-else'))

    def test_calendar_includes_anonymized_private_counts_without_double_counting(self):
        raw=self.api(total=312,count=312)
        collection=raw['data']['user']['contributionsCollection']
        collection['restrictedContributionsCount']=86
        collection['hasAnyRestrictedContributions']=True
        coverage={}
        with patch.object(update.urllib.request,'urlopen',return_value=io.BytesIO(json.dumps(raw).encode())):
            days=update.fetch_github('trynabe','test-token-not-real',coverage=coverage)
        self.assertEqual(sum(day['count'] for day in days),312)
        self.assertEqual(coverage['anonymizedPrivateContributions'],86)
        self.assertTrue(coverage['includesAnonymizedPrivate'])

    def test_graphql_rejects_total_mismatch(self):
        with self.assertRaises(RuntimeError):
            self.fetch(self.api(total=99))

    def test_graphql_rejects_negative_count(self):
        with self.assertRaises((ValueError, RuntimeError)):
            self.fetch(self.api(count=-1))

    def test_graphql_errors_are_not_data(self):
        with self.assertRaises(RuntimeError):
            self.fetch({'errors': [{'message': 'Resource inaccessible'}], 'data': None})

    def test_graphql_valid_data_and_safe_svg(self):
        days = self.fetch(self.api())
        self.assertEqual(days, [{'date': '2026-10-20', 'count': 3, 'level': 1}])
        svg = update.render_svg(days, update.compute_stats(days), username='A&B<demo>', demo=True)
        self.assertIn('A&amp;B&lt;demo&gt;', svg)
        self.assertIn('SAMPLE DATA', svg)

    def test_publish_validation_requires_explicit_real_flag_and_target(self):
        payload = {'username': 'trynabe', 'days': [{'date': '2026-10-20', 'count': 3}], 'stats': {'total': 3}, 'generatedAt': '2026-10-20T12:00:00Z'}
        validator = getattr(update, 'validate_payload', lambda *a, **kw: None)
        for changes in ({}, {'isDemo': True}, {'isDemo': False, 'username': 'demo'}, {'isDemo': False, 'stats': {'total': 99}}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                validator({**payload, **changes})
        self.assertEqual(validator({**payload, 'isDemo': False})['stats']['total'], 3)


if __name__ == '__main__':
    unittest.main()
