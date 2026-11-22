#!/usr/bin/env python3
"""Fetch and curate SAM.gov public notices. Secret never printed or written to disk."""
import datetime as dt
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'data' / 'bids.json'
API = 'https://api.sam.gov/opportunities/v2/search'
# Landscaping services and closely related grounds-maintenance categories.
CODES = ['561730', '561720', '561790', '561210', '238910', '237310', '238990', '115310']
KEYWORDS = re.compile(r'landscap|grounds?\s*(?:maintenan|keep|care|servic)|lawn|mow(?:ing)?|turf|irrigat|sprinkler|snow|ice\s*(?:remov|control)|de-?ic|tree|arbor|forestr|brush\s*(?:clear|cut|remov)|vegetat|weed\s*(?:control|remov)|herbicid|mulch|planting|prun|trimm|hardscap|pav(?:er|ing)|sidewalk|trail\s*(?:maintenan|repair|construct)|park\s*(?:maintenan|servic)|cemetery\s*(?:maintenan|ground)|erosion\s*control|stormwater|drainage|excavat|grading|site\s*(?:prepar|work|clear)|street\s*sweep|pressure\s*wash|power\s*wash|janitor|custodial|cleaning|facility\s*maintenan|building\s*maintenan|road\s*(?:maintenan|repair)|parking\s*lot\s*(?:maintenan|repair|strip)', re.I)
EXCLUDE_TYPES = {'Award Notice', 'Justification', 'Sale of Surplus Property'}
STATE_CODES = set('AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY'.split())

def date_only(value):
    if not value: return None
    s = str(value).strip()
    match = re.match(r'^(\d{4}-\d{2}-\d{2})', s)
    if match:
        try: return dt.date.fromisoformat(match.group(1)).isoformat()
        except ValueError: return None
    for fmt in ('%m/%d/%Y',):
        try: return dt.datetime.strptime(s[:10], fmt).date().isoformat()
        except ValueError: pass
    return None

def get_page(key, code, start, end, offset):
    params = {'api_key': key, 'postedFrom': start, 'postedTo': end, 'ncode': code, 'limit': 100, 'offset': offset}
    req = urllib.request.Request(API + '?' + urllib.parse.urlencode(params), headers={'Accept': 'application/json', 'User-Agent': 'BidScout/2.0'})
    try:
        with urllib.request.urlopen(req, timeout=35) as response:
            return json.load(response)
    except Exception:
        # Avoid logging URL or exception: they can contain the API key.
        raise RuntimeError('SAM.gov request failed. Check API key, access limits, and service status (details suppressed to protect secret).') from None

def main():
    key = os.getenv('SAM_API_KEY', '').strip()
    if not key:
        sys.exit('Missing SAM_API_KEY secret. Existing published data was not changed.')
    today = dt.datetime.now(dt.timezone.utc).date()
    since = today - dt.timedelta(days=180)
    found = {}
    count = 0
    for code in CODES:
        offset = 0
        # Bounded paging for free API quotas; metadata discloses that this is not exhaustive.
        for _ in range(10):
            payload = get_page(key, code, since.strftime('%m/%d/%Y'), today.strftime('%m/%d/%Y'), offset)
            records = payload.get('opportunitiesData', [])
            if not isinstance(records, list):
                raise RuntimeError('Unexpected SAM.gov response; published data unchanged.')
            count += len(records)
            for raw in records:
                title = str(raw.get('title') or '').strip()
                notice_id = str(raw.get('noticeId') or '').strip()
                if not notice_id or not re.fullmatch(r'[A-Za-z0-9-]{8,80}', notice_id): continue
                if not KEYWORDS.search(title): continue
                if str(raw.get('active') or '').lower() in ('no', 'false'): continue
                notice_type = str(raw.get('type') or '')
                if notice_type in EXCLUDE_TYPES: continue
                deadline = date_only(raw.get('responseDeadLine') or raw.get('reponseDeadLine'))
                if deadline and deadline < today.isoformat(): continue
                place = raw.get('placeOfPerformance') or {}
                if not isinstance(place, dict): place = {}
                state_obj = place.get('state') or {}
                state = (state_obj.get('code') if isinstance(state_obj, dict) else state_obj) or raw.get('state') or ''
                state = str(state).upper()
                if state not in STATE_CODES: state = ''
                city_obj = place.get('city') or {}
                city = (city_obj.get('name') if isinstance(city_obj, dict) else city_obj) or ''
                city = str(city)[:90]
                text = title.lower()
                category = ('Snow Removal' if re.search(r'snow|ice remov|de-?ic', text) else 'Irrigation' if re.search(r'irrigat|sprinkler', text) else 'Hardscaping' if re.search(r'hardscap|pav(?:er|ing)|sidewalk|parking lot|grading|excavat|site prepar', text) else 'Grounds Maintenance' if re.search(r'grounds|lawn|mow|turf|vegetat|tree|forestr|brush|weed|park|trail|erosion|stormwater', text) else 'Grounds Maintenance' if re.search(r'janitor|custodial|cleaning|facility|building maintenan|pressure wash|power wash|street sweep|road maintenan', text) else 'Landscaping')
                found[notice_id] = {'id': notice_id, 'title': title[:240], 'city': city, 'state': state, 'category': category, 'deadline': deadline, 'posted': date_only(raw.get('postedDate')), 'type': notice_type[:90], 'agency': str(raw.get('fullParentPathName') or raw.get('department') or '')[:220], 'naics': str(raw.get('naicsCode') or code), 'source': 'https://sam.gov/opp/' + notice_id + '/view'}
            offset += len(records)
            if not records or offset >= int(payload.get('totalRecords') or 0): break
    if count == 0:
        raise RuntimeError('No records returned across all queries. Published data unchanged; check API access and search filters.')
    items = sorted(found.values(), key=lambda x: (x['deadline'] is None, x['deadline'] or '9999', x['title']))
    result = {'source': 'SAM.gov Get Opportunities Public API v2', 'updatedAt': dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds'), 'windowDays': 180, 'searchNaics': CODES, 'recordsExamined': count, 'coverageNote': 'Expanded landscaping, outdoor work, facilities cleaning and maintenance federal notices; title-keyword matching and capped paging. Not exhaustive. Verify deadlines on SAM.gov.', 'opportunities': items}
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUTPUT.with_suffix('.tmp')
    tmp.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    tmp.replace(OUTPUT)
    print(f'Updated {len(items)} curated notices from {count} records; no credentials stored.')

if __name__ == '__main__':
   try: main()
except Exception:
    sys.exit('Update failed; existing data unchanged. Verify secret and SAM.gov API availability. No request details logged.')
