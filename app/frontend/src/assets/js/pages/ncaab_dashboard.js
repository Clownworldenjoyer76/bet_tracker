const BASE = 'https://raw.githubusercontent.com/Clownworldenjoyer76/bet_tracker/main/docs/win/final_scores/deeper_summaries/ncaab/';
const FILES = {
  ncaab_summary_overall:            BASE + 'ncaab_summary_overall.csv',
  ncaab_summary_by_market:          BASE + 'ncaab_summary_by_market.csv',
  ncaab_summary_by_side_group:      BASE + 'ncaab_summary_by_side_group.csv',
  ncaab_summary_by_date:            BASE + 'ncaab_summary_by_date.csv',
  ncaab_bet_log:                    BASE + 'ncaab_bet_log.csv',
  ncaab_moneyline_by_edge:          BASE + 'by_market/ncaab_moneyline_by_edge.csv',
  ncaab_moneyline_by_kelly:         BASE + 'by_market/ncaab_moneyline_by_kelly.csv',
  ncaab_moneyline_by_odds:          BASE + 'by_market/ncaab_moneyline_by_odds.csv',
  ncaab_moneyline_by_side:          BASE + 'by_market/ncaab_moneyline_by_side.csv',
  ncaab_spread_by_edge:             BASE + 'by_market/ncaab_spread_by_edge.csv',
  ncaab_spread_by_kelly:            BASE + 'by_market/ncaab_spread_by_kelly.csv',
  ncaab_spread_by_odds:             BASE + 'by_market/ncaab_spread_by_odds.csv',
  ncaab_spread_by_side:             BASE + 'by_market/ncaab_spread_by_side.csv',
  ncaab_total_by_edge:              BASE + 'by_market/ncaab_total_by_edge.csv',
  ncaab_total_by_kelly:             BASE + 'by_market/ncaab_total_by_kelly.csv',
  ncaab_total_by_odds:              BASE + 'by_market/ncaab_total_by_odds.csv',
  ncaab_total_by_side:              BASE + 'by_market/ncaab_total_by_side.csv',
};
const D = {};
let betLogFiltered = [];
let betLogPage = 0;
const PAGE_SIZE = 50;
function parseCSV(text) {
  const lines = text.trim().split('\n');
  const headers = lines[0].split(',').map(h => h.trim().replace(/\r/g,''));
  return lines.slice(1).map(line => {
    const vals = line.split(',').map(v => v.trim().replace(/\r/g,''));
    const obj = {};
    headers.forEach((h,i) => obj[h] = vals[i] ?? '');
    return obj;
  }).filter(r => Object.values(r).some(v => v !== ''));
}
async function loadAll() {
  await Promise.all(Object.entries(FILES).map(async ([key, url]) => {
    try {
      const res = await fetch(url);
      if (!res.ok) return;
      D[key] = parseCSV(await res.text());
    } catch(e) {}
  }));
  processData();
}
function n(v, dec=1) { const f = parseFloat(v); return isNaN(f) ? '—' : f.toFixed(dec); }
function pct(v) { const f = parseFloat(v); return isNaN(f) ? '—' : (f * 100).toFixed(1) + '%'; }
function wrClass(v) { const f = parseFloat(v); if (isNaN(f)) return ''; return f >= 0.60 ? 'wr-high' : f >= 0.50 ? 'wr-mid' : 'wr-low'; }
function roiColor(v) { const f = parseFloat(v); if (isNaN(f)) return ''; return f >= 0 ? 'win' : 'loss'; }
function showSection(name, el) {
  document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
  document.querySelectorAll('.dash-tabs a').forEach(a => a.classList.remove('active'));
  document.getElementById('sec-' + name).classList.add('active');
  if (el) el.classList.add('active');
  if (name === 'date' && D['ncaab_summary_by_date']) renderDateChart();
}
function processData() {
  const overall = D['ncaab_summary_overall'];
  if (overall && overall[0]) {
    const r = overall[0];
    document.getElementById('stat-cards').style.display = 'grid';
    document.getElementById('s-bets').textContent = r.bets || '—';
    document.getElementById('s-wr').textContent = r.win_rate ? (parseFloat(r.win_rate)*100).toFixed(1)+'%' : '—';
    document.getElementById('s-roi').textContent = r.roi ? (parseFloat(r.roi)*100).toFixed(1)+'%' : '—';
    const u = parseFloat(r.units);
    const uEl = document.getElementById('s-units');
    uEl.textContent = isNaN(u) ? '—' : (u >= 0 ? '+' : '') + u.toFixed(2);
    uEl.className = 'stat-value ' + (u >= 0 ? 'green' : 'red');
    document.getElementById('s-wins').textContent = r.wins || '—';
    document.getElementById('s-losses').textContent = r.losses || '—';
    document.getElementById('s-edge').textContent = r.avg_edge ? (parseFloat(r.avg_edge)*100).toFixed(2)+'%' : '—';
    document.getElementById('s-odds').textContent = r.avg_odds ? (parseFloat(r.avg_odds) > 0 ? '+' : '') + n(r.avg_odds, 0) : '—';
    document.getElementById('last-updated').textContent = 'LIVE';
  } else {
    document.getElementById('last-updated').textContent = 'NO DATA';
  }
  renderSummaryTable('ncaab_summary_by_market',     'load-market', ['market_type','bets','wins','losses','win_rate','units','roi','avg_edge','avg_odds']);
  renderSummaryTable('ncaab_summary_by_side_group', 'load-side',   ['side_group','bets','wins','losses','win_rate','units','roi','avg_edge','avg_odds']);
  renderSummaryTable('ncaab_summary_by_date',       'load-date',   ['game_date','bets','wins','losses','win_rate','units','roi','avg_edge','avg_odds']);
  renderSummaryTable('ncaab_moneyline_by_edge', 'load-edge-ml',  ['edge_bucket','bets','wins','losses','win_rate','units','roi']);
  renderSummaryTable('ncaab_spread_by_edge',    'load-edge-sp',  ['edge_bucket','bets','wins','losses','win_rate','units','roi']);
  renderSummaryTable('ncaab_total_by_edge',     'load-edge-tot', ['edge_bucket','bets','wins','losses','win_rate','units','roi']);
  renderSummaryTable('ncaab_moneyline_by_odds', 'load-odds-ml',  ['odds_bucket','bets','wins','losses','win_rate','units','roi']);
  renderSummaryTable('ncaab_spread_by_odds',    'load-odds-sp',  ['odds_bucket','bets','wins','losses','win_rate','units','roi']);
  renderSummaryTable('ncaab_total_by_odds',     'load-odds-tot', ['odds_bucket','bets','wins','losses','win_rate','units','roi']);
  renderSummaryTable('ncaab_moneyline_by_kelly', 'load-kelly-ml',  ['kelly_bucket','bets','wins','losses','win_rate','units','roi']);
  renderSummaryTable('ncaab_spread_by_kelly',    'load-kelly-sp',  ['kelly_bucket','bets','wins','losses','win_rate','units','roi']);
  renderSummaryTable('ncaab_total_by_kelly',     'load-kelly-tot', ['kelly_bucket','bets','wins','losses','win_rate','units','roi']);
  if (D['ncaab_bet_log']) { betLogFiltered = D['ncaab_bet_log']; renderBetLog(); }
  if (D['ncaab_summary_by_market']) renderTally();
  if (D['ncaab_summary_by_date']) renderDateChart();
}
function renderSummaryTable(key, targetId, cols) {
  const el = document.getElementById(targetId);
  if (!el) return;
  const data = D[key];
  if (!data || !data.length) { el.textContent = 'No data: ' + key; return; }
  const headers = cols.map(c => `<th onclick="sortTable(this)">${c.replace(/_/g,' ').toUpperCase()}</th>`).join('');
  const rows = data.map(r => {
    const cells = cols.map(c => {
      if (c === 'win_rate') return `<td><span class="wr-badge ${wrClass(r[c])}">${pct(r[c])}</span></td>`;
      if (c === 'roi') return `<td class="${roiColor(r[c])}">${r[c] ? (parseFloat(r[c])*100).toFixed(1)+'%' : '—'}</td>`;
      if (c === 'units') { const u = parseFloat(r[c]); return `<td class="${isNaN(u)?'':u>=0?'win':'loss'}">${isNaN(u)?'—':(u>=0?'+':'')+u.toFixed(2)}</td>`; }
      if (c === 'avg_edge') return `<td>${r[c] ? (parseFloat(r[c])*100).toFixed(2)+'%' : '—'}</td>`;
      if (c === 'avg_odds') return `<td>${r[c] ? (parseFloat(r[c])>0?'+':'')+n(r[c],0) : '—'}</td>`;
      if (c === 'wins') return `<td class="win">${r[c] || '—'}</td>`;
      if (c === 'losses') return `<td class="loss">${r[c] || '—'}</td>`;
      return `<td>${r[c] || '—'}</td>`;
    }).join('');
    return `<tr>${cells}</tr>`;
  }).join('');
  el.outerHTML = `<table><thead><tr>${headers}</tr></thead><tbody>${rows}</tbody></table>`;
}
function renderTally() {
  const data = D['ncaab_summary_by_market'];
  if (!data || !data.length) return;
  const maxBets = Math.max(...data.map(r => parseInt(r.bets) || 0));
  const bars = data.map(r => {
    const wr = parseFloat(r.win_rate) || 0;
    const w = Math.max(((parseInt(r.bets)||0) / maxBets) * 100, 2);
    const cls = wr >= 0.60 ? 'win-bar' : wr >= 0.50 ? 'neutral-bar' : 'loss-bar';
    return `<div class="bar-row">
      <div class="bar-label">${(r.market_type||'').toUpperCase()}</div>
      <div class="bar-track"><div class="bar-fill ${cls}" style="width:${w}%">${r.wins||0}W / ${r.losses||0}L</div></div>
      <div class="bar-meta"><span class="wr-badge ${wrClass(r.win_rate)}">${pct(r.win_rate)}</span></div>
    </div>`;
  }).join('');
  document.getElementById('tally-chart').innerHTML = `<div class="section-title" style="font-size:1rem;margin-bottom:20px">WIN RATE BY MARKET</div>${bars}`;
  renderSummaryTable('ncaab_summary_by_market', 'load-tally-table', ['market_type','wins','losses','bets','win_rate','units','roi']);
}
function renderBetLog() {
  const wrap = document.getElementById('betlog-wrap');
  const data = betLogFiltered;
  if (!data || !data.length) { wrap.innerHTML = '<div class="loading">No bet log data</div>'; return; }
  const start = betLogPage * PAGE_SIZE;
  const page = data.slice(start, start + PAGE_SIZE);
  const cols = ['game_date','away_team','home_team','market_type','bet_side','line','take_odds','selected_edge','bet_result','units'];
  const headers = cols.map(c => `<th>${c.replace(/_/g,' ').toUpperCase()}</th>`).join('');
  const rows = page.map(r => {
    const res = (r.bet_result||'').toLowerCase();
    const resClass = res === 'win' ? 'win' : res === 'loss' ? 'loss' : 'push';
    const cells = cols.map(c => {
      if (c === 'bet_result') return `<td class="${resClass}">${r[c] || '—'}</td>`;
      if (c === 'units') { const u = parseFloat(r[c]); return `<td class="${isNaN(u)?'':u>=0?'win':'loss'}">${isNaN(u)?'—':(u>=0?'+':'')+u.toFixed(2)}</td>`; }
      if (c === 'selected_edge') return `<td>${r[c] ? (parseFloat(r[c])*100).toFixed(2)+'%' : '—'}</td>`;
      if (c === 'take_odds') return `<td>${r[c] ? (parseFloat(r[c])>0?'+':'')+r[c] : '—'}</td>`;
      return `<td>${r[c] || '—'}</td>`;
    }).join('');
    return `<tr>${cells}</tr>`;
  }).join('');
  wrap.innerHTML = `<table><thead><tr>${headers}</tr></thead><tbody>${rows}</tbody></table>`;
  renderPages(data.length);
}
function filterBetLog(q) {
  const all = D['ncaab_bet_log'] || [];
  const lower = q.toLowerCase();
  betLogFiltered = lower ? all.filter(r => Object.values(r).some(v => v.toLowerCase().includes(lower))) : all;
  betLogPage = 0;
  renderBetLog();
}
function renderPages(total) {
  const pages = Math.ceil(total / PAGE_SIZE);
  const container = document.getElementById('betlog-pages');
  container.innerHTML = '';
  if (pages <= 1) return;
  for (let i = 0; i < pages; i++) {
    const btn = document.createElement('button');
    btn.className = 'page-btn' + (i === betLogPage ? ' active' : '');
    btn.textContent = i + 1;
    btn.onclick = () => { betLogPage = i; renderBetLog(); };
    container.appendChild(btn);
  }
}
function renderDateChart() {
  const data = D['ncaab_summary_by_date'];
  if (!data || !data.length) return;
  const canvas = document.getElementById('date-canvas');
  const ctx = canvas.getContext('2d');
  canvas.width = canvas.parentElement.offsetWidth - 48;
  canvas.height = 280;
  const dates = data.map(r => r.game_date || '');
  const wrs = data.map(r => (parseFloat(r.win_rate)||0)*100);
  const W = canvas.width, H = canvas.height;
  const PAD = { top: 20, right: 20, bottom: 50, left: 50 };
  const chartW = W - PAD.left - PAD.right;
  const chartH = H - PAD.top - PAD.bottom;
  const nd = dates.length;
  ctx.clearRect(0, 0, W, H);
  ctx.strokeStyle = 'rgba(255,255,255,0.05)'; ctx.lineWidth = 1;
  for (let i = 0; i <= 4; i++) { const y = PAD.top + (chartH/4)*i; ctx.beginPath(); ctx.moveTo(PAD.left, y); ctx.lineTo(W-PAD.right, y); ctx.stroke(); }
  ctx.strokeStyle = 'rgba(255,255,255,0.15)';
  ctx.beginPath(); ctx.moveTo(PAD.left, PAD.top); ctx.lineTo(PAD.left, H-PAD.bottom); ctx.stroke();
  ctx.beginPath(); ctx.moveTo(PAD.left, H-PAD.bottom); ctx.lineTo(W-PAD.right, H-PAD.bottom); ctx.stroke();
  const y50 = PAD.top + chartH * 0.5;
  ctx.strokeStyle = 'rgba(255,214,0,0.2)'; ctx.setLineDash([4,4]);
  ctx.beginPath(); ctx.moveTo(PAD.left, y50); ctx.lineTo(W-PAD.right, y50); ctx.stroke();
  ctx.setLineDash([]);
  function xPos(i) { return PAD.left + (i / Math.max(nd-1,1)) * chartW; }
  function yPosWR(v) { return PAD.top + chartH - (v / 100) * chartH; }
  if (nd > 1) {
    const grad = ctx.createLinearGradient(0, PAD.top, 0, H-PAD.bottom);
    grad.addColorStop(0, 'rgba(168,85,247,0.25)');
    grad.addColorStop(1, 'rgba(168,85,247,0.01)');
    ctx.fillStyle = grad;
    ctx.beginPath();
    ctx.moveTo(xPos(0), yPosWR(wrs[0]));
    for (let i = 1; i < nd; i++) ctx.lineTo(xPos(i), yPosWR(wrs[i]));
    ctx.lineTo(xPos(nd-1), H-PAD.bottom); ctx.lineTo(xPos(0), H-PAD.bottom);
    ctx.closePath(); ctx.fill();
    ctx.strokeStyle = '#a855f7'; ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(xPos(0), yPosWR(wrs[0]));
    for (let i = 1; i < nd; i++) ctx.lineTo(xPos(i), yPosWR(wrs[i]));
    ctx.stroke();
    wrs.forEach((v, i) => { ctx.fillStyle = '#a855f7'; ctx.beginPath(); ctx.arc(xPos(i), yPosWR(v), 3, 0, Math.PI*2); ctx.fill(); });
  }
  ctx.fillStyle = 'rgba(124,135,150,0.7)'; ctx.font = '9px monospace'; ctx.textAlign = 'center';
  const step = Math.ceil(nd / 10);
  dates.forEach((d, i) => { if (i % step === 0) ctx.fillText(d.replace('2026_','').replace(/_/g,'/'), xPos(i), H-PAD.bottom+18); });
  ctx.textAlign = 'right';
  for (let i = 0; i <= 4; i++) { const v = 100-(100/4)*i; ctx.fillText(v.toFixed(0)+'%', PAD.left-8, PAD.top+(chartH/4)*i+4); }
}
function sortTable(th) {
  const tbody = th.closest('table').querySelector('tbody');
  const rows = Array.from(tbody.querySelectorAll('tr'));
  const idx = Array.from(th.parentElement.children).indexOf(th);
  const asc = th.dataset.asc !== 'true'; th.dataset.asc = asc;
  rows.sort((a, b) => {
    const av = a.cells[idx]?.textContent.replace(/[%+,]/g,'').trim();
    const bv = b.cells[idx]?.textContent.replace(/[%+,]/g,'').trim();
    const an = parseFloat(av), bn = parseFloat(bv);
    if (!isNaN(an) && !isNaN(bn)) return asc ? an-bn : bn-an;
    return asc ? av.localeCompare(bv) : bv.localeCompare(av);
  });
  rows.forEach(r => tbody.appendChild(r));
}
window.addEventListener('resize', () => { if (D['ncaab_summary_by_date']) renderDateChart(); });
loadAll();
