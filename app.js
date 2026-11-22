/* BidScout Version 4 — landscaping and snow removal discovery.
   Drop-in replacement for the existing root app.js. No dependencies. */
'use strict';
const $ = id => document.getElementById(id);
const stateCodes = 'AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY'.split(' ');
const stateNames = 'Alabama|Alaska|Arizona|Arkansas|California|Colorado|Connecticut|Delaware|Florida|Georgia|Hawaii|Idaho|Illinois|Indiana|Iowa|Kansas|Kentucky|Louisiana|Maine|Maryland|Massachusetts|Michigan|Minnesota|Mississippi|Missouri|Montana|Nebraska|Nevada|New Hampshire|New Jersey|New Mexico|New York|North Carolina|North Dakota|Ohio|Oklahoma|Oregon|Pennsylvania|Rhode Island|South Carolina|South Dakota|Tennessee|Texas|Utah|Vermont|Virginia|Washington|West Virginia|Wisconsin|Wyoming'.split('|');
const stateLookup = Object.fromEntries(stateCodes.map((code,i)=>[code,stateNames[i]]));
let opportunities = [], saved = [], savedOnly = false, excludedCount = 0;
try { const stored = JSON.parse(localStorage.getItem('bidscout-saved-v2') || '[]'); if (Array.isArray(stored)) saved = stored.filter(x=>typeof x==='string'); } catch {}
function node(tag,value='',cls='') {const el=document.createElement(tag);if(cls)el.className=cls;el.textContent=value;return el;}
function dateAtNoon(iso){return /^\d{4}-\d{2}-\d{2}$/.test(iso||'')?new Date(iso+'T12:00:00'):null;}
function formatDate(iso){const d=dateAtNoon(iso);return d&&!Number.isNaN(d.getTime())?d.toLocaleDateString('en-US',{month:'short',day:'numeric',year:'numeric'}):'Check official notice';}
function daysUntil(iso){const d=dateAtNoon(iso);if(!d||Number.isNaN(d.getTime()))return null;const today=new Date();today.setHours(12,0,0,0);return Math.round((d-today)/86400000);}
// Conservative title-based filtering: ambiguous jobs are omitted, not represented as verified.
const snow = /\bsnow\b|\bplow(?:ing)?\b|\bde[ -]?ic(?:e|ing)\b|\bice (?:removal|control|management)\b|\bwinter maintenance\b/i;
const landscape = /landscap|grounds?\s*(?:maintenan|keep|care|servic|management)|\blawn\b|\bmow(?:ing)?\b|\bturf\b|irrigat|sprinkler|\btrees?\b|arbor|\bprun(?:e|ing)\b|\btrimm(?:ing)?\b|\bbrush\s*(?:clear|cut|remov)|\bvegetat|\bweed\b|herbicid|\bmulch|\bplanting\b|\bflower\s*bed|\bshrub|\bhedge|\bgrass\b|\bseeding\b|\bsod\b|\bhardscap|\bretaining wall|\bpavers?\b|\bcemetery grounds\b|\bpark grounds\b|\btrail vegetation\b|\bsite landscaping\b/i;
const exclude = /janitor|custodial|window clean|pressure wash|power wash|\bhousekeep|\binterior\b|\broof\b|\bhvac\b|\bplumb|\belectrical\b|\basphalt\b|\broad (?:repair|construction|maintenance)\b|\bbuilding maintenance\b|\bfacility maintenance\b|\bparking lot strip|\bexcavat|\bsite prepar|\bgrading\b|\bconcrete\b|\bstreet sweep|\broad sweep/i;
function classify(o){
 const title=String(o.title||'');
 if(snow.test(title))return 'Snow Removal';
 if(exclude.test(title))return null;
 if(!landscape.test(title))return null;
 if(/irrigat|sprinkler/i.test(title))return 'Irrigation';
 if(/hardscap|retaining wall|pavers?/i.test(title))return 'Hardscaping';
 if(/grounds?|lawn|mow|turf|grass|tree|arbor|prun|trim|brush|vegetat|weed/i.test(title))return 'Grounds Maintenance';
 return 'Landscaping';
}
function setup(){
 const category=$('category');category.replaceChildren();
 [['all','All landscaping & snow'],['Landscaping','Landscaping'],['Grounds Maintenance','Grounds maintenance'],['Snow Removal','Snow removal'],['Irrigation','Irrigation'],['Hardscaping','Hardscaping']].forEach(([value,label])=>{const o=node('option',label);o.value=value;category.append(o)});
 stateCodes.forEach((code,i)=>{const o=node('option',stateNames[i]);o.value=code;$('state').append(o)});
 const style=document.createElement('style');style.textContent=`.bidscout-deadline{margin-top:8px;font-size:.87rem;font-weight:700}.bidscout-deadline.urgent{color:#b45309}.bidscout-deadline.expired{color:#a61b1b}.bidscout-type{font-size:.78rem;color:#4b5563;margin-top:6px}.bidscout-context{font-size:.88rem;color:#4b5563;margin-top:10px}.bidscout-empty-note{margin-top:8px}`;document.head.append(style);
 const hero=document.querySelector('.hero p');if(hero)hero.textContent='Find federal landscaping, grounds maintenance, irrigation, and snow removal opportunities across the United States.';
 const about=document.querySelector('#about p');if(about)about.textContent='BidScout curates a limited selection of federal SAM.gov notices for landscaping and snow removal contractors. Listings are screened by title and may omit relevant work or include ambiguous notices. It does not cover all federal, state, local, or private contracts.';
 const sectionTitle=document.querySelector('.section-title p');if(sectionTitle)sectionTitle.textContent='Landscaping and snow removal notices screened from SAM.gov. Confirm scope and deadlines with the agency.';
 ['search','category','state','sort','deadlineFilter'].forEach(id=>$(id).addEventListener(id==='search'?'input':'change',render));
 $('clear').addEventListener('click',()=>{$('search').value='';$('category').value='all';$('state').value='all';$('sort').value='deadline';$('deadlineFilter').value='all';savedOnly=false;render()});
 $('savedToggle').addEventListener('click',()=>{savedOnly=!savedOnly;render();$('opportunities').scrollIntoView({behavior:'smooth'})});
 $('year').textContent=new Date().getFullYear();
}
function render(){
 const q=$('search').value.trim().toLowerCase(),cat=$('category').value,st=$('state').value,df=$('deadlineFilter').value;
 let items=opportunities.filter(o=>(!savedOnly||saved.includes(o.id))&&(cat==='all'||o.category===cat)&&(st==='all'||o.state===st)&&[o.title,o.city,o.state,stateLookup[o.state],o.category,o.agency,o.type,o.naics].join(' ').toLowerCase().includes(q));
 items=items.filter(o=>df==='all'||(df==='unknown'?!o.deadline:(daysUntil(o.deadline)!==null&&daysUntil(o.deadline)>=0&&daysUntil(o.deadline)<=Number(df))));
 const sort=$('sort').value;
 items.sort((a,b)=>sort==='state'?(a.state||'ZZ').localeCompare(b.state||'ZZ'):sort==='title'?a.title.localeCompare(b.title):sort==='posted'?(b.posted||'').localeCompare(a.posted||''):(a.deadline||'9999').localeCompare(b.deadline||'9999'));
 const cards=$('cards');cards.replaceChildren();
 for(const o of items){
  const article=node('article','','card'),left=node('div'),right=node('div','','side');
  left.append(node('span','SAM.gov federal notice','pill'),node('h3',o.title),node('div',`📍 ${[o.city&&o.city!=='0'?o.city:'',stateLookup[o.state]||o.state].filter(Boolean).join(', ')||'Location unspecified'} • ${o.category}`,'meta'),node('p',`${o.agency||'Federal agency'} · ${o.type||'Notice'} · Posted ${formatDate(o.posted)}`));
  const date=node('div','Response deadline','date');date.append(node('strong',formatDate(o.deadline)));
  const days=daysUntil(o.deadline), countdown=node('div',days===null?'Deadline not provided':days===0?'Closes today':days===1?'1 day remaining':`${days} days remaining`,'bidscout-deadline'+(days!==null&&days<=7?' urgent':''));date.append(countdown);
  const link=node('a','View official notice ↗','source-link');link.href=o.source;link.target='_blank';link.rel='noopener noreferrer';
  const btn=node('button',saved.includes(o.id)?'★ Saved':'☆ Save','save'+(saved.includes(o.id)?' active':''));btn.type='button';btn.setAttribute('aria-pressed',String(saved.includes(o.id)));btn.addEventListener('click',()=>{saved=saved.includes(o.id)?saved.filter(id=>id!==o.id):[...saved,o.id];try{localStorage.setItem('bidscout-saved-v2',JSON.stringify(saved))}catch{}render()});
  right.append(date,link,btn);article.append(left,right);cards.append(article);
 }
 $('empty').hidden=items.length!==0;$('resultCount').textContent=`${items.length} matching federal results`;
 $('savedCount').textContent=saved.length;$('dashboardSaved').textContent=saved.length;
 $('savedToggle').textContent=`Saved (${saved.length})${savedOnly?' ✓':''}`;
 if(!items.length){$('empty').textContent=savedOnly?'No saved opportunities match these filters. Clear filters or save a contract to see it here.':'No matching landscaping or snow removal opportunities. Try another keyword, category, or state.';}
}
async function load(){
 try{
  const response=await fetch('data/bids.json',{cache:'no-store'});if(!response.ok)throw new Error('feed unavailable');
  const data=await response.json();if(!Array.isArray(data.opportunities))throw new Error('invalid feed');
  const age=data.updatedAt?Math.floor((Date.now()-Date.parse(data.updatedAt))/86400000):null;
  const stale=age===null||!Number.isFinite(age)||age>3;
  if(stale){opportunities=[];$('dataStatus').textContent='Federal data is older than 3 days. Listings are temporarily hidden until a successful update.';}
  else{
   const current=new Date();const today=`${current.getFullYear()}-${String(current.getMonth()+1).padStart(2,'0')}-${String(current.getDate()).padStart(2,'0')}`;
   const valid=data.opportunities.filter(o=>o&&typeof o.id==='string'&&typeof o.title==='string'&&typeof o.source==='string'&&/^https:\/\/sam\.gov\/opp\/[A-Za-z0-9-]+\/view$/.test(o.source)&&(!o.deadline||o.deadline>=today));
   opportunities=valid.map(o=>({...o,category:classify(o)})).filter(o=>o.category!==null);
   excludedCount=valid.length-opportunities.length;
   $('dataStatus').textContent=`SAM.gov feed updated ${new Date(data.updatedAt).toLocaleString()}. Showing ${opportunities.length} title-matched landscaping and snow removal notices; ${excludedCount} other or unclear notices hidden. This is not exhaustive. Verify scope and deadlines on SAM.gov.`;
  }
 }catch{$('dataStatus').textContent='Federal data unavailable. Listings are hidden until a verified update succeeds.';opportunities=[];}
 $('totalCount').textContent=opportunities.length;
 $('soonCount').textContent=opportunities.filter(o=>{const d=daysUntil(o.deadline);return d!==null&&d>=0&&d<=7}).length;
 render();
}
setup();load();
