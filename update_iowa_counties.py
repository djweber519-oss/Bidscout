#!/usr/bin/env python3
"""Collect verified Iowa county RSS/Atom bid notices; never imply unconnected coverage."""
import datetime as dt
import json
import re
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / 'data/iowa_counties.json'
OUTPUT = ROOT / 'data/iowa_county_bids.json'
MATCH = re.compile(r'landscap|lawn|mow(?:ing)?|grounds?\s*(?:maintenan|care)|snow\s*(?:remov|plow|clear)|ice\s*(?:remov|control)|de.?ic|tree\s*(?:trimm|prun|remov)|irrigat|vegetation|weed\s*control|turf|mulch', re.I)
EXCLUDE = re.compile(r'janitor|custodial|interior\s*clean|housekeep', re.I)
ATOM = '{http://www.w3.org/2005/Atom}'


def child_text(node, names):
    for name in names:
        item = node.find(name)
        if item is not None and item.text:
            return ' '.join(item.text.split())
    return ''


def valid_https(url):
    p = urlparse(url or '')
    return p.scheme == 'https' and bool(p.hostname) and not p.username and not p.password


def main():
    registry = json.loads(REGISTRY.read_text(encoding='utf-8'))
    counties = registry['counties']
    names = [c['county'] for c in counties]
    if len(counties) != 99 or len(set(names)) != 99:
        raise ValueError('Registry must contain 99 unique counties')
    records, checks, failures = [], [], []
    for county in counties:
        name = county['county']
        url = county.get('feedUrl')
        status = county.get('status')
        if not url or county.get('collectorType') not in ('rss', 'atom') or status != 'verified':
            checks.append({'county': name, 'status': 'not_connected'})
            continue
        if not valid_https(url):
            failures.append(name + ': invalid HTTPS feed URL')
            checks.append({'county': name, 'status': 'failed'})
            continue
        try:
            request = urllib.request.Request(url, headers={'User-Agent': 'BidScout/1.0 (public procurement feed reader)', 'Accept': 'application/rss+xml, application/atom+xml, application/xml, text/xml'})
            with urllib.request.urlopen(request, timeout=20) as response:
                if not valid_https(response.geturl()):
                    raise ValueError('Feed redirected to non-HTTPS URL')
                data = response.read(2_000_001)
                if len(data) > 2_000_000:
                    raise ValueError('Feed too large')
            root = ET.fromstring(data)
            entries = root.findall('.//item') or root.findall('.//' + ATOM + 'entry')
            found = 0
            for entry in entries:
                title = child_text(entry, ['title', ATOM + 'title'])
                description = child_text(entry, ['description', ATOM + 'summary'])
                link = child_text(entry, ['link'])
                if not link:
                    for a in entry.findall(ATOM + 'link'):
                        if a.get('href'):
                            link = a.get('href')
                            break
                if not valid_https(link) or not MATCH.search(title + ' ' + description) or EXCLUDE.search(title):
                    continue
                records.append({'title': title[:240], 'url': link, 'agency': name + ' County', 'county': name, 'governmentLevel': 'County', 'state': 'IA', 'deadline': None, 'deadlineVerified': False, 'sourceFeed': url})
                found += 1
            checks.append({'county': name, 'status': 'checked', 'matchingCandidates': found})
        except Exception as exc:
            failures.append(f'{name}: {type(exc).__name__}: {exc}')
            checks.append({'county': name, 'status': 'failed'})
    if failures:
        raise RuntimeError('Source failures; previous output preserved: ' + '; '.join(failures))
    unique = {(r['county'], r['url']): r for r in records}
    payload = {'updatedAt': dt.datetime.now(dt.timezone.utc).isoformat(), 'registeredCounties': len(counties), 'connectedCounties': sum(c['status'] == 'checked' for c in checks), 'unconnectedCounties': sum(c['status'] == 'not_connected' for c in checks), 'opportunities': list(unique.values()), 'countyChecks': checks, 'note': 'Only configured, verified RSS/Atom feeds are checked. Title/summary candidates require verification of eligibility, status, and deadline.'}
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUTPUT.with_suffix('.tmp')
    tmp.write_text(json.dumps(payload, indent=2) + '\n', encoding='utf-8')
    tmp.replace(OUTPUT)
    print(f"Registered {len(counties)} counties; checked {payload['connectedCounties']} verified feeds; {len(unique)} candidate notices. Unconnected: {payload['unconnectedCounties']}.")

if __name__ == '__main__':
    main()
