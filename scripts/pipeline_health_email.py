#!/usr/bin/env python3
"""Read-only pipeline health digest; SMTP sending is optional."""
import argparse
import html
import json
import os
import re
import smtplib
import ssl
from datetime import datetime, timezone
from email.message import EmailMessage
from email.utils import formataddr, getaddresses
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

ROOT = Path(__file__).resolve().parents[1]
BAD = re.compile(r'\b(?:FAIL(?:ED|URE)?|ERROR|FATAL)\b', re.I)
WARN = re.compile(r'\bWARN(?:ING)?\b', re.I)
SUCCESS = re.compile(r'\bSUCCESS\b', re.I)


def fmt(x):
    return str(x).replace('_', ' ').strip().title()


def parse_dt(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace('Z', '+00:00')).replace(tzinfo=timezone.utc) if datetime.fromisoformat(str(value).replace('Z', '+00:00')).tzinfo is None else datetime.fromisoformat(str(value).replace('Z', '+00:00')).astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


def uniq(items):
    seen, out = set(), []
    for item in items:
        s = str(item).strip()
        if s and s not in seen:
            seen.add(s)
            out.append(s)
    return out


def stages_of(doc):
    stages = list(doc.get('stage_status') or [])
    if not stages:
        for workflow in (doc.get('workflows') or {}).values():
            stages.extend(workflow.get('stages') or [])
    return stages


def status_of(doc):
    """Do not conflate health=healthy with confirmed workflow success."""
    workflows = [doc['workflow']] if isinstance(doc.get('workflow'), dict) else []
    workflows += [v for v in (doc.get('workflows') or {}).values() if isinstance(v, dict)]
    workflow_statuses = [str(w.get('status', '')).lower() for w in workflows if w.get('status')]
    if any(x in ('failure', 'failed', 'error', 'cancelled', 'timed_out') for x in workflow_statuses):
        return 'Failed', 'bad'
    if doc.get('fatal_errors'):
        return 'Failed (fatal errors)', 'bad'
    stage_failures = [s for s in stages_of(doc) if BAD.search(str(s.get('status', ''))) or int(s.get('error_count') or 0) > 0]
    if stage_failures:
        return 'Failed steps reported', 'bad'
    if workflow_statuses and all(x in ('success', 'successful', 'completed') for x in workflow_statuses):
        return 'Pipeline Successful', 'good'
    if str(doc.get('status', '')).lower() in ('failed', 'failure', 'error', 'fatal'):
        return 'Pipeline Failed', 'bad'
    return 'Success not confirmed', 'unknown'


def nonempty(v):
    if isinstance(v, list):
        return len(v)
    if isinstance(v, bool):
        return int(v)
    if isinstance(v, (int, float)):
        return v
    return 0


def gather(doc, cfg, now):
    include = cfg['report']['include']
    sections = {k: [] for k in ('Warnings', 'Fatal errors / failed steps', 'Missing predictions, odds and IDs', 'Game and bet counts', 'Missing output files', 'Model health and validation')}
    add = lambda k, v: sections[k].append(str(v))
    if include.get('warnings'):
        for w in doc.get('warnings') or []:
            add('Warnings', w)
        for league, d in (doc.get('leagues') or {}).items():
            for w in d.get('warnings') or []:
                add('Warnings', w)
        for key in ('sdv_health', 'wnba_bias_drift'):
            for w in (doc.get(key) or {}).get('warnings') or []:
                add('Warnings', w)
    if include.get('fatal_errors'):
        for error in doc.get('fatal_errors') or []:
            add('Fatal errors / failed steps', error)
    if include.get('failed_steps') or include.get('warnings'):
        for stage in stages_of(doc):
            label = stage.get('display_path') or stage.get('name') or stage.get('script') or stage.get('path') or 'Unnamed stage'
            st = str(stage.get('status') or 'Unknown')
            if include.get('failed_steps') and (BAD.search(st) or int(stage.get('error_count') or 0) > 0):
                add('Fatal errors / failed steps', f'{label}: {st} (errors: {stage.get("error_count", 0)})')
            elif include.get('warnings') and (WARN.search(st) or int(stage.get('warning_count') or 0) > 0):
                add('Warnings', f'{label}: {st}')
    if include.get('coverage'):
        for league, d in (doc.get('leagues') or {}).items():
            for group in ('coverage', 'identity'):
                for key, val in (d.get(group) or {}).items():
                    if any(t in key for t in ('missing', 'blank', 'conflict', 'duplicate', 'mismatch', 'not_merged', 'not_scheduled')) and nonempty(val):
                        msg = f'{league.upper()}: {fmt(key)}: {nonempty(val)}'
                        if cfg['report'].get('include_full_game_id_lists') and isinstance(val, list):
                            msg += ' [' + ', '.join(map(str, val)) + ']'
                        add('Missing predictions, odds and IDs', msg)
            for key in ('issues', 'critical_failures'):
                value = d.get(key)
                if isinstance(value, list):
                    for item in value:
                        add('Missing predictions, odds and IDs', f'{league.upper()}: {item}')
                elif isinstance(value, dict):
                    for k, v in value.items():
                        if nonempty(v):
                            add('Missing predictions, odds and IDs', f'{league.upper()}: {fmt(k)}: {nonempty(v)}')
    if include.get('counts'):
        groups = {league.upper(): d.get('counts') or {} for league, d in (doc.get('leagues') or {}).items()}
        if isinstance(doc.get('counts'), dict):
            groups['Overall'] = doc['counts']
        for group, counts in groups.items():
            filtered = [f'{fmt(k)}: {v}' for k, v in counts.items() if isinstance(v, (int, float)) and (v or cfg['report'].get('include_zero_counts', True))]
            if filtered:
                add('Game and bet counts', group + ' — ' + '; '.join(filtered))
    if include.get('missing_outputs'):
        for stage in stages_of(doc):
            st = str(stage.get('status') or '')
            if stage.get('exists') is False or 'NO OUTPUT' in st.upper():
                add('Missing output files', f'{stage.get("name") or stage.get("script") or stage.get("path") or "Stage"}: {st}; {stage.get("path", "no path")}')
        for name, artifact in (doc.get('artifacts') or {}).items():
            if isinstance(artifact, dict):
                if artifact.get('exists') is False:
                    add('Missing output files', f'{fmt(name)}: {artifact.get("path", "missing")}')
                for f in artifact.get('missing_files') or []:
                    add('Missing output files', f'{fmt(name)}: {f}')
    if include.get('model_health'):
        for key in ('model_health', 'validation', 'report_health', 'sdv_health'):
            d = doc.get(key)
            if not isinstance(d, dict):
                continue
            selected = {k: v for k, v in d.items() if k in ('status', 'checks_failed', 'checks_total', 'failed_reports', 'warning_reports', 'invalid_targets', 'deferred_targets', 'configured_production_source', 'validation_scope')}
            if selected:
                add('Model health and validation', f'{fmt(key)}: ' + '; '.join(f'{fmt(k)}: {v}' for k, v in selected.items()))
        for league, d in (doc.get('leagues') or {}).items():
            if d.get('critical_failures'):
                add('Model health and validation', f'{league.upper()} critical failures: {d["critical_failures"]}')
    for k in sections:
        sections[k] = uniq(sections[k])[:int(cfg['report'].get('max_items_per_section', 100))]
    return sections


def build(cfg, root):
    now = datetime.now(timezone.utc)
    tz = ZoneInfo(cfg['report'].get('timezone', 'America/New_York'))
    max_age = float(cfg['report'].get('freshness_hours', 48))
    rows = []
    for key, label in cfg['pipelines'].items():
        path = root / 'frontend' / 'data' / 'pipeline_health' / f'{key}.json'
        error = None
        try:
            doc = json.loads(path.read_text(encoding='utf-8'))
            if not isinstance(doc, dict):
                raise ValueError('JSON root must be an object')
            status, color = status_of(doc)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            doc, status, color, error = {}, 'Report unavailable', 'bad', str(exc)
        stamp = parse_dt(doc.get('generated_at_utc'))
        age = round((now - stamp).total_seconds() / 3600, 1) if stamp else None
        stale = age is None or age > max_age or age < -0.25
        sections = gather(doc, cfg, now) if doc else {k: [] for k in ('Warnings', 'Fatal errors / failed steps', 'Missing predictions, odds and IDs', 'Game and bet counts', 'Missing output files', 'Model health and validation')}
        if error:
            sections['Fatal errors / failed steps'].append('Unable to read JSON: ' + error)
        rows.append(dict(key=key, label=label, status=status, color=color, health=doc.get('status', 'unavailable'), timestamp=stamp, age=age, stale=stale, sections=sections))
    return now, tz, rows


def render(cfg, now, tz, rows):
    esc = lambda v: html.escape(str(v), quote=True)
    colors = {'good': '#16783b', 'bad': '#b42318', 'unknown': '#8a5b00'}
    parts = [f'<html><body style="font-family:Arial,sans-serif;color:#17212b;max-width:850px;margin:auto"><h2>{esc(cfg["report"]["title"])}</h2>', f'<p>Generated: {esc(now.astimezone(tz).strftime("%Y-%m-%d %I:%M %p %Z"))}</p>']
    for r in rows:
        c = colors[r['color']]
        parts.append(f'<div style="padding:7px 0;border-bottom:1px solid #ddd"><strong>{esc(r["label"])}</strong> — <strong style="color:{c}">{esc(r["status"])}</strong>' + (' <span style="color:#b42318">[STALE]</span>' if r['stale'] else '') + '</div>')
    for heading in ('Warnings', 'Fatal errors / failed steps', 'Missing predictions, odds and IDs', 'Game and bet counts', 'Missing output files', 'Model health and validation'):
        if any(r['sections'][heading] for r in rows):
            parts.append(f'<h3 style="margin-top:24px">{esc(heading)}</h3>')
            for r in rows:
                items = r['sections'][heading]
                if items:
                    parts.append(f'<h4>{esc(r["label"])}</h4><ul>')
                    parts.extend(f'<li>{esc(item)}</li>' for item in items)
                    parts.append('</ul>')
    if cfg['report']['include'].get('timestamps', True):
        parts.append('<h3>Report freshness</h3><table style="border-collapse:collapse;width:100%"><tr><th align="left">Pipeline</th><th align="left">JSON generated</th><th align="left">Age</th><th align="left">Freshness</th></tr>')
        for r in rows:
            when = r['timestamp'].astimezone(tz).strftime('%Y-%m-%d %I:%M %p %Z') if r['timestamp'] else 'Unknown'
            parts.append(f'<tr><td>{esc(r["label"])}</td><td>{esc(when)}</td><td>{esc(str(r["age"]) + " hours" if r["age"] is not None else "Unknown")}</td><td>{"STALE" if r["stale"] else "Fresh"}</td></tr>')
        parts.append('</table>')
    parts.append('<p style="font-size:12px;color:#666">Statuses reflect repository JSON data, not live GitHub Actions queries. Missing output may be expected when there are no games or events. A healthy report does not independently prove workflow success.</p></body></html>')
    return ''.join(parts)


def send(cfg, html_body, rows):
    required = ['SMTP_HOST', 'SMTP_PORT', 'SMTP_USER', 'SMTP_PASSWORD', 'EMAIL_FROM', 'EMAIL_TO']
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        raise RuntimeError('Missing GitHub Actions secrets: ' + ', '.join('PIPELINE_EMAIL_' + k.removeprefix('SMTP_') if False else {'SMTP_HOST':'PIPELINE_EMAIL_SMTP_HOST','SMTP_PORT':'PIPELINE_EMAIL_SMTP_PORT','SMTP_USER':'PIPELINE_EMAIL_SMTP_USER','SMTP_PASSWORD':'PIPELINE_EMAIL_SMTP_PASSWORD','EMAIL_FROM':'PIPELINE_EMAIL_FROM','EMAIL_TO':'PIPELINE_EMAIL_TO'}[k] for k in missing))
    recipients = [addr for _, addr in getaddresses([os.environ['EMAIL_TO']]) if addr]
    if not recipients:
        raise RuntimeError('EMAIL_TO contains no valid recipient addresses')
    message = EmailMessage()
    message['From'] = formataddr((cfg['email'].get('from_name', 'Bet Tracker'), os.environ['EMAIL_FROM']))
    message['To'] = ', '.join(recipients)
    message['Subject'] = cfg['email'].get('subject_prefix', '[Bet Tracker] Pipeline Health') + ' | ' + datetime.now(timezone.utc).strftime('%Y-%m-%d')
    message.set_content('Pipeline health report is attached as HTML in this message. Use an HTML-capable email client.')
    message.add_alternative(html_body, subtype='html')
    host, port = os.environ['SMTP_HOST'], int(os.environ['SMTP_PORT'])
    security = cfg['email'].get('smtp_security', 'starttls').lower()
    context = ssl.create_default_context()
    if security == 'ssl':
        client = smtplib.SMTP_SSL(host, port, timeout=30, context=context)
    elif security == 'starttls':
        client = smtplib.SMTP(host, port, timeout=30)
    else:
        raise ValueError('smtp_security must be starttls or ssl')
    with client:
        client.ehlo()
        if security == 'starttls':
            client.starttls(context=context)
            client.ehlo()
        client.login(os.environ['SMTP_USER'], os.environ['SMTP_PASSWORD'])
        client.send_message(message)
    print('Email sent to', len(recipients), 'recipient(s)')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', default='config/pipeline_health_email.yaml')
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--output', type=Path, default=Path('pipeline_health_report.html'))
    parser.add_argument('--send', action='store_true')
    args = parser.parse_args()
    cfg = yaml.safe_load((args.root / args.config).read_text(encoding='utf-8'))
    now, tz, rows = build(cfg, args.root)
    body = render(cfg, now, tz, rows)
    args.output.write_text(body, encoding='utf-8')
    print('Report generated:', args.output, '| pipelines:', len(rows))
    for r in rows:
        print(r['label'], '|', r['status'], '|', 'STALE' if r['stale'] else 'fresh')
    if args.send:
        send(cfg, body, rows)


if __name__ == '__main__':
    main()
