    raise RuntimeError('SAM.gov request failed.')


def category_for(title):
    text = title.lower()
    if re.search(r'snow|ice remov|de-?ic', text):
        return 'Snow Removal'
    if re.search(r'irrigat|sprinkler', text):
        return 'Irrigation'
    if re.search(r'hardscap|pav(?:er|ing)|sidewalk|parking lot|grading|excavat|site prepar', text):
        return 'Hardscaping'
    if re.search(r'grounds|lawn|mow|turf|vegetat|tree|forestr|brush|weed|park|trail|erosion|stormwater', text):
        return 'Grounds Maintenance'
    if re.search(r'janitor|custodial|cleaning|facility|building maintenan|pressure wash|power wash|street sweep|road maintenan', text):
        return 'Grounds Maintenance'
    return 'Landscaping'


def main():
    key = os.environ.get('SAM_API_KEY', '').strip()
    if not key:
        raise RuntimeError('Missing SAM_API_KEY GitHub Actions secret.')

    today = dt.datetime.now(dt.timezone.utc).date()
    since = today - dt.timedelta(days=180)
    found = {}
    examined = 0
    truncated_codes = []

    for code in CODES:
        offset = 0
        for _ in range(MAX_PAGES_PER_CODE):
            payload = get_page(key, code, since.strftime('%m/%d/%Y'), today.strftime('%m/%d/%Y'), offset)
            records = payload.get('opportunitiesData')
            if not isinstance(records, list):
                raise RuntimeError(f'Unexpected SAM.gov records format for NAICS {code}.')
            examined += len(records)
            for raw in records:
                if not isinstance(raw, dict):
                    continue
                title = str(raw.get('title') or '').strip()
                notice_id = str(raw.get('noticeId') or '').strip()
                if not notice_id or not re.fullmatch(r'[A-Za-z0-9-]{8,80}', notice_id):
                    continue
                if not KEYWORDS.search(title):
                    continue
                if str(raw.get('active') or '').lower() in ('no', 'false'):
                    continue
                notice_type = str(raw.get('type') or '')
                if notice_type in EXCLUDE_TYPES:
                    continue
                deadline = date_only(raw.get('responseDeadLine') or raw.get('reponseDeadLine'))
                if deadline and deadline < today.isoformat():
                    continue
                place = raw.get('placeOfPerformance') or {}
                if not isinstance(place, dict):
                    place = {}
                state_obj = place.get('state') or {}
                state = (state_obj.get('code') if isinstance(state_obj, dict) else state_obj) or raw.get('state') or ''
                state = str(state).upper()
                if state not in STATE_CODES:
                    state = ''
                city_obj = place.get('city') or {}
                city = (city_obj.get('name') if isinstance(city_obj, dict) else city_obj) or ''
                found[notice_id] = {
                    'id': notice_id,
                    'title': title[:240],
                    'city': str(city)[:90],
                    'state': state,
                    'category': category_for(title),
                    'deadline': deadline,
                    'posted': date_only(raw.get('postedDate')),
                    'type': notice_type[:90],
                    'agency': str(raw.get('fullParentPathName') or raw.get('department') or '')[:220],
                    'naics': str(raw.get('naicsCode') or code),
                    'source': 'https://sam.gov/opp/' + notice_id + '/view',
                }
            offset += len(records)
            try:
                total = int(payload.get('totalRecords') or 0)
            except (ValueError, TypeError):
                total = 0
            if not records or offset >= total:
                break
        if total > offset:
            truncated_codes.append(code)
        print(f'NAICS {code}: examined {offset} of {total} reported records.', flush=True)

    if examined == 0:
        raise RuntimeError('No records returned across all queries; published data unchanged.')
    if not found:
        raise RuntimeError('No matching active opportunities found; published data unchanged.')

    items = sorted(found.values(), key=lambda x: (x['deadline'] is None, x['deadline'] or '9999', x['title']))
    result = {
        'source': 'SAM.gov Get Opportunities Public API v2',
        'updatedAt': dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds'),
        'windowDays': 180,
        'searchNaics': CODES,
        'recordsExamined': examined,
        'coverageNote': 'Nationwide federal notices, title-keyword matching, maximum 100 results per NAICS code. Not exhaustive; some NAICS searches are truncated. Verify eligibility and deadlines on SAM.gov.',
        'truncatedNaics': truncated_codes,
        'opportunities': items,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUTPUT.with_suffix('.tmp')
    tmp.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    tmp.replace(OUTPUT)
    print(f'Updated {len(items)} curated notices from {examined} examined records. No credentials stored.')


if __name__ == '__main__':
    try:
        main()
    except RuntimeError as exc:
        # Only messages constructed above are printed; never print raw request URLs.
        print(str(exc), file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(f'Updater failed: {type(exc).__name__}; existing data unchanged.', file=sys.stderr)
        sys.exit(1)
