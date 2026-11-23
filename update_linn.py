#!/usr/bin/env python3
"""Conservative Linn County public bid page monitor. No invented notices."""
import datetime as dt
import html
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data' / 'linn_bids.json'
URL = 'https://www.linncountyiowa.gov/Bids.aspx'
KEYWORDS = ('landscap', 'mow', 'lawn', 'snow', 'ice removal', 'tree', 'grounds maintenance', 'vegetation', 'brush removal', 'turf')

class Parser(HTMLParser):
    def __init__(self):
        super().__init__(); self.links=[]; self.current=None; self.text=[]
    def handle_starttag(self, tag, attrs):
        a=dict(attrs)
        if tag=='a' and a.get('href'):
            self.current={'href':a['href'], 'text':''}
    def handle_data(self, data):
        self.text.append(data)
        if self.current is not None: self.current['text']+=data
    def handle_endtag(self, tag):
        if tag=='a' and self.current is not None:
            self.links.append(self.current); self.current=None

def main():
    req=urllib.request.Request(URL,headers={'User-Agent':'BidScoutPublicBidMonitor/1.0 (public listings; once daily)','Accept':'text/html'})
    with urllib.request.urlopen(req,timeout=25) as response:
        page=response.read(2_000_000).decode('utf-8','replace')
    parser=Parser();parser.feed(page)
    visible=re.sub(r'\s+',' ',html.unescape(' '.join(parser.text)))
    if 'bid postings' not in visible.lower():
        raise RuntimeError('Expected Bid Postings page not found; refusing to publish a false empty result')
    empty='there are no open bid postings at this time' in visible.lower()
    from urllib.parse import urljoin, urlparse
    candidates=[]; seen=set()
    for a in parser.links:
        url=urljoin(URL,html.unescape(a['href']))
        title=re.sub(r'\s+',' ',html.unescape(a['text'])).strip()
        if not title or not re.search(r'/Bid(s)?\.aspx|/Bids/|BidID=',url,re.I): continue
        if urlparse(url).netloc.lower() not in ('www.linncountyiowa.gov','linncountyiowa.gov'): continue
        if not any(k in title.lower() for k in KEYWORDS): continue
        if url in seen:continue
        seen.add(url)
        candidates.append({'county':'Linn','title':title,'url':url,'source':'Linn County public bid postings','status':'candidate_requires_verification'})
    # A page without the known empty notice or recognizable bid details may have changed.
    has_bid_details=bool(re.search(r'BidID=|/Bids/|/Bid\.aspx',page,re.I))
    if not empty and not has_bid_details:
        raise RuntimeError('Page layout is unrecognized; manual review required before declaring zero bids')
    payload={'updatedAt':dt.datetime.now(dt.timezone.utc).isoformat(),'county':'Linn','sourceUrl':URL,'sourceReachable':True,'pageReportedNoOpenBids':empty,'opportunities':candidates,'note':'Title-matched public listing candidates only. Verify deadlines, eligibility, and current open status on official source. A zero count is not proof that no contracts exist.'}
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(payload,indent=2)+'\n',encoding='utf-8')
    print(f'Linn page checked; explicit empty message={empty}; matching candidates={len(candidates)}')
if __name__=='__main__':main()
