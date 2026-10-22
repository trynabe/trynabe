"""Refresh the skyline from GitHub's public calendar, including shared private counts.

No personal token is needed. Enable Private contributions on the owner's profile
to include the anonymized private activity they have chosen to share.
"""
import json
import re
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

from update_contributions import normalize_days, compute_stats, render_svg, validate_payload

ROOT = Path(__file__).resolve().parents[1]
PROFILE = 'trynabe'
URL = f'https://github.com/users/{PROFILE}/contributions'


class CalendarParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.cells, self.counts = {}, {}
        self.target, self.tooltip = None, []
        self.in_heading, self.heading = False, []

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        if tag == 'td' and 'data-date' in attrs:
            key = attrs.get('id')
            if not key or key in self.cells:
                raise ValueError('Duplicate or missing contribution cell ID')
            level = int(attrs.get('data-level', '-1'))
            if level not in range(5):
                raise ValueError('Invalid GitHub activity level')
            self.cells[key] = {'date': attrs['data-date'], 'level': level}
        if tag == 'tool-tip':
            self.target, self.tooltip = attrs.get('for'), []
        if tag == 'h2' and attrs.get('id') == 'js-contribution-activity-description':
            self.in_heading = True

    def handle_data(self, data):
        if self.target:
            self.tooltip.append(data)
        if self.in_heading:
            self.heading.append(data)

    def handle_endtag(self, tag):
        if tag == 'tool-tip':
            if self.target in self.cells:
                match = re.match(r'(No|[\d,]+) contributions? on ', ''.join(self.tooltip).strip())
                if not match or self.target in self.counts:
                    raise ValueError('Missing or duplicate contribution tooltip')
                self.counts[self.target] = 0 if match[1] == 'No' else int(match[1].replace(',', ''))
            self.target = None
        if tag == 'h2':
            self.in_heading = False


def parse_calendar(html):
    parser = CalendarParser()
    parser.feed(html)
    if not parser.cells or parser.cells.keys() != parser.counts.keys():
        raise ValueError('Incomplete GitHub contribution calendar')
    days = normalize_days([{**cell, 'count': parser.counts[key]} for key, cell in parser.cells.items()])
    if len(days) != len(parser.cells) or not 365 <= len(days) <= 371:
        raise ValueError('Expected a complete annual calendar with unique dates')
    match = re.search(r'([\d,]+)\s+contributions?\s+in the last year', ''.join(parser.heading))
    if not match or int(match[1].replace(',', '')) != sum(day['count'] for day in days):
        raise ValueError('GitHub headline does not match daily counts')
    return days


def fetch_calendar():
    request = urllib.request.Request(URL, headers={
        'Accept': 'text/html', 'User-Agent': 'contribution-skyline-profile-updater'})
    with urllib.request.urlopen(request, timeout=25) as response:
        body = response.read(2_000_001)
    if len(body) > 2_000_000:
        raise ValueError('Unexpectedly large GitHub calendar')
    return parse_calendar(body.decode('utf8'))


def refresh(root=ROOT):
    days = fetch_calendar()
    path = root / 'contributions.json'
    coverage = {'source': 'GitHub profile contribution calendar', 'url': URL}
    if path.exists():
        try:
            previous = validate_payload(json.loads(path.read_text(encoding='utf8')))
            if previous['days'] == days and previous.get('coverage') == coverage:
                print('Activity unchanged; existing assets preserved')
                return False
        except (ValueError, TypeError, KeyError, AttributeError):
            pass
    stats = compute_stats(days)
    data = {'username': PROFILE, 'generatedAt': datetime.now(timezone.utc).isoformat(),
            'isDemo': False, 'days': days, 'stats': stats, 'coverage': coverage}
    validate_payload(data)
    svg = render_svg(days, stats, username=PROFILE)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    (root / 'contribution-card.svg').write_text(svg, encoding='utf8')
    print(f'Updated @{PROFILE}: {stats["total"]} contributions')
    return True


if __name__ == '__main__':
    refresh()
