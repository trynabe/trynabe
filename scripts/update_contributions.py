#!/usr/bin/env python3
"""Fetch authentic GitHub contribution counts and render a README-safe SVG.

No external Python dependencies. GITHUB_TOKEN stays in GitHub Actions, never the browser.
Usage:
    GITHUB_USERNAME=yourname GITHUB_TOKEN=... python scripts/update_contributions.py
    python scripts/update_contributions.py --demo
"""
import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COLORS = ('#ebedf0', '#c6e48b', '#7bc96f', '#239a3b', '#196127')

QUERY = '''query($login: String!) {
  user(login: $login) {
    login
    contributionsCollection {
      restrictedContributionsCount
      hasAnyRestrictedContributions
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays { date contributionCount contributionLevel }
        }
      }
    }
  }
}'''


def fetch_github(login, token, *, coverage=None):
    body = json.dumps({'query': QUERY, 'variables': {'login': login}}).encode('utf-8')
    req = urllib.request.Request(
        'https://api.github.com/graphql', data=body,
        headers={
            'Authorization': f'Bearer {token}',
            'Accept': 'application/vnd.github+json',
            'Content-Type': 'application/json',
            'User-Agent': 'contribution-skyline-self-hosted',
        }, method='POST',
    )
    try:
        with urllib.request.urlopen(req, timeout=25) as response:
            raw = json.load(response)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode('utf-8', 'replace')[:600]
        raise RuntimeError(f'GitHub API HTTP {exc.code}: {detail}') from exc
    if raw.get('errors'):
        raise RuntimeError(f'GitHub GraphQL returned errors: {raw["errors"]}')
    user = (raw.get('data') or {}).get('user')
    if not user:
        raise RuntimeError(f'Could not locate GitHub user {login!r}')
    if user.get('login', '').casefold() != login.casefold():
        raise RuntimeError('GitHub returned a different account')
    collection = user['contributionsCollection']
    calendar = collection['contributionCalendar']
    days = []
    for week in calendar['weeks']:
        for item in week['contributionDays']:
            levels = {'NONE': 0, 'FIRST_QUARTILE': 1, 'SECOND_QUARTILE': 2,
                      'THIRD_QUARTILE': 3, 'FOURTH_QUARTILE': 4}
            days.append({'date': item['date'], 'count': item['contributionCount'],
                         'level': levels.get(item['contributionLevel'], 0)})
    days = normalize_days(days)
    if not days or sum(d['count'] for d in days) != calendar['totalContributions']:
        raise RuntimeError('GitHub calendar total does not match its daily counts')
    # These counts are ALREADY in the calendar; adding them again would inflate totals.
    if coverage is not None:
        coverage.update({'anonymizedPrivateContributions': collection.get('restrictedContributionsCount',0),
                         'includesAnonymizedPrivate': collection.get('hasAnyRestrictedContributions',False),
                         'source': 'GitHub contributionCalendar'})
    return days


def normalize_days(days):
    """UTC calendar dates, combined duplicates, explicit zero days for gaps."""
    by_date = {}
    for item in days:
        key, count = item.get('date'), item.get('count')
        if not isinstance(key, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', key):
            raise ValueError('Invalid contribution date')
        date.fromisoformat(key)  # Reject impossible calendar dates.
        if type(count) is not int or count < 0:
            raise ValueError('Contribution count must be a non-negative integer')
        if key not in by_date:
            by_date[key] = {'date': key, 'count': 0, 'level': 0}
        by_date[key]['count'] += count
        by_date[key]['level'] = max(by_date[key]['level'], min(4, max(0, item.get('level', 0))))
    if not by_date:
        return []
    start, end = date.fromisoformat(min(by_date)), date.fromisoformat(max(by_date))
    if (end-start).days >= 371:
        raise ValueError('Calendar exceeds the supported 371-day window')
    return [by_date.get((start+timedelta(days=i)).isoformat(),
                        {'date': (start+timedelta(days=i)).isoformat(), 'count': 0, 'level': 0})
            for i in range((end-start).days+1)]


def validate_payload(data, *, allow_demo=False, expected_username='trynabe'):
    """Fail closed before publishing, including for missing provenance flags."""
    if type(data.get('isDemo')) is not bool or (data['isDemo'] and not allow_demo):
        raise ValueError('Explicit authentic data required; simulated or unknown data refused')
    if not data['isDemo'] and data.get('username', '').casefold() != expected_username.casefold():
        raise ValueError('Contribution account does not match the intended profile')
    generated = datetime.fromisoformat(data.get('generatedAt', '').replace('Z', '+00:00'))
    if generated.tzinfo is None:
        raise ValueError('generatedAt must include a timezone')
    if not isinstance(data.get('days'), list) or not data['days']:
        raise ValueError('Contribution data has no days')
    days = normalize_days(data['days'])
    stats = compute_stats(days)
    if data.get('stats', {}).get('total') != stats['total']:
        raise ValueError('Contribution total does not match its daily counts')
    return {**data, 'days': days, 'stats': stats}


def compute_stats(days):
    days = normalize_days(days)
    total = sum(d['count'] for d in days)
    busiest = max((d for d in days if d['count'] > 0), key=lambda d: d['count'], default=None)
    longest = (0, None, None)
    length, start, end = 0, None, None
    for d in days:
        if d['count']:
            length += 1
            if start is None:
                start = d['date']
            end = d['date']
            if length > longest[0]:
                longest = (length, start, end)
        else:
            length, start, end = 0, None, None
    # If today's contributions have not appeared yet, yesterday can still be
    # the end of the current streak.
    by_day = {d['date']: d['count'] for d in days}
    if days:
        latest = date.fromisoformat(days[-1]['date'])
        curday = latest if by_day.get(latest.isoformat(), 0) else latest - timedelta(days=1)
        current_to = curday.isoformat() if by_day.get(curday.isoformat(), 0) else None
        current = 0
        while by_day.get(curday.isoformat(), 0):
            current += 1
            curday -= timedelta(days=1)
        current_from = (curday + timedelta(days=1)).isoformat() if current else None
    else:
        current = 0
        current_from, current_to = None, None
    return {'total': total, 'busiestCount': busiest['count'] if busiest else 0,
            'busiestDate': busiest['date'] if busiest else None,
            'longestStreak': longest[0], 'longestFrom': longest[1],
            'longestTo': longest[2], 'currentStreak': current,
            'currentFrom': current_from, 'currentTo': current_to,
            'startDate': days[0]['date'] if days else None,
            'endDate': days[-1]['date'] if days else None}


def formatted(dt):
    if not dt:
        return '—'
    d = date.fromisoformat(dt)
    return f'{d.strftime("%b")} {d.day}'


def range_fmt(a, b):
    if not a or not b:
        return '—'
    return f'{formatted(a)} – {formatted(b)}'


def render_svg(days, stats, *, username, demo=False):
    """Self-contained SVG: no script, animation JS, remote fonts or foreignObject."""
    if not days:
        raise ValueError('Empty contribution calendar')
    start = date.fromisoformat(days[0]['date'])
    end = date.fromisoformat(days[-1]['date'])
    first_sunday = start - timedelta(days=(start.weekday() + 1) % 7)
    last_saturday = end + timedelta(days=(5 - end.weekday()) % 7)
    num_weeks = (last_saturday - first_sunday).days // 7 + 1
    # Keep squares inside the card, regardless of the 52 vs 53 week boundary.
    pitch = min(16.35, 860 / max(num_weeks - 1, 1))
    cell = pitch - 2.9
    x0, y0 = 78, 108
    level_map = {d['date']: d['level'] for d in days}
    lines = []
    append = lines.append
    append('<svg xmlns="http://www.w3.org/2000/svg" width="980" height="375" viewBox="0 0 980 375" role="img" aria-labelledby="title desc">')
    append(f'<title id="title">{stats["total"]:,} GitHub contributions — {escape(username)}</title>')
    append('<desc id="desc">GitHub contribution calendar, monthly labels and contribution streak statistics. Static card for GitHub README.</desc>')
    append('<rect x="1" y="1" width="978" height="373" rx="15" fill="#ffffff" stroke="#e5e7eb"/>')
    append('<rect x="21" y="68" width="938" height="285" rx="12" fill="#fff" stroke="#e5e7eb"/>')
    append('<g fill="#24292f" font-family="Arial, Helvetica, sans-serif">')
    append(f'<text x="23" y="44" font-size="16" font-weight="700">{stats["total"]:,} contributions in the last year</text>')
    append('<rect x="892" y="24" width="34" height="30" rx="6" fill="#111111"/>')
    for x in (900, 910):
        for y in (32, 42):
            append(f'<rect x="{x}" y="{y}" width="6" height="6" rx="1" fill="white"/>')
    append('<rect x="931" y="24" width="29" height="30" rx="6" fill="#f9fafb" stroke="#d1d5db"/>')
    append('<path d="M938 45 943 31 952 43 947 40 946 48Z" fill="none" stroke="#737373" stroke-width="1.6"/>')
    append('</g>')
    seen = set()
    p = first_sunday
    while p <= end:
        if p.day <= 7 and (p.year,p.month) not in seen:
            seen.add((p.year,p.month))
            idx = (p - first_sunday).days // 7
            xpos = x0 + idx * pitch
            if idx < num_weeks-3:
                append(f'<text x="{xpos:.2f}" y="96" fill="#808080" font-size="11" font-family="Arial, Helvetica, sans-serif">{p.strftime("%b")}</text>')
        p += timedelta(days=7)
    for label, weekday in (('Mon', 1), ('Wed',3),('Fri',5)):
        append(f'<text x="42" y="{y0+weekday*pitch+10:.2f}" fill="#6b7280" font-size="11" font-family="Arial, Helvetica, sans-serif">{label}</text>')
    for i in range(num_weeks):
        for dow in range(7):
            day = first_sunday + timedelta(days=i*7+dow)
            if day < start or day > end:
                continue
            color = COLORS[level_map.get(day.isoformat(),0)]
            append(f'<rect x="{x0+i*pitch:.2f}" y="{y0+dow*pitch:.2f}" width="{cell:.2f}" height="{cell:.2f}" rx="2.6" fill="{color}"/>')
    stats_cols = [
        (39, '1 year total', f'{stats["total"]:,}', 'contributions', range_fmt(stats['startDate'], stats['endDate'])),
        (270, 'Busiest day', str(stats['busiestCount']), 'contributions', formatted(stats['busiestDate'])),
        (500, 'Longest streak', str(stats['longestStreak']), 'days', range_fmt(stats['longestFrom'], stats['longestTo'])),
        (731, 'Current streak', str(stats['currentStreak']), 'days', range_fmt(stats['currentFrom'], stats['currentTo'])),
    ]
    for x,label,value,unit,detail in stats_cols:
        append(f'<text x="{x}" y="254" fill="#777" font-family="Arial, Helvetica, sans-serif" font-size="13">{escape(label)}</text>')
        append(f'<text x="{x}" y="285" fill="#216e39" font-family="Arial, Helvetica, sans-serif" font-size="29" font-weight="700">{escape(value)}</text>')
        offset = len(value)*17+4
        append(f'<text x="{x+offset}" y="283" fill="#222" font-family="Arial, Helvetica, sans-serif" font-size="14">{escape(unit)}</text>')
        append(f'<text x="{x}" y="307" fill="#888" font-family="Arial, Helvetica, sans-serif" font-size="12">{escape(detail)}</text>')
    append('<text x="38" y="339" fill="#777" font-size="12" font-family="Arial, Helvetica, sans-serif">Static README preview · Open the website for interactive 2D / 3D views</text>')
    append('<text x="790" y="339" fill="#777" font-size="11" font-family="Arial, Helvetica, sans-serif">Less</text>')
    for i,color in enumerate(COLORS):
        append(f'<rect x="825" y="329" width="12" height="12" rx="2" fill="{color}" transform="translate({i*18},0)"/>')
    append('<text x="927" y="339" fill="#777" font-size="11" font-family="Arial, Helvetica, sans-serif">More</text>')
    if demo:
        append('<text x="928" y="18" fill="#b45309" text-anchor="end" font-size="10" font-family="Arial, Helvetica, sans-serif">SAMPLE DATA</text>')
    append('</svg>')
    return '\n'.join(lines) + '\n'


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--demo', action='store_true', help='Generate screenshot-inspired sample, not real stats')
    a = p.parse_args()
    coverage = {}
    if a.demo:
        data = json.loads((ROOT/'preview'/'sample-data.json').read_text(encoding='utf8'))
        days = data['days']
        login = 'demo'
        outdata = ROOT/'preview'/'contributions-demo.json'
        outsvg = ROOT/'preview'/'contribution-card-demo.svg'
    else:
        login = os.environ.get('GITHUB_USERNAME') or os.environ.get('GITHUB_REPOSITORY_OWNER')
        token = os.environ.get('GITHUB_TOKEN')
        if not login or not token:
            p.error('Provide GITHUB_USERNAME and GITHUB_TOKEN (or run --demo)')
        days = fetch_github(login, token, coverage=coverage)
        outdata = ROOT/'contributions.json'
        outsvg = ROOT/'contribution-card.svg'
    if not days:
        raise RuntimeError('No contribution days received')
    stats = compute_stats(days)
    result = {'username': login, 'generatedAt': datetime.now(timezone.utc).isoformat(),
              'isDemo': bool(a.demo), 'days': days, 'stats': stats, 'coverage': coverage}
    outdata.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf8')
    outsvg.write_text(render_svg(days,stats,username=login,demo=a.demo),encoding='utf8')
    print(f'Wrote {outdata.relative_to(ROOT)} and {outsvg.relative_to(ROOT)} — {stats["total"]:,} contributions')

if __name__ == '__main__':
    main()
