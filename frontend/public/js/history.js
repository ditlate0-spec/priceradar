(() => {
    const API = window.PRICERADAR_API_URL || 'http://localhost:8010/api/v1';

    // ---- Кастомный плагин: горизонтальные линии порогов ----
    const thresholdLinesPlugin = {
        id: 'thresholdLines',
        afterDatasetsDraw(chart) {
            const { ctx, chartArea, scales } = chart;
            if (!chartArea) return;

            const thresholds = [
                { value: 0.3, color: 'rgba(211,177,57,0.8)',  label: '0.3%' },
                { value: 0.5, color: 'rgba(211,138,57,0.8)',  label: '0.5%' },
                { value: 1.0, color: 'rgba(211,57,57,0.8)',   label: '1.0%' },
                { value: 1.5, color: 'rgba(211,57,57,0.55)',  label: '1.5%' },
                { value: 2.0, color: 'rgba(139,0,0,0.75)',    label: '2.0%' },
            ];

            ctx.save();
            ctx.setLineDash([6, 4]);
            ctx.lineWidth = 1;
            ctx.font = '11px sans-serif';

            for (const t of thresholds) {
                // Только если значение в пределах видимой оси Y
                const yPos = scales.y.getPixelForValue(t.value);
                const yNeg = scales.y.getPixelForValue(-t.value);
                // Проверяем, что точки внутри графика
                if (yPos >= chartArea.top && yPos <= chartArea.bottom) {
                    drawLine(ctx, chartArea, yPos, t.color, t.label);
                }
                if (yNeg >= chartArea.top && yNeg <= chartArea.bottom) {
                    drawLine(ctx, chartArea, yNeg, t.color, t.label);
                }
            }
            ctx.restore();
        },
    };

    function drawLine(ctx, chartArea, y, color, label) {
        ctx.strokeStyle = color;
        ctx.beginPath();
        ctx.moveTo(chartArea.left, y);
        ctx.lineTo(chartArea.right, y);
        ctx.stroke();

        // Подпись слева
        ctx.fillStyle = color;
        ctx.fillText(label, chartArea.left + 4, y - 3);
    }

    const PAIRS = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT', 'XRP/USDT',
                   'DOGE/USDT', 'ADA/USDT', 'AVAX/USDT', 'LINK/USDT'];
    const EXCHANGE_PAIRS = ['binance-bybit', 'binance-okx', 'bybit-okx'];

    const els = {
        pair:        document.getElementById('pair-select'),
        exchanges:   document.getElementById('exchanges-select'),
        direction:   document.getElementById('direction-select'),
        period:      document.getElementById('period-select'),
        interval:    document.getElementById('interval-select'),
        metric:      document.getElementById('metric-select'),
        refresh:     document.getElementById('refresh-btn'),
        summary:     document.getElementById('history-summary'),
        canvas:      document.getElementById('history-chart'),
        connDot:     document.querySelector('#conn-status .conn-dot'),
        connText:    document.querySelector('#conn-status .conn-text'),
    };

    // ---- Инициализация селектов ----
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

    // ---- Chart.js ----
    let chart = null;

    function buildChart(points) {
        const labels = points.map(p => new Date(p.ts).toLocaleString('ru-RU', {
            month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit'
        }));
        const dataLast = points.map(p => p.last);
        const dataMax  = points.map(p => p.max);
        const dataMin  = points.map(p => p.min);

        if (chart) {
            chart.data.labels = labels;
            chart.data.datasets[0].data = dataLast;
            chart.data.datasets[1].data = dataMax;
            chart.data.datasets[2].data = dataMin;
            chart.update('none');
            return;
        }

        const ctx = els.canvas.getContext('2d');
        chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels,
                datasets: [
                    {
                        label: 'Last',
                        data: dataLast,
                        borderColor: '#4a9eff',
                        backgroundColor: 'rgba(74,158,255,0.15)',
                        borderWidth: 2,
                        pointRadius: 0,
                        tension: 0.15,
                    },
                    {
                        label: 'Max',
                        data: dataMax,
                        borderColor: 'rgba(211,57,57,0.7)',
                        borderWidth: 1,
                        pointRadius: 0,
                        borderDash: [4, 4],
                        tension: 0.15,
                    },
                    {
                        label: 'Min',
                        data: dataMin,
                        borderColor: 'rgba(57,211,83,0.7)',
                        borderWidth: 1,
                        pointRadius: 0,
                        borderDash: [4, 4],
                        tension: 0.15,
                    },
                ],
            },
                options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: false,
                interaction: { mode: 'index', intersect: false },
                plugins: {
                    legend: { labels: { color: '#e6e8ee' } },
                    tooltip: {
                        backgroundColor: '#1b1e28',
                        borderColor: '#262a36',
                        borderWidth: 1,
                        titleColor: '#e6e8ee',
                        bodyColor: '#e6e8ee',
                    },
                    // ---- Линии порогов ----
                    annotation: undefined,   // зарезервировано, если будем ставить плагин
                },
                scales: {
                    x: {
                        ticks: { color: '#9aa0ae', maxRotation: 0, autoSkip: true },
                        grid: { color: '#262a36' },
                    },
                    y: {
                        ticks: { color: '#9aa0ae', callback: v => v.toFixed(3) + '%' },
                        grid: { color: '#262a36' },
                    },
                },
            },
            plugins: [thresholdLinesPlugin],
        });
    }

    // ---- Summary ----
    function renderSummary(data) {
        const s = data.summary;
        if (!s) {
            els.summary.innerHTML = 'Нет данных за период';
            return;
        }
        els.summary.innerHTML =
            `Период: <b>${data.from.slice(0, 16)}</b> — <b>${data.to.slice(0, 16)}</b> · ` +
            `точек: <b>${data.points.length}</b> · ` +
            `avg|net|: <b>${s.spread_avg_abs?.toFixed(4) ?? '—'}%</b> · ` +
            `max|net|: <b>${s.spread_max_abs?.toFixed(4) ?? '—'}%</b> · ` +
            `% ≥ 0.3%: <b>${s.pct_above_03}%</b> · ` +
            `≥ 0.5%: <b>${s.pct_above_05}%</b> · ` +
            `≥ 1%: <b>${s.pct_above_10}%</b> · ` +
            `≥ 2%: <b>${s.pct_above_20}%</b>`;
    }

    // ---- Fetch ----
  function periodToRange(period) {
    const now = new Date();
    const from = new Date(now);
    switch (period) {
        case '1h':  from.setHours(now.getHours() - 1); break;
        case '24h': from.setHours(now.getHours() - 24); break;
        case '7d':  from.setDate(now.getDate() - 7); break;
        case '30d': from.setDate(now.getDate() - 30); break;
        case 'all':
            // Достаточно далеко в прошлом — API сам вернёт всё, что есть в БД.
            // Но не дальше 90 дней — иначе бэкенд отдаст 400.
            from.setDate(now.getDate() - 90);
            break;
    }
    return { from: from.toISOString(), to: now.toISOString() };
}

    async function load() {
        setConn('wait');
        const params = new URLSearchParams({
            pair: els.pair.value,
            exchange_pair: els.exchanges.value,
            direction: els.direction.value,
            interval: els.interval.value,
            metric: els.metric.value,
            ...periodToRange(els.period.value),
        });

        try {
            const res = await fetch(`${API}/spreads/history?${params}`, {
                headers: { 'Accept': 'application/json' },
            });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const data = await res.json();
            buildChart(data.points ?? []);
            renderSummary(data);
            setConn('ok');
        } catch (e) {
            console.error('history fetch error', e);
            setConn('err');
            els.summary.innerHTML = `<span style="color:#d33939;">Ошибка загрузки: ${e.message}</span>`;
        }
    }

    function setConn(s) {
        els.connDot.className = 'conn-dot conn-dot--' + s;
        els.connText.textContent = s === 'ok' ? 'live' : s === 'wait' ? 'загрузка…' : 'ошибка';
    }

    // ---- Events ----
        // ---- Экспорт ----
    function buildExportUrl(format) {
        const params = new URLSearchParams({
            pair: els.pair.value,
            exchange_pair: els.exchanges.value,
            direction: els.direction.value,
            metric: els.metric.value,
            format,
            ...periodToRange(els.period.value),
        });
        return `${API}/export?${params}`;
    }

    document.getElementById('export-csv-btn').addEventListener('click', () => {
        window.location.href = buildExportUrl('csv');
    });
    document.getElementById('export-json-btn').addEventListener('click', () => {
        window.location.href = buildExportUrl('json');
    });

    // ---- Events ----
    ['pair','exchanges','direction','period','interval','metric'].forEach(k => {
        els[k].addEventListener('change', load);
    });
    els.refresh.addEventListener('click', load);

    load();
})();