(() => {
    const API = window.PRICERADAR_API_URL || 'http://localhost:8010/api/v1';
    const REFRESH_MS = 5000;

    const els = {
        tbody: document.getElementById('spreads-body'),
        summary: document.getElementById('summary'),
        connDot: document.querySelector('#conn-status .conn-dot'),
        connText: document.querySelector('#conn-status .conn-text'),
        filterHighlight: document.getElementById('filter-highlight'),
        filterPositive: document.getElementById('filter-positive'),
        reloadBtn: document.getElementById('reload-btn'),
    };

    let state = {
        rows: [],
        sortBy: 'spread_net',
        sortDir: 'desc',
    };

    // ---------- API ----------
    async function fetchSpreads() {
        const url = `${API}/spreads/current`;
        const res = await fetch(url, { headers: { 'Accept': 'application/json' } });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return await res.json();
    }

    // ---------- Helpers ----------
    function fmt(v, digits = 4) {
        if (v === null || v === undefined) return '—';
        return (v >= 0 ? '+' : '') + Number(v).toFixed(digits);
    }

    function staleClass(level) {
        return level === 'ok' ? 'stale-ok' : level === 'stale' ? 'stale-stale' : 'stale-unavailable';
    }

    function levelToClass(level) {
        return `level-${level}`;
    }

    function directionArrow(dir) {
        // dir приходит как "binance→bybit" (со стрелкой из API)
        return dir;
    }

    // ---------- Rendering ----------
    function applyFilters(rows) {
        return rows.filter(r => {
            if (els.filterHighlight.checked && r.level === 'norm') return false;
            if (els.filterPositive.checked && r.spread_net <= 0) return false;
            return true;
        });
    }

    function applySort(rows) {
        const by = state.sortBy;
        const dir = state.sortDir === 'asc' ? 1 : -1;
        return [...rows].sort((a, b) => {
            let av, bv;
            switch (by) {
                case 'pair':       av = a.pair; bv = b.pair; break;
                case 'exchanges':  av = a.exchange_a + a.exchange_b; bv = b.exchange_a + b.exchange_b; break;
                case 'direction':  av = a.direction; bv = b.direction; break;
                case 'spread_net': av = Math.abs(a.spread_net); bv = Math.abs(b.spread_net); break;
                case 'spread_gross': av = a.spread_gross; bv = b.spread_gross; break;
                case 'fee':        av = a.fee_a + a.fee_b; bv = b.fee_a + b.fee_b; break;
                case 'level': {
    const order = { extreme: 5, strong: 4, significant: 3, notice: 2, norm: 1 };
    av = order[a.level] ?? 0;
    bv = order[b.level] ?? 0;
    break;
}
                case 'stale':      av = a.stale_a + a.stale_b; bv = b.stale_a + b.stale_b; break;
                default: return 0;
            }
            if (av < bv) return -1 * dir;
            if (av > bv) return 1 * dir;
            return 0;
        });
    }

    function render(rows) {
        const filtered = applyFilters(rows);
        const sorted = applySort(filtered);

        if (!sorted.length) {
            els.tbody.innerHTML = '<tr><td colspan="8" class="empty">Нет данных под фильтр</td></tr>';
            return;
        }

        const html = sorted.map(r => {
            const feeTotal = ((r.fee_a + r.fee_b) * 100).toFixed(3);
            return `
                <tr data-row-id="${r.row_id}">
                    <td>${r.pair}</td>
                    <td>${r.exchange_a} ↔ ${r.exchange_b}</td>
                    <td>${directionArrow(r.direction)}</td>
                    <td class="num cell-net ${levelToClass(r.level)}">${fmt(r.spread_net)}</td>
                    <td class="num">${fmt(r.spread_gross)}</td>
                    <td class="num">${feeTotal}</td>
                    <td class="num">${r.level}</td>
                    <td class="num ${staleClass(r.stale_a)}">${r.stale_a}/${r.stale_b}</td>
                </tr>`;
        }).join('');

        els.tbody.innerHTML = html;
    }

    function renderSummary(payload) {
        const total = payload.spreads?.length ?? 0;
        const positive = (payload.spreads ?? []).filter(r => r.spread_net > 0).length;
        const highlight = (payload.spreads ?? []).filter(r => r.level !== 'norm').length;
        const ts = payload.as_of ? new Date(payload.as_of).toLocaleTimeString() : '—';
        els.summary.innerHTML = `Всего: <b>${total}</b> · Положительных: <b>${positive}</b> · С подсветкой: <b>${highlight}</b> · Обновлено: ${ts}`;
    }

    // ---------- Status ----------
    function setConn(status) {
        els.connDot.className = 'conn-dot conn-dot--' + status;
        els.connText.textContent = status === 'ok' ? 'live' : status === 'wait' ? 'подключение…' : 'ошибка связи';
    }

    // ---------- Tick ----------
    async function tick() {
        try {
            setConn('wait');
            const payload = await fetchSpreads();
            state.rows = payload.spreads ?? [];
            render(state.rows);
            renderSummary(payload);
            setConn('ok');
        } catch (e) {
            console.error('fetch error', e);
            setConn('err');
        }
    }

    // ---------- Sorting events ----------
    document.querySelectorAll('.spreads-table th[data-sort]').forEach(th => {
        th.addEventListener('click', () => {
            const key = th.dataset.sort;
            if (state.sortBy === key) {
                state.sortDir = state.sortDir === 'asc' ? 'desc' : 'asc';
            } else {
                state.sortBy = key;
                state.sortDir = 'desc';
            }
            render(state.rows);
        });
    });

    els.filterHighlight.addEventListener('change', () => render(state.rows));
    els.filterPositive.addEventListener('change', () => render(state.rows));
    els.reloadBtn.addEventListener('click', tick);

    // ---------- Start ----------
    tick();
    setInterval(tick, REFRESH_MS);
})();