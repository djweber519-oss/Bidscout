const $ = id => document.getElementById(id);
const stateCodes = 'AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY'.split(' ');
const stateNames = 'Alabama|Alaska|Arizona|Arkansas|California|Colorado|Connecticut|Delaware|Florida|Georgia|Hawaii|Idaho|Illinois|Indiana|Iowa|Kansas|Kentucky|Louisiana|Maine|Maryland|Massachusetts|Michigan|Minnesota|Mississippi|Missouri|Montana|Nebraska|Nevada|New Hampshire|New Jersey|New Mexico|New York|North Carolina|North Dakota|Ohio|Oklahoma|Oregon|Pennsylvania|Rhode Island|South Carolina|South Dakota|Tennessee|Texas|Utah|Vermont|Virginia|Washington|West Virginia|Wisconsin|Wyoming'.split('|');
const stateLookup = Object.fromEntries(stateCodes.map((s,i)=>[s,stateNames[i]]));
stateCodes.forEach((s,i)=>{const o=document.createElement('option');o.value=s;o.textContent=stateNames[i];$('state').append(o)});
let opportunities=[], saved=[], savedOnly=false;
try {saved=JSON.parse(localStorage.getItem('bidscout-saved-v2')||'[]');if(!Array.isArray(saved))saved=[];}catch{saved=[]}
function text(tag,value,cls){const el=document.createElement(tag);if(cls)el.className=cls;el.textContent=value;return el;}
function formatDate(date){if(!date)return 'Check official notice';return new Date(date+'T12:00:00').toLocaleDateString('en-US',{month:'short',day:'numeric',year:'numeric'});}
function render(){
 const q=$('search').value.trim().toLowerCase(),cat=$('category').value,st=$('state').value;
 let items=opportunities.filter(o=>(!savedOnly||saved.includes(o.id))&&(cat==='all'||o.category===cat)&&(st==='all'||o.state===st)&&[o.title,o.city,o.state,stateLookup[o.state],o.category,o.agency,o.type].join(' ').toLowerCase().includes(q));
 const sort=$('sort').value;
 items.sort((a,b)=>sort==='state'?(a.state||'ZZ').localeCompare(b.state||'ZZ'):sort==='title'?a.title.localeCompare(b.title):(a.deadline||'9999').localeCompare(b.deadline||'9999'));
 $('cards').replaceChildren();
 for(const o of items){
  const article=text('article','','card'),left=document.createElement('div'),right=text('div','','side');
  left.append(text('span','SAM.gov federal notice','pill'),text('h3',o.title),text('div',`📍 ${[o.city,stateLookup[o.state]||o.state].filter(Boolean).join(', ')||'Location unspecified'} • ${o.category}`,'meta'),text('p',`${o.agency||'Federal agency'} · ${o.type||'Notice'} · Posted ${formatDate(o.posted)}`));
  const date=text('div','Response deadline','date');date.append(text('strong',formatDate(o.deadline)));
  const link=text('a','View official notice ↗','source-link');link.href=o.source;link.target='_blank';link.rel='noopener noreferrer';
  const btn=text('button',saved.includes(o.id)?'★ Saved':'☆ Save','save'+(saved.includes(o.id)?' active':''));btn.type='button';btn.addEventListener('click',()=>{saved=saved.includes(o.id)?saved.filter(id=>id!==o.id):[...saved,o.id];try{localStorage.setItem('bidscout-saved-v2',JSON.stringify(saved))}catch{}render()});
  right.append(date,link,btn);article.append(left,right);$('cards').append(article);
 }
 $('empty').hidden=items.length!==0;$('resultCount').textContent=items.length+' federal results';$('savedCount').textContent=saved.length;$('savedToggle').textContent='Saved ('+saved.length+')'+(savedOnly?' ✓':'');
}
['search','category','state','sort'].forEach(id=>$(id).addEventListener(id==='search'?'input':'change',render));
$('clear').addEventListener('click',()=>{$('search').value='';$('category').value='all';$('state').value='all';$('sort').value='deadline';savedOnly=false;render()});
$('savedToggle').addEventListener('click',()=>{savedOnly=!savedOnly;render();$('opportunities').scrollIntoView({behavior:'smooth'})});
$('year').textContent=new Date().getFullYear();
async function load(){
 try{
  const res=await fetch('data/bids.json',{cache:'no-store'});if(!res.ok)throw Error('feed unavailable');
  const data=await res.json();if(!Array.isArray(data.opportunities))throw Error('invalid feed');
  const now=new Date().toISOString().slice(0,10);
  opportunities=data.opportunities.filter(o=>o&&o.id&&o.title&&o.source?.startsWith('https://sam.gov/opp/')&&(!o.deadline||o.deadline>=now));
  const age=data.updatedAt?Math.floor((Date.now()-Date.parse(data.updatedAt))/86400000):null;
  const stale=age===null||!Number.isFinite(age)||age>3;
  if(stale){opportunities=[];$('dataStatus').textContent='Live data unavailable or older than 3 days. Listings are hidden until a successful update. Check back later.';}
  else {$('dataStatus').textContent=`Federal SAM.gov feed last updated ${new Date(data.updatedAt).toLocaleString()}. ${data.coverageNote||'Limited federal coverage.'} Verify every deadline and requirement at SAM.gov.`;}
 }catch{$('dataStatus').textContent='Live data unavailable. No unverified listings are shown. Please check back later.';opportunities=[];}
 render();
}
load();
