/**
 * ultraexchange — renderer.js
 */

const BASE = (window.APP_CONFIG && window.APP_CONFIG.backendUrl) || 'http://127.0.0.1:5678';

const $ = id => document.getElementById(id);
const E = {
  boot:       $('boot'),
  priceVal:   $('price-val'),
  symLabel:   $('sym-label'),
  liveDot:    $('live-dot'),
  liveTxt:    $('live-txt'),
  smaMain:    $('sma-main'),
  smaVal:     $('sma-val'),
  upperVal:   $('upper-val'),
  lowerVal:   $('lower-val'),
  upperLbl:   $('upper-lbl'),
  lowerLbl:   $('lower-lbl'),
  bandZone:   $('band-zone'),
  bandNeedle: $('band-needle'),
  usdVal:     $('usd-val'),
  cryptoVal:  $('crypto-val'),
  cryptoSym:  $('crypto-sym'),
  statusPill: $('status-pill'),
  statusText: $('status-text'),
  statSym:    $('stat-sym'),
  statInterval: $('stat-interval'),
  statTrade:  $('stat-trade'),
  logOutput:  $('log-output'),
  logCount:   $('log-count'),
  btnStart:   $('btn-start'),
  btnStop:    $('btn-stop'),
  inApiKey:   $('in-api-key'),
  inSymbol:   $('in-symbol'),
  inInterval: $('in-interval'),
  inTrade:    $('in-trade'),
  inWallet:   $('in-wallet'),
};

let logCount  = 0;
let lastPrice = 0;
let evtSource = null;

// ─────────────────────────────
async function boot() {
  await waitForBackend();
  await loadConfig();
  syncStatus();
  startLogStream();
  setInterval(syncStatus, 2200);
  E.boot.classList.add('hidden');
}

async function waitForBackend(retries = 50, delay = 400) {
  for (let i = 0; i < retries; i++) {
    try {
      const r = await fetch(`${BASE}/api/config`, { signal: AbortSignal.timeout(900) });
      if (r.ok) return;
    } catch (_) {}
    await sleep(delay);
  }
}

async function loadConfig() {
  try {
    const d = await (await fetch(`${BASE}/api/config`)).json();
    if (d.api_key) E.inApiKey.value = d.api_key;
  } catch (_) {}
}

// ─────────────────────────────
async function syncStatus() {
  try {
    const d = await (await fetch(`${BASE}/api/status`)).json();
    render(d);
  } catch (_) {}
}

function render(d) {
  const { price, sma, upper, lower, is_running, symbol, usd, holdings, trade_amt, interval } = d;
  const sym = symbol || 'BTC';

  // Symbol
  E.symLabel.textContent  = `${sym} / USD`;
  E.cryptoSym.textContent = sym;
  E.statSym.textContent   = sym;
  E.statInterval.textContent = interval ? `${interval}s` : '—';
  E.statTrade.textContent    = trade_amt ? fmt$(trade_amt) : '—';

  // Price
  if (price) {
    E.priceVal.textContent = fmt$(price);
    if (price > lastPrice && lastPrice > 0)      flash(E.priceVal, 'up');
    else if (price < lastPrice && lastPrice > 0) flash(E.priceVal, 'down');
    lastPrice = price;
  }

  // Bollinger
  const f = v => v != null ? fmt$(v) : '—';
  E.smaMain.textContent  = sma   ? `SMA ${fmt$(sma)}` : 'SMA —';
  E.smaVal.textContent   = f(sma);
  E.upperVal.textContent = f(upper);
  E.lowerVal.textContent = f(lower);
  E.upperLbl.textContent = upper ? fmt$(upper) : '$—';
  E.lowerLbl.textContent = lower ? fmt$(lower) : '$—';

  // Band visualizer
  if (upper != null && lower != null && price != null) {
    const range  = upper - lower;
    const pct    = range > 0 ? Math.max(0, Math.min(1, (price - lower) / range)) : 0.5;
    // needle sits at `pct` across the full width
    E.bandNeedle.style.left = `${(pct * 100).toFixed(1)}%`;
  }

  // Portfolio
  E.usdVal.textContent    = fmt$(usd);
  E.cryptoVal.textContent = (holdings || 0).toFixed(6);

  // Status
  if (is_running) {
    E.statusPill.classList.add('running');
    E.statusText.textContent = 'Synchronizing';
    E.liveDot.classList.add('on');
    E.liveTxt.textContent = 'live';
    E.btnStart.disabled = true;
    E.btnStop.disabled  = false;
    lockInputs(true);
  } else {
    E.statusPill.classList.remove('running');
    E.statusText.textContent = 'Suspended';
    E.liveDot.classList.remove('on');
    E.liveTxt.textContent = 'offline';
    E.btnStart.disabled = false;
    E.btnStop.disabled  = true;
    lockInputs(false);
  }
}

// ─────────────────────────────
function startLogStream() {
  if (evtSource) evtSource.close();
  evtSource = new EventSource(`${BASE}/api/logs`);
  evtSource.onmessage = e => appendLog(JSON.parse(e.data));
}

function appendLog(line) {
  logCount++;
  E.logCount.textContent = `${logCount} event${logCount !== 1 ? 's' : ''}`;

  const m    = line.match(/^\[(\d{2}:\d{2}:\d{2})\]\s+(.*)$/);
  const time = m ? m[1] : '';
  const msg  = m ? m[2] : line;

  let cls = '';
  if (/Filled BUY/i.test(msg))    cls = 'buy';
  else if (/Filled SELL/i.test(msg)) cls = 'sell';
  else if (/Error/i.test(msg))    cls = 'err';
  else if (/System:/i.test(msg))  cls = 'sys';
  else if (/Signal:/i.test(msg))  cls = 'sig';

  const row = document.createElement('div');
  row.className = `log-row ${cls}`;
  row.innerHTML = `<span class="log-ts">${time}</span><span class="log-body">${esc(msg)}</span>`;
  E.logOutput.appendChild(row);
  E.logOutput.scrollTop = E.logOutput.scrollHeight;

  while (E.logOutput.children.length > 500) E.logOutput.removeChild(E.logOutput.firstChild);
}

// ─────────────────────────────
E.btnStart.addEventListener('click', async () => {
  const key = E.inApiKey.value.trim();
  if (!key) {
    E.inApiKey.style.borderColor = 'rgba(251,113,133,0.55)';
    E.inApiKey.focus();
    setTimeout(() => E.inApiKey.style.borderColor = '', 1600);
    return;
  }

  E.btnStart.disabled = true;
  E.btnStart.textContent = 'Starting…';

  try {
    const res = await fetch(`${BASE}/api/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        api_key:   key,
        symbol:    (E.inSymbol.value.trim() || 'BTC').toUpperCase(),
        interval:  parseInt(E.inInterval.value)  || 300,
        trade_amt: parseFloat(E.inTrade.value)   || 500,
        wallet:    parseFloat(E.inWallet.value)  || 10000,
      }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Start failed');
    syncStatus();
  } catch (e) {
    appendLog(`[--:--:--]  Error: ${e.message}`);
    E.btnStart.disabled = false;
  }

  E.btnStart.innerHTML = `<svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"/></svg> Initialize Sync`;
});

E.btnStop.addEventListener('click', async () => {
  await fetch(`${BASE}/api/stop`, { method: 'POST' });
  syncStatus();
});

// ─────────────────────────────
function fmt$(n) {
  return new Intl.NumberFormat('en-US', {
    style: 'currency', currency: 'USD', minimumFractionDigits: 2
  }).format(n);
}

function flash(el, cls) {
  el.classList.remove('up', 'down');
  void el.offsetWidth;
  el.classList.add(cls);
  setTimeout(() => el.classList.remove(cls), 1400);
}

function lockInputs(v) {
  [E.inApiKey, E.inSymbol, E.inInterval, E.inTrade, E.inWallet].forEach(el => {
    el.disabled = v;
    el.style.opacity = v ? '0.4' : '1';
  });
}

function esc(s) {
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

boot();