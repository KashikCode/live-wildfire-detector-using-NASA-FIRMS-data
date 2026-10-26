/* TerraSignal front end: observational map, not a wildfire warning service. */
'use strict';

const REGIONS = {
  all: {name:'Contiguous United States', bounds:[[-125,24],[-66,50]], center:[39,-97],zoom:4},
  west:{name:'Western US',bounds:[[-125,31],[-101,49.5]],center:[40,-114],zoom:5},
  ca:{name:'California area',bounds:[[-125,32],[-113.5,42.5]],center:[37,-120],zoom:6},
  pnw:{name:'Pacific Northwest',bounds:[[-125,41],[-110,50]],center:[45.6,-119],zoom:6},
  mountain:{name:'Mountain West',bounds:[[-117,31],[-102,46]],center:[39,-109],zoom:5},
  tx:{name:'Texas area',bounds:[[-107,25],[-93,37]],center:[31,-100],zoom:6},
  se:{name:'Southeastern US',bounds:[[-96,24],[-75,37]],center:[32,-85],zoom:6}
};
const COLORS = {h:'#eb744c',n:'#e8b552',l:'#3c92a7'};
const number = new Intl.NumberFormat('en-US');
let observations = [];
let displayed = [];
let snapshot = null;
let map = null;
let markerLayer = null;
const MAX_MARKERS = 5000;
const $ = id => document.getElementById(id);

function escapeText(s){return String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
function dayStamp(t){return new Date(t).toISOString().slice(0,10);}
function formatUtc(t){if(!t)return '—';const d=new Date(t);return Number.isNaN(d.getTime())?'—':`${d.toLocaleDateString('en-US',{month:'short',day:'numeric',timeZone:'UTC'})} · ${d.toLocaleTimeString('en-US',{hour:'2-digit',minute:'2-digit',hour12:false,timeZone:'UTC'})} UTC`;}
function formatShort(t){if(!t)return '—';let d=new Date(t);return `${d.toLocaleDateString('en-US',{month:'short',day:'numeric',timeZone:'UTC'})} · ${d.toLocaleTimeString('en-US',{hour:'2-digit',minute:'2-digit',hour12:false,timeZone:'UTC'})}`;}

function initMap(){
  map=L.map('map',{zoomControl:false,preferCanvas:true}).setView([39,-97],4);
  L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png',{
    attribution:'&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
    maxZoom:18
  }).addTo(map);
  L.control.zoom({position:'bottomright'}).addTo(map);
  markerLayer=L.markerClusterGroup({maxClusterRadius:42,disableClusteringAtZoom:10,showCoverageOnHover:false,chunkedLoading:true,chunkInterval:100,chunkDelay:20});
  map.addLayer(markerLayer);
}
function normalizeObservation(row){
  const lat=Number(row.lat),lon=Number(row.lon),frp=Number(row.frp);
  const time=new Date(row.time).getTime();
  if(!Number.isFinite(lat)||!Number.isFinite(lon)||Math.abs(lat)>90||Math.abs(lon)>180||!Number.isFinite(frp)||frp<0||!Number.isFinite(time))return null;
  if(!['h','n','l'].includes(row.confidence)||!['NOAA-20','NOAA-21'].includes(row.satellite))return null;
  return {lat,lon,frp,time,iso:row.time,confidence:row.confidence,satellite:row.satellite,daynight:row.daynight||''};
}
function inBounds(p, region){const b=REGIONS[region].bounds;return p.lon>=b[0][0]&&p.lon<=b[1][0]&&p.lat>=b[0][1]&&p.lat<=b[1][1];}
function getFilters(){return {region:$('region').value,days:Number($('days').value),satellite:$('satellite').value,minFrp:Number($('frp').value),confidence:new Set([...document.querySelectorAll('.confidence-field input:checked')].map(x=>x.value))};}
function filterObservations(){
  const f=getFilters();
  const anchor=snapshot.status==='demo' ? observations.reduce((max,p)=>Math.max(max,p.time),0) : Date.now();
  const earliest=anchor-f.days*24*60*60*1000;
  return observations.filter(p=>p.time>=earliest&&p.time<=anchor&&inBounds(p,f.region)&&p.frp>=f.minFrp&&f.confidence.has(p.confidence)&&(f.satellite==='all'||p.satellite===f.satellite));
}
function popupHtml(p){
  const confidence={h:'High',n:'Nominal',l:'Low'}[p.confidence];
  return `<div class="popup-title">VIIRS thermal observation</div><div class="popup-line">Satellite: <strong>${escapeText(p.satellite)}</strong></div><div class="popup-line">Confidence: <strong>${confidence}</strong></div><div class="popup-line">Radiative power: <strong>${p.frp.toFixed(1)} MW</strong></div><div class="popup-line">Observed: <strong>${escapeText(formatUtc(p.iso))}</strong></div><div class="popup-line">Coordinates: <strong>${p.lat.toFixed(4)}, ${p.lon.toFixed(4)}</strong></div>`;
}
function renderMap(items){
  markerLayer.clearLayers();
  const displayedMarkers=items.slice(0,MAX_MARKERS);
  const markers=displayedMarkers.map(p=>L.marker([p.lat,p.lon],{icon:L.divIcon({className:'',html:`<span style="display:block;width:12px;height:12px;border:1px solid white;border-radius:50%;background:${COLORS[p.confidence]};box-shadow:0 0 0 2px #ffffff99"></span>`,iconSize:[12,12],iconAnchor:[6,6]})}).bindPopup(popupHtml(p)));
  markerLayer.addLayers(markers);
  $('render-note').textContent=items.length>MAX_MARKERS?`Showing ${number.format(MAX_MARKERS)} of ${number.format(items.length)} filtered observations. Statistics use all matching records.`:'Each marker is a satellite thermal observation, not an individual wildfire.';
  $('map-summary').textContent=`${number.format(items.length)} matching observations`;
}
function renderMetrics(items){
  $('metric-detections').textContent=number.format(items.length);
  $('metric-frp').textContent=items.length?items.reduce((max,p)=>Math.max(max,p.frp),0).toFixed(1):'0';
  $('metric-recent').textContent=items.length?formatShort(items[0].iso):'No detections';
  $('metric-sources').textContent=new Set(items.map(p=>p.satellite)).size;
  $('metric-period').textContent=`Within last ${$('days').value} day(s) and selected area`;
  $('export-btn').disabled=items.length===0;
}
function renderChart(items){
  const days=Number($('days').value);
  const anchor=snapshot.status==='demo' ? new Date(observations.reduce((max,p)=>Math.max(max,p.time),0)) : new Date();
  const bucket=[];
  for(let back=days;back>=0;back--){const d=new Date(anchor);d.setUTCHours(0,0,0,0);d.setUTCDate(d.getUTCDate()-back);bucket.push({day:d.toISOString().slice(0,10),count:0});}
  const lookup=new Map(bucket.map(x=>[x.day,x]));
  items.forEach(p=>{const b=lookup.get(dayStamp(p.iso));if(b)b.count++});
  const max=Math.max(1,...bucket.map(x=>x.count));
  $('chart').innerHTML=bucket.map((b,i)=>`<div class="bar-cell" title="${b.day}: ${number.format(b.count)} observations"><div class="bar-number">${number.format(b.count)}</div><div class="bar-track"><div class="bar ${i===bucket.length-1?'is-latest':''}" style="height:${Math.max(2,Math.round(b.count/max*100))}%"></div></div><div class="bar-label">${escapeText(new Date(b.day+'T00:00:00Z').toLocaleDateString('en-US',{month:'short',day:'numeric',timeZone:'UTC'}))}</div></div>`).join('');
}
function renderList(items){
  const top=items.slice(0,8);
  $('observation-list').innerHTML=top.length?top.map((p,i)=>`<button type="button" class="activity-row" data-index="${i}"><span class="conf-dot ${p.confidence==='h'?'high':p.confidence==='n'?'nominal':'low'}"></span><span class="activity-main"><b>${p.lat.toFixed(3)}°, ${p.lon.toFixed(3)}°</b><small>${escapeText(p.satellite)} · ${escapeText(formatUtc(p.iso))}</small></span><span class="activity-frp">${p.frp.toFixed(1)} <span>MW</span></span></button>`).join(''):'<p class="empty">No observations match these filters.</p>';
  [...document.querySelectorAll('.activity-row')].forEach(btn=>btn.addEventListener('click',()=>{
    const p=top[Number(btn.dataset.index)];map.flyTo([p.lat,p.lon],9,{duration:.6});
    L.popup().setLatLng([p.lat,p.lon]).setContent(popupHtml(p)).openOn(map);
  }));
}
function update(){if(!snapshot)return;displayed=filterObservations();renderMetrics(displayed);renderChart(displayed);renderList(displayed);renderMap(displayed);$('frp-value').textContent=$('frp').value;}
function exportCSV(){
  const header=['latitude','longitude','observed_utc','satellite','frp_mw','confidence','daynight'];
  const text=[header.join(','),...displayed.map(p=>[p.lat,p.lon,p.iso,p.satellite,p.frp,p.confidence,p.daynight].join(','))].join('\n');
  const url=URL.createObjectURL(new Blob([text],{type:'text/csv;charset=utf-8'}));
  const a=document.createElement('a');a.href=url;a.download=`terrasignal-${dayStamp(new Date())}.csv`;a.click();
  setTimeout(()=>URL.revokeObjectURL(url),1000);
}
function reset(){ $('region').value='all';$('days').value='7';$('satellite').value='all';$('frp').value=0;document.querySelectorAll('.confidence-field input').forEach(x=>x.checked=true);map.setView([39,-97],4);update();}
async function loadData(){
  try{
    const response=await fetch('data/observations.json',{cache:'no-store'});
    if(!response.ok)throw new Error('Feed unavailable');
    const payload=await response.json();
    if(!['demo','live'].includes(payload.status)||!Array.isArray(payload.observations))throw new Error('Malformed feed');
    snapshot=payload;
    observations=payload.observations.map(normalizeObservation).filter(Boolean).sort((a,b)=>b.time-a.time);
    if(!observations.length && payload.status==='demo')throw new Error('Empty demo');
    $('demo-warning').hidden=payload.status!=='demo';
    $('mode-pill').className=`mode-pill ${payload.status==='demo'?'demo':'live'}`;
    $('mode-pill').innerHTML=`<span class="pulse-dot"></span> ${payload.status==='demo'?'DEMO DATA':'NASA NEAR-REAL-TIME'}`;
    $('updated-at').textContent=formatUtc(payload.generated_at_utc);
    $('source-description').textContent=payload.status==='demo'?'Synthetic data · not actual fires':'NASA VIIRS NOAA-20 / NOAA-21';
    update();
  }catch(error){$('feed-error').hidden=false;$('feed-error').textContent='Unable to load observation data. The publication may still be deploying, or the feed file is missing.';$('map-summary').textContent='Feed unavailable';$('mode-pill').textContent='DATA UNAVAILABLE';console.error('Data could not be loaded:',error.message);}
}
window.addEventListener('DOMContentLoaded',()=>{
  if(!window.L||!L.markerClusterGroup){$('feed-error').hidden=false;$('feed-error').textContent='The map library failed to load. Check your internet connection.';return;}
  initMap();['region','days','satellite'].forEach(id=>$(id).addEventListener('change',()=>{if(id==='region'){const r=REGIONS[$('region').value];map.setView(r.center,r.zoom);}update();}));
  document.querySelectorAll('.confidence-field input').forEach(el=>el.addEventListener('change',update));
  $('frp').addEventListener('input',update);$('reset-btn').addEventListener('click',reset);$('export-btn').addEventListener('click',exportCSV);
  loadData();
});
