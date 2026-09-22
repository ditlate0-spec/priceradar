(() => {
    const API = window.PRICERADAR_API_URL || 'http://localhost:8010/api/v1';

    const PAIRS = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT', 'XRP/USDT',
                   'DOGE/USDT', 'ADA/USDT', 'AVAX/USDT', 'LINK/USDT'];
    const EXCHANGE_PAIRS = ['binance-bybit', 'binance-okx', 'bybit-okx'];

    const els = {
        pair:        document.getElementById('pair-select'),
        exchanges:   document.getElementById('exchanges-select'),
        direction:   document.getElementById('direction-select'),
        days:        document.getElementById('days-select'),
        metric:      document.getElementById('metric-select'),
        refresh:     document.getElementById('refresh-btn'),
        summary:     document.getElementById('heatmap-summary'),
        grid:        document.getElementById('heatmap-grid'),
        legend:      document.getElementById('legend-scale'),
        connDot:     document.querySelector('#conn-status .conn-dot'),
        connText:    document.querySelector('#conn-status .conn-text'),
    };

    // ---- Селекты ----
    PAIRS.forEach(p => els.pair.add(new Option(p, p)));
    EXCHANGE_PAIRS.forEach(e => els.exchanges.add(new Option(e, e)));
    updateDirections();

    function updateDirections() {
        const [a, b] = els.exchanges.value.split('-');
        els.direction.innerHTML = '';
        els.direction.add(new Option(`${a}→${b}`, `${a}-${b}`));
        els.direction.add(new Option(`${b}→${a}`, `${b}-${a}`));
    }

    els.exchanges.addEventListener('change', updateDirections);

    // ---- Цвет по значению (0..1 → светло-жёлтый ... тёмно-красный) ----
    function colorFor(value, min, max) {
        if (value === null || value === undefined) return 'transparent';
        if (max <= min) return 'rgba(74,158,255,0.15)';
        const t = Math.max(0, Math.min(1, (value - min) / (max - min)));
        // Интерполяция: жёлтый (255,214,0) → оранжевый (255,149,0) → красный (211,57,57) → тёмно-красный (139,0,0)
        let r, g, b;
        if (t < 0.33) {
            const k = t / 0.33;
            r = 255; g = Math.round(214 + (149 - 214) * k); b = 0;
        } else if (t < 0.66) {
            const k = (t - 0.33) / 0.33;
            r = Math.round(255 + (211 - 255) * k);
            g = Math.round(149 + (57 - 149) * k);
            b = Math.round(0 + (57 - 0) * k);
        } else {
            const k = (t - 0.66) / 0.34;
            r = Math.round(211 + (139 - 211) * k);
            g = Math.round(57 + (0 - 57) * k);
            b = Math.round(57 + (0 - 57) * k);
        }
        return `rgba(${r},${g},${b},0.75)`;
    }

    // ---- Отрисовка ----
    function renderGrid(cells, metric) {
        // Вычисляем min/max по метрике
        let values = cells
            .map(c => metric === 'pct_above_03' ? c.pct_above_03 : c.avg_spread_abs)
            .filter(v => v !== null && v !== undefined);
        const min = values.length ? Math.min(...values) : 0;
        const max = values.length ? Math.max(...values) : 1;

        els.grid.innerHTML = cells.map(c => {
            const v = metric === 'pct_above_03' ? c.pct_above_03 : c.avg_spread_abs;
            const noData = c.no_data || v === null || v === undefined;
            const bg = noData ? 'transparent' : colorFor(v, min, max);
            const display = noData ? '—' : (
                metric === 'pct_above_03'
                    ? `${Number(v).toFixed(2)}%`
                    : `${Number(v).toFixed(4)}%`
            );
            const totalMin = Math.round((c.total_seconds ?? 0) / 60);
            const tooltip = noData
                ? `Час ${c.hour}:00 — нет данных`
                : `Час ${c.hour}:00 UTC\n` +
                  `% времени ≥ 0.3%: ${c.pct_above_03 ?? '—'}%\n` +
                  `% ≥ 0.5%: ${c.pct_above_05 ?? '—'}%\n` +
                  `% ≥ 1.0%: ${c.pct_above_10 ?? '—'}%\n` +
                  `% ≥ 2.0%: ${c.pct_above_20 ?? '—'}%\n` +
                  `avg |net|: ${c.avg_spread_abs ?? '—'}%\n` +
                  `max |net|: ${c.max_abs ?? '—'}%\n` +
                  `данных: ${totalMin} мин`;

            return `
                <div class="heatmap-cell ${noData ? 'heatmap-cell--empty' : ''}"
                     style="background:${bg};"
                     title="${tooltip.replace(/"/g, '&quot;')}">
                    <div class="heatmap-hour">${String(c.hour).padStart(2, '0')}</div>
                    <div class="heatmap-value">${display}</div>
                </div>`;
        }).join('');

        // Легенда
        const steps = 8;
        els.legend.innerHTML = Array.from({ length: steps }, (_, i) => {
            const t = i / (steps - 1);
            const color = colorFor(t, 0, 1);
            const label = (min + (max - min) * t).toFixed(metric === 'pct_above_03' ? 2 : 4);
            return `<div class="legend-step" style="background:${color};" title="${label}"></div>`;
        }).join('');
    }

function renderSummary(payload) {
    const cells = payload.cells ?? [];
    const withData = cells.filter(c => !c.no_data).length;
    const totalMin = Math.round(
        cells.reduce((s, c) => s + (c.total_seconds ?? 0), 0) / 60
    );

    const expectedMinPerDay = 24 * 60;  // минут в сутках
    const expectedMin = payload.days * expectedMinPerDay;
    const coveragePct = expectedMin > 0 ? (totalMin / expectedMin * 100).toFixed(1) : 0;

    els.summary.innerHTML =
        `Пара: <b>${payload.row_id.split('|')[0]}</b> · ` +
        `период: <b>${payload.days}</b> дн. · ` +
        `часов с данными: <b>${withData}</b> / 24 · ` +
        `всего данных: <b>${totalMin}</b> мин ` +
        `(<b>${coveragePct}%</b> от ${expectedMin} мин)`;
}

    function setConn(s) {
        els.connDot.className = 'conn-dot conn-dot--' + s;
        els.connText.textContent = s === 'ok' ? 'live' : s === 'wait' ? 'загрузка…' : 'ошибка';
    }

    // ---- Fetch ----
    async function load() {
        setConn('wait');
        const params = new URLSearchParams({
            pair: els.pair.value,
            exchange_pair: els.exchanges.value,
            direction: els.direction.value,
            days: els.days.value,
            metric: els.metric.value,
            tz: 'utc',
        });

        try {
            const res = await fetch(`${API}/heatmap?${params}`, {
                headers: { 'Accept': 'application/json' },
            });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const data = await res.json();
            renderGrid(data.cells ?? [], els.metric.value);
            renderSummary(data);
            setConn('ok');
        } catch (e) {
            console.error('heatmap fetch error', e);
            setConn('err');
            els.summary.innerHTML = `<span style="color:#d33939;">Ошибка: ${e.message}</span>`;
        }
    }

    // ---- Events ----
    ['pair','exchanges','direction','days','metric'].forEach(k => {
        els[k].addEventListener('change', load);
    });
    els.refresh.addEventListener('click', load);

    load();
})();