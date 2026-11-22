#!/usr/bin/env python3
"""Conservative public RSS/Atom procurement collector. No fabricated notices."""
import datetime as dt
import json
import re
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / 'data' / 'iowa_sources.json'
OUTPUT = ROOT / 'data' / 'iowa_bids.json'
PATTERN = re.compile(r'landscap|lawn|mow(?:ing)?|grounds? maintenan|snow (?:remov|plow|clear)|ice (?:remov|control)|de.?ic|tree (?:trimm|prun|remov)|irrigat|vegetation|weed control|turf|mulch', re.I)
EXCLUDE = re.compile(r'janitor|custodial|interior clean|housekeep', re.I)

def value(el, name):
    node = el.find(name)
    return (node.text or '').strip() if node is not None else ''

def main():
    config = json.loads(CONFIG.read_text(encoding='utf-8'))
    results = []
    failures = []
    feeds = [x for x in config['sources'] if x.get('feed_url')]
    for source in feeds:
        url = source['feed_url']
        if not url.startswith('https://'):
            failures.append(source['name'] + ': feed URL must be HTTPS')
            continue
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'BidScout-Iowa/1.0 (public feed reader)'})
            with urllib.request.urlopen(req, timeout=20) as resp:
                xml = resp.read(2_000_000)
            root = ET.fromstring(xml)
            entries = root.findall('.//item') or root.findall('{http://www.w3.org/2005/Atom}entry')
            for item in entries:
                title = value(item, 'title') or value(item, '{http://www.w3.org/2005/Atom}title')
                link = value(item, 'link')
                if not link:
                    for elem in item.findall('{http://www.w3.org/2005/Atom}link'):
                        if elem.get('href'):
                            link = elem.get('href')
                            break
                if not PATTERN.search(title) or EXCLUDE.search(title) or not link.startswith('https://'):
                    continue
                results.append({'title': title[:240], 'url': link, 'agency': source['name'], 'governmentLevel': source['level'], 'state': 'IA', 'deadline': None, 'deadlineVerified': False})
        except Exception as exc:
            failures.append(f"{source['name']}: {type(exc).__name__}")
    # Avoid publishing incomplete feed results when a source fails.
    if failures:
        raise RuntimeError('Source checks failed; prior data preserved: ' + '; '.join(failures))
    # If no live feeds have been configured, do not claim successful discovery.
    if not feeds:
        print('No verified RSS/Atom feeds configured. Existing data unchanged. Add confirmed public feed URLs to data/iowa_sources.json.')
        return
    unique = {item['url']: item for item in results}
    payload = {'updatedAt': dt.datetime.now(dt.timezone.utc).isoformat(), 'sourceCount': len(feeds), 'opportunities': list(unique.values()), 'note': 'Feed-title matches only. Deadlines are not verified; confirm at the issuing agency.'}
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUTPUT.with_suffix('.tmp')
    tmp.write_text(json.dumps(payload, indent=2) + '\n', encoding='utf-8')
    tmp.replace(OUTPUT)
    print(f'Published {len(unique)} candidate opportunities from {len(feeds)} public feeds.')

if __name__ == '__main__':
    main()
