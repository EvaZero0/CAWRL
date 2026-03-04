// ── State ──────────────────────────────────────────────────────────────────
let robotsActive = true;
let unlimitedActive = false;
let pagesCount = 0;
let brokenCount = 0;
let loadTimes = [];
let eventSource = null;


// ── Toggles ────────────────────────────────────────────────────────────────
function toggleOption(name) {
    if (name === 'robots') {
        robotsActive = !robotsActive;
        document.getElementById('toggle-robots').classList.toggle('active', robotsActive);
    }
    if (name === 'unlimited') {
        unlimitedActive = !unlimitedActive;
        const btn = document.getElementById('toggle-unlimited');
        const wrap = document.getElementById('wrap-max-pages');
        const warning = document.getElementById('unlimited-warning');
        const label = document.getElementById('label-unlimited');
        btn.classList.toggle('active', unlimitedActive);
        btn.classList.toggle('warn-toggle', unlimitedActive);
        wrap.classList.toggle('disabled', unlimitedActive);        // Grey out max pages input
        warning.classList.toggle('visible', unlimitedActive);      // Show warning
        label.classList.toggle('warn', unlimitedActive);
    }
}


// ── Status indicator ───────────────────────────────────────────────────────
function setStatus(state, text) {
    const dot = document.getElementById('status-dot');
    const lbl = document.getElementById('status-label');
    dot.className = 'status-dot ' + state;
    lbl.textContent = text;
    lbl.style.color = state === 'running' ? 'var(--accent)'
        : state === 'error' ? 'var(--accent2)'
            : 'var(--muted)';
}


// ── Log helpers ────────────────────────────────────────────────────────────
function appendLog(type, icon, url, meta = '') {
    const log = document.getElementById('log');
    const empty = log.querySelector('.empty-state');
    if (empty) empty.remove();

    const entry = document.createElement('div');
    entry.className = `log-entry ${type}`;
    entry.innerHTML = `
        <span class="log-icon">${icon}</span>
        <span class="log-url" title="${url}">${url}</span>
        <span class="log-meta">${meta}</span>`;
    log.appendChild(entry);
    log.scrollTop = log.scrollHeight;                              // Auto-scroll to bottom

    document.getElementById('log-badge').textContent =
        log.querySelectorAll('.log-entry').length;
}

function updateLastLogMeta(text, color) {
    const entries = document.querySelectorAll('.log-entry');
    if (!entries.length) return;
    const meta = entries[entries.length - 1].querySelector('.log-meta');
    if (meta) { meta.textContent = text; meta.style.color = color; }
}


// ── Broken links ───────────────────────────────────────────────────────────
function addBrokenLink(url, status) {
    const list = document.getElementById('broken-list');
    const empty = list.querySelector('.empty-state');
    if (empty) empty.remove();

    const cls = status === 0 ? 'status-0' : 'status-4xx';
    const label = status === 0 ? 'Timeout / Error' : status;

    const item = document.createElement('div');
    item.className = 'broken-item';
    item.innerHTML = `
        <div class="broken-url">${url}</div>
        <div class="broken-meta">
            <span class="status-pill ${cls}">${label}</span>
        </div>`;
    list.appendChild(item);

    brokenCount++;
    document.getElementById('stat-broken').textContent = brokenCount;
    document.getElementById('broken-badge').textContent = brokenCount;
    document.getElementById('card-broken').classList.add('has-broken');
}


// ── Average load time ──────────────────────────────────────────────────────
function updateAvgTime() {
    if (!loadTimes.length) return;
    const avg = (loadTimes.reduce((a, b) => a + b, 0) / loadTimes.length).toFixed(2);
    document.getElementById('stat-time').textContent = avg + 's';
}


// ── Reset UI ───────────────────────────────────────────────────────────────
function resetUI() {
    pagesCount = 0; brokenCount = 0; loadTimes = [];

    document.getElementById('btn-stop').disabled = true;
    document.getElementById('stat-pages').textContent = '0';
    document.getElementById('stat-broken').textContent = '0';
    document.getElementById('stat-time').textContent = '–';
    document.getElementById('stat-queue').textContent = '–';
    document.getElementById('log').innerHTML = '';
    document.getElementById('broken-list').innerHTML =
        '<div class="empty-state"><span class="icon">✅</span>No broken links found</div>';
    document.getElementById('broken-badge').textContent = '0';
    document.getElementById('robots-info').textContent = '';
    document.getElementById('card-broken').classList.remove('has-broken');
    document.getElementById('btn-start').disabled = true;
    document.getElementById('btn-export').disabled = true;
}


// ── Start crawl ────────────────────────────────────────────────────────────
async function startCrawl() {
    const urlVal = document.getElementById('url-input').value.trim();
    if (!urlVal) { alert('Please enter a URL.'); return; }

    resetUI();

    const progress = document.getElementById('progress-bar');
    progress.className = 'progress-bar indeterminate';

    setStatus('running', 'Connecting…');

    const payload = {
        url: urlVal,
        respect_robots: robotsActive,
        max_pages: unlimitedActive ? 0 : parseInt(document.getElementById('max-pages').value),
        crawl_delay: parseFloat(document.getElementById('crawl-delay').value),
    };

    const resp = await fetch('/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
    });

    const data = await resp.json();

    if (!resp.ok) {
        setStatus('error', 'Error: ' + (data.error || 'Unknown'));
        document.getElementById('btn-start').disabled = false;
        progress.className = 'progress-bar';
        return;
    }

    // Show robots.txt info
    const ri = data.robots;
    const riEl = document.getElementById('robots-info');
    riEl.innerHTML = ri.found
        ? `robots.txt: <span class="ok">${ri.disallow_count} disallow rule(s)</span>`
        : `robots.txt: <span class="warn">not found</span>`;

    setStatus('running', 'Crawling ' + ri.base_url);
    appendLog('info', '🚀', 'Crawl started: ' + ri.base_url);
    document.getElementById('btn-stop').disabled = false;

    // Connect to SSE stream
    if (eventSource) eventSource.close();
    eventSource = new EventSource('/stream');

    eventSource.onmessage = (e) => {
        const ev = JSON.parse(e.data);

        if (ev.type === 'crawling') {
            document.getElementById('stat-queue').textContent = ev.count;
            appendLog('ok', '→', ev.url);
        }
        else if (ev.type === 'page_done') {
            pagesCount++;
            document.getElementById('stat-pages').textContent = pagesCount;
            loadTimes.push(ev.load_time);
            updateAvgTime();
            updateLastLogMeta(`${ev.status} · ${ev.load_time}s`, 'var(--accent3)');
        }
        else if (ev.type === 'broken') {
            addBrokenLink(ev.url, ev.status);
            updateLastLogMeta(ev.status || 'Error', 'var(--accent2)');
            const entries = document.querySelectorAll('.log-entry');
            if (entries.length) entries[entries.length - 1].classList.add('broken');
        }
        else if (ev.type === 'skip') {
            appendLog('skip', '⊘', ev.url, 'robots.txt');
        }
        else if (ev.type === 'done') {
            progress.className = 'progress-bar';
            progress.style.width = '100%';
            setTimeout(() => { progress.style.width = '0'; }, 1500);

            setStatus('done', `Done – ${ev.total_pages} page(s)`);
            appendLog('info', '✓',
                `Crawl complete — ${ev.total_pages} pages · ${ev.broken_count} broken · avg ${ev.avg_load_time}s`);

            document.getElementById('btn-start').disabled = false;
            document.getElementById('btn-export').disabled = false;
            document.getElementById('btn-stop').disabled = true;   // ← neu
            document.getElementById('stat-queue').textContent = '–';
            eventSource.close();
        }
    };

    eventSource.onerror = () => {
        setStatus('error', 'Connection lost');
        document.getElementById('btn-start').disabled = false;
        progress.className = 'progress-bar';
    };
}


// ── Export JSON ────────────────────────────────────────────────────────────
async function exportJSON() {
    const resp = await fetch('/export');
    const data = await resp.json();
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = 'crawl_result.json'; a.click();
    URL.revokeObjectURL(url);
}


// ── Enter key support ──────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('url-input').addEventListener('keydown', e => {
        if (e.key === 'Enter') startCrawl();
    });
});


// ── Stop crawl ─────────────────────────────────────────────────────────
async function stopCrawl() {
    await fetch('/stop', { method: 'POST' });
    document.getElementById('btn-stop').disabled = true;
}