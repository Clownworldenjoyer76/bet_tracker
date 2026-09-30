const SOURCE='data/pipeline_health/nhl.json';
const esc=v=>String(v??'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
const pretty=v=>String(v||'').replace(/_/g,' ').replace(/\b\w/g,c=>c.toUpperCase());
fetch(SOURCE+'?v='+Date.now(),{cache:'no-store'}).then(r=>{if(!r.ok)throw new Error('HTTP '+r.status);return r.json();}).then(d=>{
  const s=String(d.status||'unknown').toLowerCase(); const badge=document.getElementById('status'); badge.textContent=s.toUpperCase(); badge.classList.add(s);
  document.getElementById('meta').textContent=`Report date: ${d.report_date||'—'} · Generated: ${d.generated_at_utc||'—'} · Workflow: ${d.workflow?.status||'—'}`;
  const counts=Object.entries(d.counts||{}).map(([k,v])=>`<div class="card"><div class="k">${esc(pretty(k))}</div><div class="v">${esc(v)}</div></div>`).join('');
  const fat=(d.fatal_errors||[]), warn=(d.warnings||[]);
  const stages=(d.stage_status||[]).map(x=>`<tr><td>${esc(x.name||'')}</td><td class="${String(x.status||'').includes('FAILED')?'failed':''}">${esc(x.status||'')}</td><td>${esc(x.path||'')}</td></tr>`).join('');
  document.getElementById('content').innerHTML=`<div class="grid">${counts}</div>
    <div class="title">Fatal Errors</div><div class="panel">${fat.length?'<ul>'+fat.map(x=>'<li class="failed">'+esc(x)+'</li>').join('')+'</ul>':'<span class="muted">None</span>'}</div>
    <div class="title">Warnings</div><div class="panel">${warn.length?'<ul>'+warn.map(x=>'<li class="warning">'+esc(x)+'</li>').join('')+'</ul>':'<span class="muted">None</span>'}</div>
    <div class="title">Pipeline Stages</div><div class="table"><table><thead><tr><th>Stage</th><th>Status</th><th>Path</th></tr></thead><tbody>${stages}</tbody></table></div>`;
}).catch(e=>{document.getElementById('meta').textContent='Failed to load '+SOURCE;document.getElementById('status').textContent='ERROR';document.getElementById('status').classList.add('failed');document.getElementById('content').innerHTML='<div class="panel failed">'+esc(e.message)+'</div>';});
