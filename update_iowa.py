#!/usr/bin/env python3
"""BidScout: manually test Iowa's public bid JSON response.

Before enabling scheduled/commercial collection, verify the source's access terms.
Only publish complete, valid responses; preserve previous data on errors.
"""
import datetime as dt
import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'data' / 'iowa_bids.json'
ENDPOINT = 'https://bidopportunities.iowa.gov/Home/DT_HostedBidsSearch'
DETAIL = 'https://bidopportunities.iowa.gov/Home/BidInfo?bidId='

SERVICE = re.compile(r'landscap(?:ing|e)?|lawn\s*(?:care|maintenance|mow)|mow(?:ing)?|grounds?\s*(?:maintenance|keeping|care)|snow\s*(?:removal|plowing|clearing)|ice\s*(?:removal|control|management)|de[ -]?ic(?:ing|e)|tree\s*(?:trimming|pruning|removal|care)|irrigation\s*(?:service|maintenance|repair|installation)|vegetation\s*(?:management|control|removal)|weed\s*(?:control|removal)|turf\s*(?:maintenance|care)|mulch(?:ing)?\s*(?:service|installation)|brush\s*(?:clearing|removal)|right.of.way\s*(?:mowing|vegetation|maintenance)', re.I)
EXCLUDE = re.compile(r'janitor|custodial|housekeep|interior cleaning|anti.ice trailer|snow plow truck|snowplow truck|salt spreader|hydraulic|mulcher drum|mower (?:parts|equipment|purchase)|purchase of (?:mowers|equipment)|supply of (?:mowers|equipment)', re.I)
DOTNET_DATE = re.compile(r'^/Date\((-?\d+)(?:[+-]\d{4})?\)/$')


def deadline_from_dotnet(value):
    match = DOTNET_DATE.fullmatch(str(value or ''))
    if not match:
        raise ValueError('Unrecognized Iowa expiration date')
    return dt.datetime.fromtimestamp(int(match.group(1)) / 1000, tz=dt.timezone.utc)


def fetch():
    params = urllib.parse.urlencode({'agencyId': '', 'enteredSearchText': '', '_': str(int(dt.datetime.now(dt.timezone.utc).timestamp() * 1000))})
    request = urllib.request.Request(ENDPOINT + '?' + params, headers={'Accept': 'application/json', 'User-Agent': 'BidScout/1.0 (public procurement pilot)'})
    with urllib.request.urlopen(request, timeout=25) as response:
        if urllib.parse.urlparse(response.geturl()).hostname != 'bidopportunities.iowa.gov':
            raise RuntimeError('Unexpected redirect host')
        raw = response.read(4_000_001)
        if len(raw) > 4_000_000:
            raise RuntimeError('Response exceeds size limit')
        return json.loads(raw.decode('utf-8'))


def collect(payload):
    if not isinstance(payload, dict) or not isinstance(payload.get('aaData'), list):
        raise RuntimeError('Iowa JSON response missing aaData array')
    total = payload.get('iTotalRecords')
    rows = payload['aaData']
    if not isinstance(total, int) or total < 0 or len(rows) != total:
        raise RuntimeError('Iowa JSON response appears incomplete; existing data preserved')
    now = dt.datetime.now(dt.timezone.utc)
    matches = {}
    for item in rows:
        if not isinstance(item, dict):
            raise RuntimeError('Unexpected Iowa bid record format')
        title = str(item.get('Solicitation') or '').strip()
        description = str(item.get('Description') or '').strip()
        # Match the service sought, not incidental landscaping mentioned in unrelated projects.
        if not SERVICE.search(title):
            continue
        if EXCLUDE.search(title):
            continue
        if item.get('IsActive') is not True or str(item.get('Status', '')).lower() != 'open':
            continue
        deadline = deadline_from_dotnet(item.get('ExpirationDate'))
        if deadline <= now:
            continue
        bid_id = str(item.get('ID') or '').strip()
        if not re.fullmatch(r'[0-9a-fA-F-]{36}', bid_id):
            raise RuntimeError('Invalid Iowa bid ID in matching record')
        matches[bid_id] = {
            'title': title[:240],
            'description': description[:1000],
            'url': DETAIL + urllib.parse.quote(bid_id),
            'agency': str(item.get('AgencyName') or 'State of Iowa'),
            'governmentLevel': 'State',
            'state': 'IA',
            'deadline': deadline.date().isoformat(),
            'deadlineVerified': False,
            'bidNumber': str(item.get('BidNumber') or ''),
        }
    return total, list(matches.values())


def main():
    total, opportunities = collect(fetch())
    result = {
        'updatedAt': dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds'),
        'sourceCount': 1,
        'opportunities': opportunities,
        'note': 'Iowa public listing candidates. Confirm eligibility and deadlines at the official agency site. Source covers Iowa state portal only.'
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    temp = OUTPUT.with_suffix('.tmp')
    temp.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    temp.replace(OUTPUT)
    print(f'Iowa JSON: {total} total notices; {len(opportunities)} relevant active candidates saved.')


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(f'Iowa collector failed: {error}; previous data preserved.', file=sys.stderr)
        sys.exit(1)
