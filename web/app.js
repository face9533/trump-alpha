'use strict';

let DATA = null;
let SORT = { key: 'post_date', dir: -1 };
let FILTER = 'ALL';
let KFILTER = 'ALL';

const $ = (s, r = document) => r.querySelector(s);
const el = (tag, cls, html) => {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (html != null) e.innerHTML = html;
  return e;
};

/* ---------- 数值格式 ---------- */
function pctClass(v) { return v == null ? 'flat' : v > 0.0001 ? 'up' : v < -0.0001 ? 'down' : 'flat'; }
function pctText(v) { return v == null ? '—' : (v > 0 ? '+' : '') + v.toFixed(2) + '%'; }
function pctHTML(v) { return `<span class="pct ${pctClass(v)}">${pctText(v)}</span>`; }
function price(v) { return v == null ? '—' : v >= 1000 ? v.toLocaleString('en-US', { maximumFractionDigits: 0 })
  : v.toFixed(2); }

function sentimentChip(s) {
  if (s === 'positive') return '<span class="chip pos">看涨</span>';
  if (s === 'negative') return '<span class="chip neg">看跌</span>';
  return '<span class="chip neu">中性</span>';
}

/* ---------- SVG 走势图 ---------- */
function sparkline(series, marks, w = 240, h = 56) {
  if (!series || series.length < 2) return `<svg width="${w}" height="${h}"></svg>`;
  const ys = series.map(p => p.c);
  const minY = Math.min(...ys), maxY = Math.max(...ys);
  const span = maxY - minY || 1;
  const pad = 4;
  const X = i => pad + (i / (series.length - 1)) * (w - 2 * pad);
  const Y = v => pad + (1 - (v - minY) / span) * (h - 2 * pad);
  const up = ys[ys.length - 1] >= ys[0];
  const color = up ? '#16c784' : '#ea3943';
  const pts = series.map((p, i) => `${X(i).toFixed(1)},${Y(p.c).toFixed(1)}`).join(' ');
  const area = `${X(0)},${h - pad} ${pts} ${X(series.length - 1)},${h - pad}`;
  const gid = 'g' + Math.random().toString(36).slice(2, 8);

  const markLines = (marks || []).map(d => {
    const idx = series.findIndex(p => p.date === d);
    if (idx < 0) return '';
    const x = X(idx).toFixed(1);
    return `<line x1="${x}" y1="${pad}" x2="${x}" y2="${h - pad}" stroke="#d4a943" stroke-width="1" stroke-dasharray="2 2" opacity=".65"/>`
      + `<circle cx="${x}" cy="${Y(series[idx].c).toFixed(1)}" r="2.6" fill="#d4a943"/>`;
  }).join('');

  return `<svg width="${w}" height="${h}" viewBox="0 0 ${w} ${h}" preserveAspectRatio="none">
    <defs><linearGradient id="${gid}" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="${color}" stop-opacity=".22"/>
      <stop offset="1" stop-color="${color}" stop-opacity="0"/>
    </linearGradient></defs>
    <polygon points="${area}" fill="url(#${gid})"/>
    ${markLines}
    <polyline points="${pts}" fill="none" stroke="${color}" stroke-width="1.6"
      stroke-linejoin="round" stroke-linecap="round"/>
  </svg>`;
}

/* ---------- K 线（蜡烛图）---------- */
function fmtP(v) { return v >= 1000 ? Math.round(v).toLocaleString('en-US') : v.toFixed(2); }

function candlestick(series, opts = {}) {
  const w = opts.w || 600, h = opts.h || 200;
  const padL = 8, padR = 46, padT = 14, padB = 18;
  if (!series || series.length < 2)
    return '<div class="cs-empty">该时段行情数据不足，无法绘制 K 线。</div>';
  const n = series.length;
  const hi = Math.max(...series.map(p => p.h));
  const lo = Math.min(...series.map(p => p.l));
  const span = (hi - lo) || 1;
  const plotW = w - padL - padR, plotH = h - padT - padB;
  const step = plotW / n;
  const cw = Math.max(1.5, Math.min(16, step * 0.6));
  const Xc = i => padL + step * (i + 0.5);
  const Y = v => padT + (1 - (v - lo) / span) * plotH;
  const upC = '#16c784', dnC = '#ea3943';

  let candles = '';
  series.forEach((p, i) => {
    const x = Xc(i), up = p.c >= p.o, col = up ? upC : dnC;
    const top = Math.min(Y(p.o), Y(p.c)), bot = Math.max(Y(p.o), Y(p.c));
    candles += `<line x1="${x.toFixed(1)}" y1="${Y(p.h).toFixed(1)}" x2="${x.toFixed(1)}" y2="${Y(p.l).toFixed(1)}" stroke="${col}" stroke-width="1"/>`
      + `<rect x="${(x - cw / 2).toFixed(1)}" y="${top.toFixed(1)}" width="${cw.toFixed(1)}" height="${Math.max(1, bot - top).toFixed(1)}" fill="${col}"/>`;
  });

  let marks = '';
  (opts.marks || []).forEach(d => {
    const idx = series.findIndex(p => p.date === d);
    if (idx < 0) return;
    const x = Xc(idx);
    marks += `<rect x="${(x - cw / 2 - 2.5).toFixed(1)}" y="${padT}" width="${(cw + 5).toFixed(1)}" height="${plotH}" fill="#d4a943" opacity=".10"/>`
      + `<line x1="${x.toFixed(1)}" y1="${padT}" x2="${x.toFixed(1)}" y2="${h - padB}" stroke="#d4a943" stroke-width="1" stroke-dasharray="3 3" opacity=".75"/>`
      + `<text x="${x.toFixed(1)}" y="${(padT - 4).toFixed(1)}" fill="#d4a943" font-size="9" text-anchor="middle">喊单</text>`;
  });

  const axis = `<text x="${w - padR + 5}" y="${(Y(hi) + 3).toFixed(1)}" fill="#5a6076" font-size="9">${fmtP(hi)}</text>`
    + `<text x="${w - padR + 5}" y="${(Y(lo) + 3).toFixed(1)}" fill="#5a6076" font-size="9">${fmtP(lo)}</text>`
    + `<text x="${padL}" y="${h - 5}" fill="#5a6076" font-size="9">${series[0].date.slice(5)}</text>`
    + `<text x="${w - padR}" y="${h - 5}" fill="#5a6076" font-size="9" text-anchor="end">${series[n - 1].date.slice(5)}</text>`;

  return `<svg viewBox="0 0 ${w} ${h}" width="${w}" height="${h}" class="cs">${marks}${candles}${axis}</svg>`;
}

// 取某次喊单的"喊单后"窗口：喊单日前 3 根到后 maxAfter 根
function postCallWindow(ticker, entryDate, maxAfter = 30) {
  const ch = (DATA.charts[ticker] || { series: [] }).series;
  const idx = ch.findIndex(p => p.date === entryDate);
  if (idx < 0) return ch;
  return ch.slice(Math.max(0, idx - 3), Math.min(ch.length, idx + maxAfter + 1));
}

// 喊单后涨幅轨迹折线图
function trajChart(traj, peak) {
  const w = 560, h = 196, padL = 10, padR = 42, padT = 20, padB = 22;
  if (!traj || traj.length < 2) return '<div class="cs-empty">轨迹数据不足。</div>';
  const ys = traj.map(t => t.avg);
  const minY = Math.min(0, ...ys), maxY = Math.max(...ys, 0.5);
  const span = (maxY - minY) || 1;
  const plotW = w - padL - padR, plotH = h - padT - padB;
  const X = i => padL + (i / (traj.length - 1)) * plotW;
  const Y = v => padT + (1 - (v - minY) / span) * plotH;
  const pts = traj.map((t, i) => `${X(i).toFixed(1)},${Y(t.avg).toFixed(1)}`).join(' ');
  const area = `${X(0).toFixed(1)},${Y(minY).toFixed(1)} ${pts} ${X(traj.length - 1).toFixed(1)},${Y(minY).toFixed(1)}`;
  const zeroY = Y(0).toFixed(1);

  let peakEl = '';
  if (peak) {
    const pi = traj.findIndex(t => t.day === peak.day);
    if (pi >= 0) {
      const px = X(pi), py = Y(peak.avg);
      peakEl = `<line x1="${px.toFixed(1)}" y1="${padT}" x2="${px.toFixed(1)}" y2="${h - padB}" stroke="#d4a943" stroke-dasharray="3 3" stroke-width="1" opacity=".7"/>`
        + `<circle cx="${px.toFixed(1)}" cy="${py.toFixed(1)}" r="3.6" fill="#d4a943"/>`
        + `<text x="${px.toFixed(1)}" y="${(py - 9).toFixed(1)}" fill="#d4a943" font-size="11" text-anchor="middle" font-weight="700">第${peak.day}日 ${pctText(peak.avg)}</text>`;
    }
  }
  const xlabels = traj.map((t, i) => t.day % 2 === 0
    ? `<text x="${X(i).toFixed(1)}" y="${h - 6}" fill="#5a6076" font-size="9" text-anchor="middle">${t.day}</text>` : '').join('');

  return `<svg viewBox="0 0 ${w} ${h}" width="${w}" height="${h}" class="cs">
    <line x1="${padL}" y1="${zeroY}" x2="${w - padR}" y2="${zeroY}" stroke="#2b3142" stroke-width="1"/>
    <polygon points="${area}" fill="rgba(22,199,132,.12)"/>
    <polyline points="${pts}" fill="none" stroke="#16c784" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>
    ${peakEl}${xlabels}
    <text x="${w - padR + 5}" y="${(Y(maxY) + 3).toFixed(1)}" fill="#5a6076" font-size="9">${pctText(maxY)}</text>
    <text x="${w - padR + 5}" y="${(parseFloat(zeroY) + 3).toFixed(1)}" fill="#5a6076" font-size="9">0%</text>
  </svg>`;
}

/* ---------- 主渲染 ---------- */
function render() {
  const d = DATA;
  $('#asof-date').textContent = d.as_of_date;
  $('#gen-time').textContent = d.generated_at.replace('T', ' ').slice(0, 16);

  renderStats(d.summary);
  renderAnalytics(d);
  renderReview(d.daily_review);
  renderReviewHistory(d);
  renderTickers(d);
  renderKlines(d);
  renderFilters(d);
  renderTable(d);

  $('#status').hidden = true;
  ['#stats', '#analytics', '#review', '#review-history', '#tickers', '#klines', '#mentions']
    .forEach(s => { $(s).hidden = false; });
}

function renderStats(s) {
  const box = $('#stats');
  box.innerHTML = '';
  if (!s || !s.count) {
    box.innerHTML = '<div class="stat" style="grid-column:1/-1">近期窗口内未检测到股票相关喊单。</div>';
    return;
  }
  const cards = [
    { k: '追踪喊单数', v: s.count, note: `${s.unique_tickers} 只不同标的` },
    { k: '整体胜率', v: s.win_rate + '<small>%</small>', note: '自喊单以来上涨占比', accent: true },
    { k: '平均涨幅', v: pctText(s.avg_return_since), note: '自喊单以来', cls: pctClass(s.avg_return_since) },
    { k: '跑赢大盘', v: pctText(s.avg_excess_since),
      note: `${s.beat_market_rate == null ? '—' : s.beat_market_rate + '%'} 喊单跑赢标普`,
      cls: pctClass(s.avg_excess_since) },
    { k: '看涨喊单胜率', v: (s.bull_win_rate == null ? '—' : s.bull_win_rate + '<small>%</small>'),
      note: `他明确看好的 ${s.bull_count} 次` },
    { k: '最佳标的', v: s.best.ticker, note: `${s.best.company} ${pctText(s.best.return)}`, accent: true },
  ];
  cards.forEach(c => {
    const e = el('div', 'stat' + (c.accent ? ' accent' : ''));
    e.innerHTML = `<div class="k">${c.k}</div>
      <div class="v ${c.cls || ''}">${c.v}</div>
      <div class="note">${c.note}</div>`;
    box.appendChild(e);
  });
}

function renderAnalytics(d) {
  const a = d.analytics;
  if (!a || !a.count) { $('#analytics').hidden = true; return; }

  $('#findings').innerHTML = (a.findings || []).map((f, i) =>
    `<div class="finding"><span class="fnum">${i + 1}</span><span>${escapeHTML(f)}</span></div>`).join('');

  $('#traj-cap').textContent = `同一批 ${a.cohort_n} 次喊单 · 横轴＝喊单后第几个交易日`;
  $('#traj-chart').innerHTML = trajChart(a.trajectory, a.peak);

  $('#horizons').innerHTML = (a.horizons || []).map(h =>
    `<div class="hz">
       <div class="hz-k">${h.key}</div>
       <div class="hz-v ${pctClass(h.avg)}">${pctText(h.avg)}</div>
       <div class="hz-w">胜率 ${h.win}%</div>
     </div>`).join('');

  $('#sector-bars').innerHTML = (a.sectors || []).map(s => {
    const small = s.n < 3 ? '<span class="sb-small">样本少</span>' : '';
    const tone = s.win >= 60 ? 'good' : s.win >= 40 ? 'mid' : 'bad';
    return `<div class="sb-row">
      <div class="sb-name">${s.sector}${small}</div>
      <div class="sb-track"><div class="sb-fill ${tone}" style="width:${Math.max(4, s.win)}%"></div></div>
      <div class="sb-win">${s.win}%</div>
      <div class="sb-meta">${s.n}次 · 均${pctText(s.avg)}${s.excess == null ? '' : ' · 超额' + pctText(s.excess)}</div>
    </div>`;
  }).join('');
}

function renderReview(r) {
  if (!r) return;
  $('#review-date').textContent = r.date;
  $('#review-headline').textContent = r.headline;

  const nb = $('#review-new'); nb.innerHTML = '';
  if (!r.new_mentions || !r.new_mentions.length) {
    nb.appendChild(el('div', 'empty', '基准日当天没有新的股票相关喊单。'));
  } else {
    r.new_mentions.forEach(m => {
      const e = el('div', 'new-item');
      e.innerHTML = `<div class="ni-head"><span class="tk-badge">${m.ticker}</span>
        <span class="tc-company">${m.company}</span> ${sentimentChip(m.sentiment)}</div>
        <div class="ni-text">"${escapeHTML(m.excerpt)}"</div>
        <a href="${m.post_url}" target="_blank" rel="noopener">查看原文 ↗</a>`;
      nb.appendChild(e);
    });
  }

  const mb = $('#review-movers'); mb.innerHTML = '';
  if (!r.movers || !r.movers.length) {
    mb.appendChild(el('div', 'empty', '当日无可用行情。'));
  } else {
    r.movers.forEach(m => {
      const e = el('div', 'movers-row');
      e.innerHTML = `<span class="tk">${m.ticker}</span>
        <span class="co">${m.company}</span>
        ${pctHTML(m.day_move)}
        <span class="since">累计 ${pctText(m.return_since)}</span>`;
      mb.appendChild(e);
    });
  }
}

function renderReviewHistory(d) {
  const list = $('#rh-list'); list.innerHTML = '';
  const latest = d.daily_review ? d.daily_review.date : null;
  // 排除最新那天（已在上方"每日复盘"详细展示），其余倒序
  const rows = (d.review_history || []).filter(r => r.date !== latest);
  if (!rows.length) {
    list.innerHTML = '<div class="rh-empty">暂无更早的复盘存档——系统每天会自动多存一条，过几天这里就会积累起来。</div>';
    return;
  }
  list.innerHTML = rows.slice(0, 40).map(r =>
    `<div class="rh-item">
      <div class="rh-date">${r.date.slice(5)}</div>
      <div class="rh-headline">${escapeHTML(r.headline)}</div>
    </div>`).join('');
}

function renderTickers(d) {
  // 聚合每只标的
  const g = {};
  d.mentions.forEach(r => { (g[r.ticker] ||= []).push(r); });
  const grid = $('#ticker-grid'); grid.innerHTML = '';
  const tickers = Object.keys(g).sort((a, b) => g[b].length - g[a].length);
  tickers.forEach(tk => {
    const rs = g[tk];
    const latest = rs.reduce((a, b) => a.post_datetime > b.post_datetime ? a : b);
    const rets = rs.map(r => r.return_since).filter(v => v != null);
    const avg = rets.length ? rets.reduce((a, b) => a + b, 0) / rets.length : null;
    const ch = d.charts[tk] || { series: [], marks: [] };
    const card = el('div', 'ticker-card');
    card.innerHTML = `
      <div class="tc-head">
        <div><div class="tc-ticker">${tk} ${rs[0].type === 'crypto' ? '<span class="chip crypto">币</span>' : ''}</div>
          <div class="tc-company">${rs[0].company}</div></div>
        <div class="tc-ret ${pctClass(avg)}">${pctText(avg)}<small>平均涨幅</small></div>
      </div>
      <div class="tc-spark">${sparkline(ch.series, ch.marks)}</div>
      <div class="tc-foot"><span>${rs.length} 次喊单</span><span>最近 ${latest.post_date}</span></div>`;
    card.addEventListener('click', () => openModal(tk, rs, rs[0].company));
    grid.appendChild(card);
  });
}

/* ---------- 喊单后 K 线专区 ---------- */
function klineCard(r) {
  const series = postCallWindow(r.ticker, r.entry_date);
  const metrics = [
    ['次日', r.return_next_day], ['3日', r.return_3d], ['一周', r.return_1w],
    ['至今', r.return_since], ['最高浮盈', r.max_gain], ['最大回撤', r.max_drawdown],
  ];
  return `<div class="kl-card">
    <div class="kl-head">
      <div class="kl-id"><span class="tk-badge">${r.ticker}</span>
        <span class="tc-company">${r.company}</span> ${sentimentChip(r.sentiment)}</div>
      <div class="kl-date">${r.post_date}</div>
    </div>
    <div class="kl-excerpt">"${escapeHTML(r.excerpt)}"</div>
    <div class="kl-chart">${candlestick(series, { marks: [r.entry_date], w: 620, h: 188 })}</div>
    <div class="kl-metrics">
      ${metrics.map(([k, v]) => `<div class="klm"><span class="klm-k">${k}</span>${pctHTML(v)}</div>`).join('')}
    </div>
    ${r.excess_since == null ? '' :
      `<div class="kl-excess ${r.excess_since >= 0 ? 'win' : 'lose'}">vs 大盘 <b>${pctText(r.excess_since)}</b> · 同期标普 ${pctText(r.bench_since)}</div>`}
    <div class="kl-read">${escapeHTML(r.kline_read || '')}</div>
    <a class="kl-link" href="${r.post_url}" target="_blank" rel="noopener">查看原文 ↗</a>
  </div>`;
}

function renderKlineFilters(d) {
  const tickers = [...new Set(d.mentions.map(r => r.ticker))]
    .sort((a, b) => count(d, b) - count(d, a));
  const box = $('#kline-filters'); box.innerHTML = '';
  const mk = (val, label) => {
    const b = el('button', val === KFILTER ? 'active' : '', label);
    b.addEventListener('click', () => { KFILTER = val; renderKlines(d); });
    return b;
  };
  box.appendChild(mk('ALL', '最近喊单'));
  tickers.forEach(t => box.appendChild(mk(t, `${t} ${count(d, t)}`)));
}

function renderKlines(d) {
  renderKlineFilters(d);
  const list = $('#kline-list'); list.innerHTML = '';
  let rows = d.mentions.slice(); // 已按时间倒序
  if (KFILTER !== 'ALL') rows = rows.filter(r => r.ticker === KFILTER);
  const limit = KFILTER === 'ALL' ? 8 : rows.length;
  const show = rows.slice(0, limit);
  if (!show.length) { list.innerHTML = '<div class="empty">暂无喊单。</div>'; return; }
  list.innerHTML = show.map(klineCard).join('');
  if (KFILTER === 'ALL' && rows.length > show.length) {
    list.insertAdjacentHTML('beforeend',
      `<div class="kl-more">仅显示最近 ${show.length} 次喊单；点上方标的可看该股全部，或点「标的总览」卡片看整段 K 线。</div>`);
  }
}

function renderFilters(d) {
  const tickers = [...new Set(d.mentions.map(r => r.ticker))]
    .sort((a, b) => count(d, b) - count(d, a));
  const box = $('#filters'); box.innerHTML = '';
  const mk = (val, label) => {
    const b = el('button', val === FILTER ? 'active' : '', label);
    b.addEventListener('click', () => { FILTER = val; renderFilters(d); renderTable(d); });
    return b;
  };
  box.appendChild(mk('ALL', `全部 ${d.mentions.length}`));
  tickers.forEach(t => box.appendChild(mk(t, `${t} ${count(d, t)}`)));
}
function count(d, t) { return d.mentions.filter(r => r.ticker === t).length; }

function renderTable(d) {
  const body = $('#mentions-body'); body.innerHTML = '';
  let rows = d.mentions.slice();
  if (FILTER !== 'ALL') rows = rows.filter(r => r.ticker === FILTER);
  rows.sort((a, b) => {
    let x = a[SORT.key], y = b[SORT.key];
    if (x == null) x = -Infinity; if (y == null) y = -Infinity;
    if (typeof x === 'string') return SORT.dir * x.localeCompare(y);
    return SORT.dir * (x - y);
  });
  rows.forEach(r => {
    const tr = el('tr');
    tr.innerHTML = `
      <td>${r.post_date}</td>
      <td><span class="tk-badge">${r.ticker}</span> <span class="tc-company">${r.company}</span></td>
      <td>${sentimentChip(r.sentiment)}</td>
      <td class="num">${price(r.entry_price)}</td>
      <td class="num">${price(r.latest_price)}</td>
      <td class="num">${pctHTML(r.return_since)}</td>
      <td class="num">${pctHTML(r.return_next_day)}</td>
      <td class="num">${pctHTML(r.return_1w)}</td>
      <td class="num">${pctHTML(r.max_gain)}</td>
      <td class="excerpt"><a href="${r.post_url}" target="_blank" rel="noopener" title="查看原文">"${escapeHTML(r.excerpt)}"</a></td>`;
    body.appendChild(tr);
  });
  if (!rows.length) body.innerHTML = '<tr><td colspan="10" class="empty">无记录</td></tr>';
}

/* ---------- 弹层 ---------- */
function openModal(tk, rs, company) {
  const ch = DATA.charts[tk] || { series: [], marks: [] };
  const sorted = rs.slice().sort((a, b) => b.post_datetime.localeCompare(a.post_datetime));
  const c = $('#modal-content');
  c.innerHTML = `
    <h2>${tk} <span style="font-size:15px;color:var(--text-dim)">${company}</span></h2>
    <div class="m-sub">${rs.length} 次喊单 · 整段 K 线 · 金色虚线＝喊单当日</div>
    <div class="m-chart">${candlestick(ch.series, { marks: ch.marks, w: 720, h: 248 })}</div>
    <h3 class="m-h3">每次喊单 · 喊单后走势</h3>
    <div class="kline-list">${sorted.map(klineCard).join('')}</div>`;
  $('#modal').hidden = false;
}
function closeModal() { $('#modal').hidden = true; }

/* ---------- 工具 ---------- */
function escapeHTML(s) {
  return (s || '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
}

function bindSorting() {
  document.querySelectorAll('thead th[data-sort]').forEach(th => {
    th.addEventListener('click', () => {
      const key = th.dataset.sort;
      SORT.dir = SORT.key === key ? -SORT.dir : (key === 'ticker' || key === 'post_date' ? 1 : -1);
      SORT.key = key;
      renderTable(DATA);
    });
  });
}

/* ---------- 启动 ---------- */
async function boot() {
  bindSorting();
  $('#modal-close').addEventListener('click', closeModal);
  $('#modal').addEventListener('click', e => { if (e.target.id === 'modal') closeModal(); });
  document.addEventListener('keydown', e => { if (e.key === 'Escape') closeModal(); });
  try {
    const res = await fetch('data.json?t=' + Date.now());
    if (!res.ok) throw new Error('HTTP ' + res.status);
    DATA = await res.json();
    render();
  } catch (e) {
    const s = $('#status');
    s.className = 'status-box error';
    s.innerHTML = `加载 data.json 失败：${e.message}<br><br>
      请确认已运行 <code>python -m pipeline.update</code> 生成数据，<br>
      并通过本地服务器打开（用项目里的 <code>./start.sh</code>），<br>
      而不是直接双击 index.html。`;
  }
}
boot();
