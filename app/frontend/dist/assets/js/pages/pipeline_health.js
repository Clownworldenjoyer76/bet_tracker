const SPORT_SOURCES = [
  { key: 'basketball', label: 'Basketball', path: 'data/pipeline_health/basketball.json' },
  { key: 'mlb',        label: 'MLB',        path: 'data/pipeline_health/mlb.json' },
  { key: 'nhl',        label: 'NHL',        path: 'data/pipeline_health/nhl.json' },
  { key: 'cfb',        label: 'CFB',        path: 'data/pipeline_health/cfb.json' },
  { key: 'soccer',     label: 'Soccer',     path: 'data/pipeline_health/soccer.json' },
  { key: 'ufc',        label: 'UFC',        path: 'data/pipeline_health/ufc.json' }
];

const HEALTH = {};
let activeSport = 'all';

function esc(v) {
  return String(v == null ? '' : v)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&#039;');
}

function arr(v) { return Array.isArray(v) ? v : []; }
function obj(v) { return v && typeof v === 'object' && !Array.isArray(v) ? v : {}; }

function prettyName(value) {
  return String(value || '')
    .replace(/\.txt$/i, '')
    .replace(/\.json$/i, '')
    .replace(/^\d+_/, '')
    .replace(/_/g, ' ')
    .replace(/\b\w/g, c => c.toUpperCase());
}

function stageName(path) {
  const parts = String(path || '').split('/');
  return prettyName(parts[parts.length - 1] || path || 'Stage');
}

function parseStageClass(text) {
  const s = String(text || '').toUpperCase();
  if (/FAILED|FAILURE|ERROR|CRITICAL|FATAL|UNHEALTHY/.test(s)) return 'stage-bad';
  if (/WARNING|WARN/.test(s)) return 'stage-warn';
  if (/SUCCESS|HEALTHY|CLEAN/.test(s)) return 'stage-ok';
  return '';
}

function formatGenerated(value) {
  if (!value) return 'unknown';
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return String(value);
  return d.toLocaleString('en-US', {
    year: 'numeric', month: 'short', day: 'numeric',
    hour: '2-digit', minute: '2-digit', timeZoneName: 'short'
  });
}

function seasonText(cfg) {
  cfg = obj(cfg);
  if (!cfg.start_month || !cfg.start_day || !cfg.end_month || !cfg.end_day) return '';
  const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  return `${months[cfg.start_month - 1]} ${cfg.start_day} – ${months[cfg.end_month - 1]} ${cfg.end_day}`;
}

function collectLeagueIssues(league) {
  const issues = [];
  const coverage = obj(league.coverage);
  const identity = obj(league.identity);
  Object.entries(coverage).forEach(([k, v]) => {
    if (Array.isArray(v) && v.length) issues.push(`${prettyName(k)}: ${v.length}`);
    else if (typeof v === 'number' && v > 0) issues.push(`${prettyName(k)}: ${v}`);
  });
  Object.entries(identity).forEach(([k, v]) => {
    if (Array.isArray(v) && v.length) issues.push(`${prettyName(k)}: ${v.length}`);
    else if (typeof v === 'number' && v > 0) issues.push(`${prettyName(k)}: ${v}`);
  });
  arr(league.issues).forEach(v => issues.push(String(v)));
  arr(league.critical_failures).forEach(v => issues.push(String(v)));
  return issues;
}

function collectWarnings(data) {
  const out = [];
  const seen = new Set();
  const add = v => {
    const s = String(v || '').trim();
    if (!s || seen.has(s)) return;
    seen.add(s); out.push(s);
  };
  arr(data.warnings).forEach(add);
  arr(obj(data.wnba_bias_drift).warnings).forEach(add);
  arr(obj(data.sdv_health).warnings).forEach(add);
  Object.entries(obj(data.leagues)).forEach(([lg, row]) => {
    collectLeagueIssues(obj(row)).forEach(v => add(`${lg.toUpperCase()}: ${v}`));
  });
  Object.entries(obj(obj(data.sdv_health).current)).forEach(([lg, row]) => {
    arr(obj(row).issues).forEach(v => add(`${lg.toUpperCase()}: ${v}`));
    arr(obj(row).critical_failures).forEach(v => add(`${lg.toUpperCase()}: ${v}`));
  });
  return out;
}

function sportStatus(data) {
  if (arr(data.fatal_errors).length) return 'failed';
  const raw = String(data.status || '').toLowerCase();
  if (/fail|error|critical|fatal|unhealthy/.test(raw)) return 'failed';
  if (/warn/.test(raw)) return 'warning';
  return 'healthy';
}

function leagueStatus(key, league, data) {
  if (league.in_season === false) return 'offseason';
  const warnings = collectWarnings(data);
  const hasNamedWarning = warnings.some(w => w.toLowerCase().includes(key.toLowerCase()));
  if (collectLeagueIssues(league).length || hasNamedWarning) return 'warning';
  return 'healthy';
}

function summaryFor(data) {
  const leagues = Object.values(obj(data.leagues));
  const stages = arr(data.stage_status);
  const stageSuccess = stages.filter(s => /SUCCESS/i.test(String(obj(s).status || ''))).length;
  return {
    fatal: arr(data.fatal_errors).length,
    active: leagues.filter(l => obj(l).in_season === true).length,
    stages: `${stageSuccess}/${stages.length}`,
    warnings: collectWarnings(data).length
  };
}

function renderLeagueCard(key, league, data) {
  league = obj(league);
  const c = obj(league.counts);
  const status = leagueStatus(key, league, data);
  const label = status === 'offseason' ? 'Offseason' : status === 'warning' ? 'Warning' : status === 'failed' ? 'Failed' : 'Healthy';
  const issues = collectLeagueIssues(league);
  const season = seasonText(league.season_config);
  let note = season ? `Season: ${season}. ` : '';
  if (issues.length) note += issues.join(' · ');
  else if (league.in_season === true && Number(c.scheduled_games || 0) === 0) note += 'In season; no games scheduled today.';
  else note += 'No coverage or identity issues reported.';
  return `
    <section class="league-card">
      <div class="league-head">
        <div class="league-name">${esc(key.toUpperCase())}</div>
        <span class="badge ${status}">${esc(label)}</span>
      </div>
      <div class="league-body">
        <div class="metrics">
          <div class="metric"><div class="metric-value">${esc(c.scheduled_games ?? 0)}</div><div class="metric-label">Scheduled</div></div>
          <div class="metric"><div class="metric-value">${esc(c.prediction_games ?? 0)}</div><div class="metric-label">Predictions</div></div>
          <div class="metric"><div class="metric-value">${esc(c.sportsbook_games ?? 0)}</div><div class="metric-label">Sportsbook</div></div>
          <div class="metric"><div class="metric-value">${esc(c.merged_games ?? 0)}</div><div class="metric-label">Merged</div></div>
          <div class="metric"><div class="metric-value">${esc(c.selected_bets ?? 0)}</div><div class="metric-label">Selected Bets</div></div>
          <div class="metric"><div class="metric-value">${esc(c.locked_bets ?? 0)}</div><div class="metric-label">Locked Bets</div></div>
        </div>
        <div class="league-note">${esc(note)}</div>
      </div>
    </section>`;
}

function renderWarnings(data) {
  const fatals = arr(data.fatal_errors);
  const warnings = collectWarnings(data);
  let html = '';
  if (fatals.length) {
    html += `<div class="section-title">Fatal Errors</div><div class="warning-box fatal-box"><ul class="warning-list">${fatals.map(v => `<li>${esc(v)}</li>`).join('')}</ul></div>`;
  }
  html += `<div class="section-title">Warnings Requiring Attention</div>`;
  if (!warnings.length) {
    html += `<div class="warning-box"><ul class="warning-list"><li style="color:var(--text-muted)">No warnings reported.</li></ul></div>`;
  } else {
    html += `<div class="warning-box"><ul class="warning-list">${warnings.map(v => `<li>${esc(v)}</li>`).join('')}</ul></div>`;
  }
  return html;
}

function renderStages(data) {
  const stages = arr(data.stage_status);
  if (!stages.length) return '';
  return `
    <div class="section-title">Pipeline Stages</div>
    <div class="table-wrap"><table>
      <thead><tr><th>Stage</th><th>Status</th><th>Log</th></tr></thead>
      <tbody>${stages.map(s => {
        s = obj(s);
        const cls = parseStageClass(s.status);
        return `<tr><td>${esc(stageName(s.path))}</td><td class="${cls}">${esc(s.status || 'Unknown')}</td><td>${esc(s.path || '')}</td></tr>`;
      }).join('')}</tbody>
    </table></div>`;
}

function renderModelHealth(data) {
  const sdv = obj(data.sdv_health);
  if (!Object.keys(sdv).length) return '';
  const cfg = obj(sdv.configs);
  const modelCfg = obj(cfg.model_config);
  const sdvModel = obj(cfg.sdv_model);
  const manifests = obj(sdv.historical_manifests);
  const artifacts = obj(sdv.model_artifacts);
  const weights = obj(sdv.ensemble_weights);
  const artifactRows = Object.entries(artifacts).map(([k,v]) => {
    v = obj(v); return `<div class="data-row"><span class="data-key">${esc(k.toUpperCase())}</span><span class="data-value ${v.valid === false ? 'bad-text' : 'ok'}">${v.valid === false ? 'Invalid' : 'Valid'}</span></div>`;
  }).join('');
  const validWeights = Object.values(weights).filter(v => obj(v).valid === true).length;
  return `
    <div class="section-title">Model &amp; Data Health</div>
    <div class="data-grid">
      <div class="data-card">
        <div class="data-card-title">Production Configuration</div>
        <div class="data-row"><span class="data-key">Prediction source</span><span class="data-value">${esc(sdv.configured_production_source || modelCfg.configured_source || '—')}</span></div>
        <div class="data-row"><span class="data-key">SDV model version</span><span class="data-value">${esc(sdvModel.model_version || '—')}</span></div>
        <div class="data-row"><span class="data-key">Feature version</span><span class="data-value">${esc(sdvModel.feature_version || '—')}</span></div>
        <div class="data-row"><span class="data-key">Historical manifests</span><span class="data-value ${manifests.valid_count === manifests.required_count ? 'ok' : 'warn-text'}">${esc(manifests.valid_count ?? '—')} / ${esc(manifests.required_count ?? '—')} valid</span></div>
      </div>
      <div class="data-card">
        <div class="data-card-title">League Models</div>
        ${artifactRows || '<div class="data-row"><span class="data-key">Artifacts</span><span class="data-value">No artifact summary</span></div>'}
        <div class="data-row"><span class="data-key">Ensemble weights</span><span class="data-value ${validWeights === Object.keys(weights).length ? 'ok' : 'warn-text'}">${validWeights} / ${Object.keys(weights).length} valid</span></div>
      </div>
    </div>`;
}

function renderSport(source, data) {
  const summary = summaryFor(data);
  const status = sportStatus(data);
  const statusLabel = status === 'failed' ? 'Failed' : status === 'warning' ? 'Warning' : 'Healthy';
  const leagues = obj(data.leagues);
  return `
    <section class="sport-panel" data-rendered-sport="${esc(source.key)}">
      <div class="sport-head">
        <div>
          <div class="sport-name">${esc(source.label)}</div>
          <div class="sport-meta">Game date: ${esc(data.game_date_new_york || '—')} · Generated: ${esc(formatGenerated(data.generated_at_utc))}</div>
        </div>
        <span class="badge ${status}">${esc(statusLabel)}</span>
      </div>
      <div class="summary-grid">
        <div class="summary-card"><div class="summary-label">Fatal Errors</div><div class="summary-value ${summary.fatal ? 'bad-text' : ''}">${summary.fatal}</div></div>
        <div class="summary-card"><div class="summary-label">Active Leagues</div><div class="summary-value">${summary.active}</div></div>
        <div class="summary-card"><div class="summary-label">Stages Successful</div><div class="summary-value">${esc(summary.stages)}</div></div>
        <div class="summary-card"><div class="summary-label">Warnings</div><div class="summary-value ${summary.warnings ? 'warn-text' : ''}">${summary.warnings}</div></div>
      </div>
      ${Object.keys(leagues).length ? `<div class="section-title">League Status</div><div class="league-grid">${Object.entries(leagues).map(([k,v]) => renderLeagueCard(k,v,data)).join('')}</div>` : ''}
      ${renderWarnings(data)}
      ${renderStages(data)}
      ${renderModelHealth(data)}
    </section>`;
}

function render() {
  const host = document.getElementById('health-content');
  const selected = activeSport === 'all'
    ? SPORT_SOURCES.filter(s => HEALTH[s.key])
    : SPORT_SOURCES.filter(s => s.key === activeSport && HEALTH[s.key]);

  if (!selected.length) {
    const src = SPORT_SOURCES.find(s => s.key === activeSport);
    host.innerHTML = `<div class="empty-state">${src ? esc(src.label) + ' pipeline health is not available yet' : 'No pipeline health data available'}</div>`;
    return;
  }
  host.innerHTML = selected.map(s => renderSport(s, HEALTH[s.key])).join('');
}

function updateControls() {
  document.querySelectorAll('.sport-pill').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.sport === activeSport);
    if (btn.dataset.sport !== 'all') btn.classList.toggle('unavailable', !HEALTH[btn.dataset.sport]);
  });
}

async function loadAll() {
  const results = await Promise.all(SPORT_SOURCES.map(async source => {
    try {
      const response = await fetch(source.path, { cache: 'no-store' });
      if (!response.ok) return { source, ok: false };
      HEALTH[source.key] = await response.json();
      return { source, ok: true };
    } catch (e) {
      return { source, ok: false };
    }
  }));

  const loaded = results.filter(r => r.ok).length;
  const dot = document.getElementById('load-dot');
  const text = document.getElementById('load-text');
  dot.className = 'status-dot ' + (loaded ? 'green' : 'red');
  text.textContent = loaded
    ? `${loaded} sport pipeline ${loaded === 1 ? 'file' : 'files'} loaded · selectors become active as each sport is added`
    : 'No pipeline health files could be loaded';
  updateControls();
  render();
}

document.getElementById('sport-controls').addEventListener('click', e => {
  const btn = e.target.closest('.sport-pill');
  if (!btn) return;
  activeSport = btn.dataset.sport;
  updateControls();
  render();
});

loadAll();
