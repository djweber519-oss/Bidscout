#!/usr/bin/env python3
"""BidScout Iowa DAS public-page pilot. Never invent or silently overwrite results."""
import datetime as dt
import json
import re
import sys
import urllib.error
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'data' / 'iowa_bids.json'
PAGE = 'https://bidopportunities.iowa.gov/Home'
MATCH = re.compile(r'landscap|lawn|mow(?:ing)?|grounds?\s*(?:maintenan|care|keep)|snow\s*(?:remov|plow|clear)|ice\s*(?:remov|control|manag)|de.?ic|tree\s*(?:trimm|prun|remov|care)|irrigat|vegetation|weed\s*control|turf|mulch|brush\s*(?:clear|remov)|invasive\s*(?:brush|plant)', re.I)
EXCLUDE = re.compile(r'janitor|custodial|interior\s*clean|housekeep', re.I)
DATE = re.compile(r'\b(\d{1,2}/\d{1,2}/\d{4})\b')

class Tables(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows=[];self.row=None;self.cell=None;self.link=None
    def handle_starttag(self, tag, attrs):
        a=dict(attrs)
        if tag=='tr': self.row=[]
        if self.row is not None and tag in ('td','th'):
            self.cell={'text':'','href':None}
        if self.cell is not None and tag=='a' and a.get('href'):
            self.cell['href']=a['href']
    def handle_data(self,data):
        if self.cell is not None:self.cell['text']+=data
    def handle_endtag(self,tag):
        if tag in ('td','th') and self.cell is not None:
            self.cell['text']=' '.join(self.cell['text'].split())
            self.row.append(self.cell);self.cell=None
        if tag=='tr' and self.row is not None:
            if self.row:self.rows.append(self.row)
            self.row=None

def main():
    req=urllib.request.Request(PAGE,headers={'User-Agent':'BidScout/1.0 (public procurement listings; contact via website)','Accept':'text/html'})
    try:
        with urllib.request.urlopen(req,timeout=25) as r:
            if urlparse(r.geturl()).hostname!='bidopportunities.iowa.gov':
                raise RuntimeError('Iowa site redirected to an unexpected host')
            raw=r.read(3_000_001)
            if len(raw)>3_000_000:raise RuntimeError('Iowa listing exceeds safe download limit')
            html=raw.decode('utf-8',errors='replace')
    except (urllib.error.HTTPError,urllib.error.URLError) as e:
        raise RuntimeError('Could not retrieve Iowa public listings ('+type(e).__name__+'). Existing data preserved.') from None
    parser=Tables();parser.feed(html)
    today=dt.datetime.now(dt.timezone.utc).date()
    candidates=[]; inspected=0
    for row in parser.rows:
        values=[c['text'] for c in row]
        if len(values)<5:continue
        date_cells=[(i,DATE.search(v)) for i,v in enumerate(values)]
        dates=[(i,m.group(1)) for i,m in date_cells if m]
        if len(dates)<2:continue
        inspected+=1
        # Official listing columns: bid number, agency, contact, title, effective date, expiration date.
        expiry_idx,expiry_text=dates[-1]
        try:expiry=dt.datetime.strptime(expiry_text,'%m/%d/%Y').date()
        except ValueError:continue
        if expiry<today:continue
        title_idx=dates[0][0]-1
        if title_idx<0:continue
        title=values[title_idx]
        if not MATCH.search(title) or EXCLUDE.search(title):continue
        agency=values[title_idx-2] if title_idx>=2 else 'State of Iowa'
        number=values[title_idx-3] if title_idx>=3 else ''
        href=next((c['href'] for c in row if c['href'] and 'BidInfo' in c['href']),None)
        # Never fabricate a detail URL. Portal link is a valid fallback.
        url=urljoin(PAGE,href) if href else PAGE
        if urlparse(url).hostname!='bidopportunities.iowa.gov':url=PAGE
        candidates.append({'title':title[:240],'url':url,'agency':agency or 'State of Iowa','governmentLevel':'State','state':'IA','deadline':expiry.isoformat(),'deadlineVerified':True,'bidNumber':number})
    print(f'Iowa listing HTML: {len(parser.rows)} table rows, {inspected} date-bearing rows, {len(candidates)} matching active notices.')
    # Fail safely when website uses JS/API rendering, rather than publishing a misleading zero.
    if inspected==0:
        raise RuntimeError('Iowa page does not expose bid rows as static HTML. A verified data endpoint is needed; existing data preserved.')
    unique={x['bidNumber'] or x['url']+'|'+x['title']:x for x in candidates}
    payload={'updatedAt':dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds'),'sourceCount':1,'opportunities':list(unique.values()),'note':'State of Iowa public HTML listing. Confirm deadlines and bid details on the official site. Other sources not yet connected.'}
    OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    temp=OUTPUT.with_suffix('.tmp')
    temp.write_text(json.dumps(payload,indent=2)+'\n',encoding='utf-8')
    temp.replace(OUTPUT)
    print(f'Wrote {len(unique)} Iowa candidate contracts to data/iowa_bids.json.')

if __name__=='__main__':
    try:main()
    except Exception as e:
        print('Iowa collector: '+str(e),file=sys.stderr)
        sys.exit(1)
