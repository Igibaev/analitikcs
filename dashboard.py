"""
Renders the final HTML dashboard from a report dict (output of analyze.build_report).
Injects real data as JSON into the same dark-theme template.
"""
import json
from pathlib import Path


_TEMPLATE = """<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>Claude Code Impact · {team_name}</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-annotation@3"></script>
  <style>
    *{{box-sizing:border-box;margin:0;padding:0}}
    body{{font-family:'Segoe UI',sans-serif;background:#0f1117;color:#e2e8f0;min-height:100vh}}
    header{{background:linear-gradient(135deg,#1a1f35,#0d1b2a);border-bottom:1px solid #2d3748;
      padding:20px 32px;display:flex;align-items:center;justify-content:space-between}}
    header h1{{font-size:20px;font-weight:700;color:#fff}}
    header h1 span{{color:#e88c30}}
    .badge{{background:#e88c30;color:#000;font-size:11px;font-weight:700;
      padding:3px 10px;border-radius:99px;letter-spacing:.5px}}
    .team-bar{{background:#161b2e;border-bottom:1px solid #2d3748;padding:12px 32px;
      display:flex;align-items:center;gap:16px;font-size:13px;color:#94a3b8}}
    .team-bar strong{{color:#fff}}
    .sep{{color:#3a4460}}
    .main{{padding:0 32px 32px;background:#1e2540;margin:0 32px;
      border:1px solid #3b4a6b;border-top:none;border-radius:0 8px 8px 8px}}
    .kpi-strip{{display:grid;grid-template-columns:repeat(5,1fr);gap:16px;padding:24px 0 20px}}
    .qbs-kpi-strip{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:16px}}
    .kpi{{background:#161b2e;border:1px solid #2d3748;border-radius:10px;padding:16px 18px}}
    .kpi-label{{font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:.5px;margin-bottom:6px}}
    .kpi-val{{font-size:26px;font-weight:700;color:#fff}}
    .kpi-delta{{font-size:12px;margin-top:4px}}
    .kpi-delta.up{{color:#4ade80}}
    .kpi-delta.down{{color:#f87171}}
    .kpi-delta.neutral{{color:#94a3b8}}
    .section-title{{font-size:14px;font-weight:700;color:#94a3b8;text-transform:uppercase;
      letter-spacing:.8px;padding:12px 0 14px;border-top:1px solid #2d3748;
      margin-top:8px;display:flex;align-items:center;gap:10px}}
    .charts-row{{display:grid;grid-template-columns:1.4fr 1fr;gap:16px;margin-bottom:16px}}
    .qbs-grid{{display:grid;grid-template-columns:1fr 1.6fr;gap:16px;margin-bottom:16px}}
    .chart-card{{background:#161b2e;border:1px solid #2d3748;border-radius:10px;padding:18px}}
    .chart-card h3{{font-size:13px;font-weight:600;color:#94a3b8;margin-bottom:14px}}
    .chart-wrap{{position:relative;height:200px}}
    .epics-table,.status-table{{width:100%;border-collapse:collapse;font-size:13px;margin-bottom:16px}}
    .epics-table th,.status-table th{{text-align:left;color:#64748b;font-weight:600;
      padding:8px 10px;border-bottom:1px solid #2d3748;font-size:11px;text-transform:uppercase}}
    .epics-table td,.status-table td{{padding:9px 10px;border-bottom:1px solid #1a2035;color:#e2e8f0;vertical-align:middle}}
    .epics-table tr:hover td,.status-table tr:hover td{{background:#1e2850}}
    .status-pill{{font-size:11px;font-weight:700;padding:2px 10px;border-radius:99px}}
    .pill-done{{background:#14532d;color:#4ade80}}
    .pill-progress{{background:#1e3a5f;color:#60a5fa}}
    .pill-overdue{{background:#450a0a;color:#f87171}}
    .delta-cell{{font-weight:700}}
    .delta-pos{{color:#4ade80}}
    .delta-neg{{color:#f87171}}
    .neutral{{color:#94a3b8}}
    .status-dot{{width:10px;height:10px;border-radius:50%;display:inline-block;margin-right:7px;vertical-align:middle}}
    .sentiment-row{{display:flex;gap:12px;margin-bottom:16px}}
    .sent-box{{flex:1;background:#161b2e;border:1px solid #2d3748;border-radius:10px;padding:14px;text-align:center}}
    .sent-box .s-label{{font-size:11px;color:#64748b;margin-bottom:6px}}
    .sent-box .s-icon{{font-size:28px;margin-bottom:4px}}
    .sent-box .s-q1{{font-size:13px;color:#94a3b8}}
    .sent-box .s-q2{{font-size:20px;font-weight:700;color:#fff}}
    .sent-box .s-arrow{{font-size:12px}}
    .arrow-up{{color:#4ade80}}
    .arrow-down{{color:#f87171}}
    .insight-box{{background:linear-gradient(135deg,#1a2a1a,#162035);border:1px solid #2d5a2d;
      border-radius:10px;padding:18px 20px;margin-bottom:16px;font-size:13px;line-height:1.7;color:#94a3b8}}
    .insight-box h3{{color:#4ade80;font-size:13px;font-weight:700;margin-bottom:8px}}
    .insight-box ul{{padding-left:18px}}
    .insight-box li{{margin-bottom:4px}}
    .insight-box strong{{color:#e2e8f0}}
    .legend{{display:flex;gap:16px;font-size:12px;color:#64748b;margin-bottom:12px}}
    .legend span{{display:flex;align-items:center;gap:5px}}
    .legend-dot{{width:10px;height:10px;border-radius:50%}}
    .tab-row{{display:flex;gap:8px;padding:20px 32px 0}}
    .tab{{padding:8px 20px;border-radius:8px 8px 0 0;font-size:13px;font-weight:600;
      border:1px solid #2d3748;border-bottom:none;background:#161b2e;color:#64748b}}
    .tab.active{{background:#1e2540;color:#fff;border-color:#3b4a6b}}
    .tab .dot{{width:8px;height:8px;border-radius:50%;display:inline-block;margin-right:6px}}
    .dot.red{{background:#f87171}}
    .dot.green{{background:#4ade80}}
    .refresh-btn{{background:#1e3a5f;border:1px solid #3b4a6b;color:#60a5fa;
      font-size:12px;padding:6px 16px;border-radius:6px;cursor:pointer}}
  </style>
</head>
<body>
<header>
  <h1>Claude Code Impact · <span>{team_name}</span></h1>
  <div style="display:flex;gap:10px;align-items:center;">
    <span style="font-size:12px;color:#64748b;">Данные: {generated_at}</span>
    <div class="badge">LIVE DATA</div>
  </div>
</header>
<div class="team-bar">
  <strong>Команда: {team_name}</strong>
  <span class="sep">|</span>
  Q1: {q1_label} (без Claude Code)
  <span class="sep">|</span>
  Q2: {q2_label} (с Claude Code)
</div>
<div class="tab-row">
  <div class="tab active"><span class="dot red"></span>Q1 vs Q2</div>
  <div class="tab"><span class="dot green"></span>Jira Эпики</div>
  <div class="tab"><span class="dot green"></span>QBS Статусы</div>
  <div class="tab"><span class="dot green"></span>Review Quality</div>
</div>
<div class="main">

  <!-- KPI Strip -->
  <div class="kpi-strip" id="kpiStrip"></div>

  <!-- Charts -->
  <div class="section-title"><span>📈</span>Динамика по неделям</div>
  <div class="charts-row">
    <div class="chart-card">
      <h3>Коммиты в неделю — Q1 vs Q2</h3>
      <div class="chart-wrap"><canvas id="commitChart"></canvas></div>
    </div>
    <div class="chart-card">
      <h3>Размер MR — медиана строк по месяцам</h3>
      <div class="chart-wrap"><canvas id="mrSizeChart"></canvas></div>
    </div>
  </div>

  <!-- Epics -->
  <div class="section-title"><span>🗂</span>Jira Эпики — Q1 vs Q2</div>
  <table class="epics-table">
    <thead><tr>
      <th>Эпик</th><th>Статус</th>
      <th>Q1 дней</th><th>Q2 дней</th><th>Δ время</th>
      <th>Q1 subtasks</th><th>Q2 subtasks</th>
    </tr></thead>
    <tbody id="epicsBody"></tbody>
  </table>

  <!-- QBS -->
  <div class="section-title"><span>🧪</span>QBS — Аналитика по статусам</div>
  <div class="qbs-kpi-strip" id="qbsKpi"></div>
  <div class="qbs-grid">
    <div class="chart-card" style="display:flex;flex-direction:column;gap:12px;">
      <h3>Распределение по статусам</h3>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;">
        <div>
          <div style="font-size:11px;color:#64748b;text-align:center;margin-bottom:6px;">Q1 (без CC)</div>
          <div style="position:relative;height:150px;"><canvas id="donutQ1"></canvas></div>
        </div>
        <div>
          <div style="font-size:11px;color:#64748b;text-align:center;margin-bottom:6px;">Q2 (с CC)</div>
          <div style="position:relative;height:150px;"><canvas id="donutQ2"></canvas></div>
        </div>
      </div>
      <div id="donutLegend" style="display:flex;flex-wrap:wrap;gap:8px;font-size:11px;color:#94a3b8;"></div>
    </div>
    <div class="chart-card">
      <h3>Задачи по статусам — помесячно</h3>
      <div class="chart-wrap" style="height:240px;"><canvas id="qbsStackedBar"></canvas></div>
    </div>
  </div>

  <div class="chart-card" style="margin-bottom:16px;">
    <h3 style="margin-bottom:14px;">Детализация по статусам — Q1 vs Q2</h3>
    <table class="status-table">
      <thead><tr>
        <th>Статус</th>
        <th>Q1 задач</th><th>Q1 %</th>
        <th>Q2 задач</th><th>Q2 %</th>
        <th>Δ задач</th>
        <th>Cycle Q1 (д)</th><th>Cycle Q2 (д)</th><th>Δ cycle</th>
      </tr></thead>
      <tbody id="statusBody"></tbody>
    </table>
  </div>

  <div class="charts-row" style="margin-bottom:16px;">
    <div class="chart-card">
      <h3>Среднее время в статусе (дней)</h3>
      <div class="chart-wrap" style="height:220px;"><canvas id="cycleTimeChart"></canvas></div>
    </div>
    <div class="chart-card">
      <h3>Blocked & Reopened по месяцам</h3>
      <div class="chart-wrap" style="height:220px;"><canvas id="blockedChart"></canvas></div>
    </div>
  </div>

  <!-- Review quality -->
  <div class="section-title"><span>💬</span>Качество code review</div>
  <div class="sentiment-row" id="sentimentRow"></div>

  <!-- Insight -->
  <div class="insight-box">
    <h3>AI-вывод: Влияние Claude Code</h3>
    <ul id="insightList"></ul>
  </div>

</div>

<script>
const DATA = {data_json};

// ── helpers ──────────────────────────────────────────────────────────────────
const darkScales = {{
  x:{{ticks:{{color:'#64748b',font:{{size:10}}}},grid:{{color:'#1e2a40'}}}},
  y:{{ticks:{{color:'#64748b',font:{{size:10}}}},grid:{{color:'#1e2a40'}}}}
}};

function deltaClass(d) {{ return d?.positive === true ? 'delta-pos' : d?.positive === false ? 'delta-neg' : 'neutral'; }}
function kpiDeltaClass(d) {{ return d?.positive === true ? 'up' : d?.positive === false ? 'down' : 'neutral'; }}

// ── KPI strip ─────────────────────────────────────────────────────────────────
const kpi = DATA.kpi;
const kpiDefs = [
  ['Эпики закрыты', kpi.epics_done.q2, kpi.epics_done.delta],
  ['Avg cycle time (д)', kpi.cycle_days.q2, kpi.cycle_days.delta],
  ['Размер MR (строк)', kpi.diff_size.q2, kpi.diff_size.delta],
  ['Время ревью (ч)', kpi.review_hours.q2, kpi.review_hours.delta],
  ['Коммитов/неделю', kpi.commits_per_week.q2, kpi.commits_per_week.delta],
];
document.getElementById('kpiStrip').innerHTML = kpiDefs.map(([label, val, d]) => `
  <div class="kpi">
    <div class="kpi-label">${{label}}</div>
    <div class="kpi-val">${{val ?? '—'}}</div>
    <div class="kpi-delta ${{kpiDeltaClass(d)}}">${{d?.label ?? '—'}}</div>
  </div>`).join('');

// ── Commit chart ───────────────────────────────────────────────────────────────
const w1 = DATA.weekly_commits_q1, w2 = DATA.weekly_commits_q2;
const wLabels = Array.from({{length: Math.max(w1.length,w2.length)}}, (_,i) => 'Н'+(i+1));
new Chart(document.getElementById('commitChart'), {{
  type:'line',
  data:{{
    labels: wLabels,
    datasets:[
      {{label:'Q1 (без CC)',data:w1,borderColor:'#f87171',backgroundColor:'rgba(248,113,113,0.1)',tension:0.4,fill:true,pointRadius:3}},
      {{label:'Q2 (с CC)',  data:w2,borderColor:'#4ade80',backgroundColor:'rgba(74,222,128,0.1)', tension:0.4,fill:true,pointRadius:3}},
    ]
  }},
  options:{{responsive:true,maintainAspectRatio:false,
    plugins:{{legend:{{labels:{{color:'#94a3b8',font:{{size:11}}}}}}}},scales:darkScales}}
}});

// MR size — monthly (we approximate from diff_size medians stored per member)
// Placeholder: render q1/q2 medians as two bars
new Chart(document.getElementById('mrSizeChart'), {{
  type:'bar',
  data:{{
    labels:['Q1','Q2'],
    datasets:[{{
      data:[DATA.kpi.diff_size.q1, DATA.kpi.diff_size.q2],
      backgroundColor:['rgba(248,113,113,0.75)','rgba(74,222,128,0.75)'],
      borderRadius:6,
    }}]
  }},
  options:{{responsive:true,maintainAspectRatio:false,
    plugins:{{legend:{{display:false}}}},scales:darkScales}}
}});

// ── Epics table ───────────────────────────────────────────────────────────────
const eq1 = DATA.epics_q1.epics || [];
const eq2 = DATA.epics_q2.epics || [];
// Match by summary keyword (best-effort without stable ID across periods)
const epicMap = {{}};
eq1.forEach(e => {{ epicMap[e.key] = {{q1:e}}; }});
eq2.forEach(e => {{
  const match = Object.values(epicMap).find(m => m.q1?.summary === e.summary);
  if (match) match.q2 = e; else epicMap[e.key] = {{q2:e}};
}});

const pillClass = s => s?.toLowerCase().includes('done') || s?.toLowerCase().includes('closed') ? 'pill-done'
  : s?.toLowerCase().includes('progress') ? 'pill-progress' : 'pill-overdue';

document.getElementById('epicsBody').innerHTML = Object.values(epicMap).map({{q1:e1,q2:e2}} => {{
  const e = e1 || e2;
  const d = e1?.cycle_days != null && e2?.cycle_days != null ? e2.cycle_days - e1.cycle_days : null;
  const dClass = d === null ? 'neutral' : d < 0 ? 'delta-pos' : 'delta-neg';
  const dLabel = d === null ? '—' : (d<0?'':'+')+d+'д '+(d<0?'▲':'▼');
  return `<tr>
    <td>${{e.key}} · ${{e.summary}}</td>
    <td><span class="status-pill ${{pillClass(e.status)}}">${{e.status}}</span></td>
    <td>${{e1?.cycle_days ?? '—'}}</td>
    <td>${{e2?.cycle_days ?? '—'}}</td>
    <td class="delta-cell ${{dClass}}">${{dLabel}}</td>
    <td>${{e1?.subtask_count ?? '—'}}</td>
    <td>${{e2?.subtask_count ?? '—'}}</td>
  </tr>`;
}}).join('');

// ── QBS KPI ───────────────────────────────────────────────────────────────────
const qbs = DATA.qbs;
const qbsDefs = [
  ['Всего задач Q2', qbs.total_q2, `▲ +${{qbs.total_q2 - qbs.total_q1}} vs Q1 (${{qbs.total_q1}})`],
  ['Done rate Q2', qbs.done_rate_q2+'%', `▲ +${{(qbs.done_rate_q2-qbs.done_rate_q1).toFixed(1)}}pp vs Q1 (${{qbs.done_rate_q1}}%)`],
];
document.getElementById('qbsKpi').innerHTML = qbsDefs.map(([l,v,d]) => `
  <div class="kpi"><div class="kpi-label">${{l}}</div>
  <div class="kpi-val">${{v}}</div>
  <div class="kpi-delta up">${{d}}</div></div>`).join('');

// ── Donuts ────────────────────────────────────────────────────────────────────
const STATUS_COLORS = {{
  'Done':'#4ade80','In Progress':'#60a5fa','In Review':'#a78bfa',
  'Testing':'#fbbf24','To Do':'#64748b','Blocked':'#f87171','Reopened':'#fb923c',
}};
const defaultColor = '#475569';
const allStatuses = [...new Set([...Object.keys(qbs.status_q1), ...Object.keys(qbs.status_q2)])];

function makeDonut(canvasId, statusMap, total) {{
  const labels = allStatuses;
  const data   = labels.map(s => statusMap[s]?.count || 0);
  const colors = labels.map(s => STATUS_COLORS[s] || defaultColor);
  new Chart(document.getElementById(canvasId), {{
    type:'doughnut',
    data:{{labels,datasets:[{{data,backgroundColor:colors,borderWidth:0}}]}},
    options:{{responsive:true,maintainAspectRatio:false,cutout:'68%',
      plugins:{{legend:{{display:false}},
        tooltip:{{callbacks:{{label:c=>`${{c.label}}: ${{c.raw}} (${{Math.round(c.raw/total*100)}}%)`}}}}}}}}
  }});
}}
makeDonut('donutQ1', qbs.status_q1, qbs.total_q1);
makeDonut('donutQ2', qbs.status_q2, qbs.total_q2);

document.getElementById('donutLegend').innerHTML = allStatuses.map(s =>
  `<span><span style="display:inline-block;width:9px;height:9px;border-radius:2px;
    background:${{STATUS_COLORS[s]||defaultColor}};margin-right:4px;"></span>${{s}}</span>`
).join('');

// ── Stacked bar ───────────────────────────────────────────────────────────────
const allMonths = [...new Set([...Object.keys(qbs.monthly_q1), ...Object.keys(qbs.monthly_q2)])].sort();
new Chart(document.getElementById('qbsStackedBar'), {{
  type:'bar',
  data:{{
    labels: allMonths,
    datasets: allStatuses.map(s => ({{
      label: s,
      data: allMonths.map(m => (qbs.monthly_q1[m]||{{}})[s] || (qbs.monthly_q2[m]||{{}})[s] || 0),
      backgroundColor: STATUS_COLORS[s] || defaultColor,
      stack:'s',
    }}))
  }},
  options:{{responsive:true,maintainAspectRatio:false,
    plugins:{{legend:{{labels:{{color:'#94a3b8',font:{{size:10}},boxWidth:10}}}}}},
    scales:{{
      x:{{stacked:true,ticks:{{color:'#64748b',font:{{size:10}}}},grid:{{color:'#1e2a40'}}}},
      y:{{stacked:true,ticks:{{color:'#64748b',font:{{size:10}}}},grid:{{color:'#1e2a40'}}}}
    }}
  }}
}});

// ── Status breakdown table ────────────────────────────────────────────────────
const totalQ1 = qbs.total_q1 || 1, totalQ2 = qbs.total_q2 || 1;
document.getElementById('statusBody').innerHTML = allStatuses.map(s => {{
  const s1 = qbs.status_q1[s] || {{}};
  const s2 = qbs.status_q2[s] || {{}};
  const c1 = s1.count || 0, c2 = s2.count || 0;
  const dd = c2 - c1;
  const ddClass = dd < 0 && s === 'Done' ? 'delta-neg' : dd > 0 && s === 'Done' ? 'delta-pos'
    : dd < 0 ? 'delta-pos' : dd > 0 ? 'delta-neg' : 'neutral';
  const cy1 = s1.avg_cycle_days, cy2 = s2.avg_cycle_days;
  const cyd = cy1 != null && cy2 != null ? (cy2-cy1).toFixed(1) : null;
  const cyClass = cyd == null ? 'neutral' : parseFloat(cyd) < 0 ? 'delta-pos' : 'delta-neg';
  return `<tr>
    <td><span class="status-dot" style="background:${{STATUS_COLORS[s]||defaultColor}}"></span>${{s}}</td>
    <td>${{c1}}</td><td>${{Math.round(c1/totalQ1*100)}}%</td>
    <td>${{c2}}</td><td>${{Math.round(c2/totalQ2*100)}}%</td>
    <td class="delta-cell ${{ddClass}}">${{dd>0?'+':''}}${{dd}}</td>
    <td>${{cy1??'—'}}</td><td>${{cy2??'—'}}</td>
    <td class="delta-cell ${{cyClass}}">${{cyd!=null?(parseFloat(cyd)<0?'':'+')+cyd+'д':'—'}}</td>
  </tr>`;
}}).join('') + `<tr style="background:#0f1420;font-weight:700;">
  <td>Итого</td><td>${{qbs.total_q1}}</td><td>100%</td>
  <td>${{qbs.total_q2}}</td><td>100%</td>
  <td class="delta-pos">+${{qbs.total_q2-qbs.total_q1}}</td>
  <td colspan="3" style="color:#64748b;font-weight:400;font-size:11px;">Cycle считается по закрытым задачам</td>
</tr>`;

// ── Cycle time chart ──────────────────────────────────────────────────────────
const cycleStatuses = allStatuses.filter(s => {{
  const c1 = qbs.status_q1[s]?.avg_cycle_days, c2 = qbs.status_q2[s]?.avg_cycle_days;
  return c1 != null || c2 != null;
}});
new Chart(document.getElementById('cycleTimeChart'), {{
  type:'bar',
  data:{{
    labels: cycleStatuses,
    datasets:[
      {{label:'Q1',data:cycleStatuses.map(s=>qbs.status_q1[s]?.avg_cycle_days||0),backgroundColor:'rgba(248,113,113,0.75)',borderRadius:4}},
      {{label:'Q2',data:cycleStatuses.map(s=>qbs.status_q2[s]?.avg_cycle_days||0),backgroundColor:'rgba(74,222,128,0.75)', borderRadius:4}},
    ]
  }},
  options:{{responsive:true,maintainAspectRatio:false,
    plugins:{{legend:{{labels:{{color:'#94a3b8',font:{{size:11}}}}}}}},
    scales:{{
      x:{{ticks:{{color:'#64748b',font:{{size:10}}}},grid:{{color:'#1e2a40'}}}},
      y:{{ticks:{{color:'#64748b',font:{{size:10}},callback:v=>v+'д'}},grid:{{color:'#1e2a40'}}}}
    }}
  }}
}});

// Blocked & Reopened
const blockedQ1 = allMonths.map(m => (qbs.monthly_q1[m]||{{}})['Blocked']||0);
const blockedQ2 = allMonths.map(m => (qbs.monthly_q2[m]||{{}})['Blocked']||0);
const reopenedQ1 = allMonths.map(m => (qbs.monthly_q1[m]||{{}})['Reopened']||0);
const reopenedQ2 = allMonths.map(m => (qbs.monthly_q2[m]||{{}})['Reopened']||0);
new Chart(document.getElementById('blockedChart'), {{
  type:'line',
  data:{{
    labels: allMonths,
    datasets:[
      {{label:'Blocked',  data:[...blockedQ1,...blockedQ2],  borderColor:'#f87171',backgroundColor:'rgba(248,113,113,0.15)',tension:0.4,fill:true,pointRadius:4}},
      {{label:'Reopened', data:[...reopenedQ1,...reopenedQ2],borderColor:'#fb923c',backgroundColor:'rgba(251,146,60,0.15)', tension:0.4,fill:true,pointRadius:4}},
    ]
  }},
  options:{{responsive:true,maintainAspectRatio:false,
    plugins:{{legend:{{labels:{{color:'#94a3b8',font:{{size:11}}}}}}}},scales:darkScales}}
}});

// ── Sentiment ─────────────────────────────────────────────────────────────────
const rv = DATA.review;
const sentDefs = [
  ['🔴','Критические / MR', rv.q1.avg_critical_comments, rv.q2.avg_critical_comments, true],
  ['🟡','Nitpick / style',  rv.q1.avg_nitpick_comments,  rv.q2.avg_nitpick_comments,  true],
  ['🟢','Одобрение / LGTM', rv.q1.avg_approval_comments, rv.q2.avg_approval_comments, false],
  ['✅','First-pass rate',  rv.q1.first_pass_rate,        rv.q2.first_pass_rate,        false],
];
document.getElementById('sentimentRow').innerHTML = sentDefs.map(([icon,label,v1,v2,invertGood]) => {{
  const diff = v2 - v1;
  const good = invertGood ? diff < 0 : diff > 0;
  const arrow = diff > 0 ? '▲' : '▼';
  const cls = good ? 'arrow-up' : 'arrow-down';
  const pct = v1 ? Math.round(Math.abs(diff)/v1*100) : 0;
  return `<div class="sent-box">
    <div class="s-label">${{label}}</div>
    <div class="s-icon">${{icon}}</div>
    <div class="s-q1">Q1: ${{v1??'—'}}</div>
    <div class="s-q2">Q2: ${{v2??'—'}}</div>
    <div class="s-arrow ${{cls}}">${{arrow}} ${{pct}}%</div>
  </div>`;
}}).join('');

// ── Insights ──────────────────────────────────────────────────────────────────
const insights = [];
if (DATA.kpi.epics_done.delta.positive) {{
  insights.push(`Команда закрыла на <strong>${{DATA.kpi.epics_done.delta.raw}}</strong> эпиков больше в Q2.`);
}}
if (DATA.kpi.cycle_days.delta.positive) {{
  insights.push(`Среднее время цикла сократилось на <strong>${{Math.abs(DATA.kpi.cycle_days.delta.raw)}}д</strong>.`);
}}
if (DATA.kpi.diff_size.delta.positive) {{
  insights.push(`Медиана размера MR снизилась на <strong>${{Math.abs(DATA.kpi.diff_size.delta.raw)}} строк</strong> — код стал атомарнее.`);
}}
if (DATA.kpi.review_hours.delta.positive) {{
  insights.push(`Время code review сократилось на <strong>${{Math.abs(DATA.kpi.review_hours.delta.raw)}}ч</strong> в среднем.`);
}}
if (rv.q2.first_pass_rate > rv.q1.first_pass_rate) {{
  insights.push(`First-pass approval rate вырос с <strong>${{rv.q1.first_pass_rate}}%</strong> до <strong>${{rv.q2.first_pass_rate}}%</strong>.`);
}}
const doneDelta = (qbs.done_rate_q2 - qbs.done_rate_q1).toFixed(1);
insights.push(`Done rate по QBS задачам: ${{qbs.done_rate_q1}}% → <strong>${{qbs.done_rate_q2}}%</strong> (+${{doneDelta}}pp).`);

if (!insights.length) insights.push('Недостаточно данных для автовыводов — проверьте конфигурацию.');
document.getElementById('insightList').innerHTML = insights.map(i => `<li>${{i}}</li>`).join('');
</script>
</body>
</html>
"""


def render(report: dict, output_path: str = "dashboard.html") -> str:
    import datetime
    data_json = json.dumps(report, ensure_ascii=False, indent=None)
    html = _TEMPLATE.format(
        team_name=report.get("team_name", "Team"),
        q1_label=report.get("q1_label", ""),
        q2_label=report.get("q2_label", ""),
        generated_at=datetime.datetime.now().strftime("%d.%m.%Y %H:%M"),
        data_json=data_json,
    )
    Path(output_path).write_text(html, encoding="utf-8")
    return output_path
