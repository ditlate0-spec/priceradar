(() => {
    const API = window.PRICERADAR_API_URL || 'http://localhost:8010/api/v1';
    const PAGE_SIZE = 50;

    const els = {
        pair:        document.getElementById('pair-select'),
        exchanges:   document.getElementById('exchanges-select'),
        direction:   document.getElementById('direction-select'),
        threshold:   document.getElementById('threshold-select'),
        period:      document.getElementById('period-select'),
        refresh:     document.getElementById('refresh-btn'),
        summary:     document.getElementById('peaks-summary'),
        tbody:       document.getElementById('peaks-body'),
        pageInfo:    document.getElementById('pagination-info'),
        prev:        document.getElementById('prev-btn'),
        next:        document.getElementById('next-btn'),
        connDot:     document.querySelector('#conn-status .conn-dot'),
        connText:    document.querySelector('#conn-status .conn-text'),
    };

    let state = { offset: 0, total: 0, rows: [] };

    // ---------- API ----------
    function periodToRange(period) {
        const now = new Date();
        const from = new Date(now);
        switch (period) {
            case '1h':  from.setHours(now.getHours() - 1); break;
            case '24h': from.setHours(now.getHours() - 24); break;
            case '7d':  from.setDate(now.getDate() - 7); break;
            case '30d': from.setDate(now.getDate() - 30); break;
        }
        return { from: from.toISOString(), to: now.toISOString() };
    }

    async function fetchPeaks() {
        const params = new URLSearchParams({
            limit: PAGE_SIZE,
            offset: state.offset,
            ...periodToRange(els.period.value),
        });
        if (els.pair.value)      params.set('pair', els.pair.value);
        if (els.exchanges.value) params.set('exchange_pair', els.exchanges.value);
        if (els.direction.value) params.set('direction', els.direction.value);
        if (els.threshold.value) params.set('threshold', els.threshold.value);

        setConn('wait');
        const res = await fetch(`${API}/peaks?${params}`, {
            headers: { 'Accept': 'application/json' },
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return await res.json();
    }

    // ---------- Helpers ----------
    function fmt(v, digits = 4) {
        if (v === null || v === undefined) return '—';
        return Number(v).toFixed(digits);
    }

    function fmtTime(iso) {
        if (!iso) return '—';
        const d = new Date(iso);
        return d.toLocaleString('ru-RU', {
            month: '2-digit', day: '2-digit',
            hour: '2-digit', minute: '2-digit', second: '2-digit',
        });
    }

    function parseRowId(rowId) {
        // {pair}|{ex_a}-{ex_b}|{ex_a}→{ex_b}
        const parts = rowId.split('|');
        return {
            pair: parts[0] || '—',
            exchangePair: parts[1] || '—',
            direction: parts[2] || '—',
        };
    }

    // ---------- Rendering ----------
    function renderRows(rows) {
       if (!rows.length) {
    const hasFilters = els.exchanges.value || els.direction.value || els.pair.value || els.threshold.value;
    const hint = hasFilters
        ? 'По выбранным фильтрам пиков не найдено. Попробуйте расширить период или выбрать другое направление.'
        : 'Пиков за выбранный период нет.';
    els.tbody.innerHTML = `<tr><td colspan="10" class="empty">${hint}</td></tr>`;
    return;
}

        els.tbody.innerHTML = rows.map(p => {
            const info = parseRowId(p.row_id);
            const isOpen = p.time_end === null;
            const statusClass = isOpen ? 'stale-stale' : 'stale-ok';
            const statusText = isOpen ? 'открыт' : 'закрыт';

            return `
                <tr>
                    <td>${fmtTime(p.time_start)}</td>
                    <td>${info.pair}</td>
                    <td>${info.exchangePair.replace('-', ' ↔ ')}</td>
                    <td>${info.direction}</td>
                    <td class="num">${fmt(p.threshold, 2)}</td>
                    <td class="num">${p.duration_seconds ?? '—'}</td>
                    <td class="num">${p.duration_data_seconds ?? 0}</td>
                    <td class="num">${fmt(p.spread_max_abs)}</td>
                    <td class="num">${fmt(p.spread_avg_abs)}</td>
                    <td class="num ${statusClass}">${statusText}</td>
                </tr>`;
        }).join('');
    }

    function renderSummary(payload) {
        const total = payload.total ?? 0;
        const shown = payload.peaks?.length ?? 0;
        const from = payload.from?.slice(0, 16) ?? '';
        const to = payload.to?.slice(0, 16) ?? '';
      if (total === 0) {
    els.summary.innerHTML =
        `Период: <b>${from}</b> — <b>${to}</b> · пиков не найдено`;
    return;
}
    els.summary.innerHTML =
    `Период: <b>${from}</b> — <b>${to}</b> · ` +
    `всего пиков: <b>${total}</b> · ` +
    `показано: <b>${shown}</b>`;
    }

    function renderPagination(payload) {
        const total = payload.total ?? 0;
        const offset = payload.offset ?? 0;
        const limit = payload.limit ?? PAGE_SIZE;
        const shownFrom = total === 0 ? 0 : offset + 1;
        const shownTo = Math.min(offset + limit, total);

        els.pageInfo.textContent = `${shownFrom}–${shownTo} из ${total}`;
        els.prev.disabled = offset <= 0;
        els.next.disabled = offset + limit >= total;
    }

    function setConn(s) {
        els.connDot.className = 'conn-dot conn-dot--' + s;
        els.connText.textContent = s === 'ok' ? 'live' : s === 'wait' ? 'загрузка…' : 'ошибка';
    }

    // ---------- Load ----------
    async function load() {
        try {
            const payload = await fetchPeaks();
            state.rows = payload.peaks ?? [];
            state.total = payload.total ?? 0;
            renderRows(state.rows);
            renderSummary(payload);
            renderPagination(payload);
            setConn('ok');
        } catch (e) {
            console.error('peaks fetch error', e);
            setConn('err');
            els.summary.innerHTML = `<span style="color:#d33939;">Ошибка загрузки: ${e.message}</span>`;
            els.tbody.innerHTML = '<tr><td colspan="10" class="empty">Ошибка загрузки</td></tr>';
        }
    }

    // ---------- Events ----------
    ['pair','exchanges','direction','threshold','period'].forEach(k => {
        els[k].addEventListener('change', () => {
            state.offset = 0;      // сброс страницы при смене фильтра
            load();
        });
    });

    els.refresh.addEventListener('click', () => {
        state.offset = 0;
        load();
    });

    els.prev.addEventListener('click', () => {
        state.offset = Math.max(0, state.offset - PAGE_SIZE);
        load();
    });

    els.next.addEventListener('click', () => {
        state.offset += PAGE_SIZE;
        load();
    });

    load();
})();