(() => {
    const API = window.PRICERADAR_API_URL || 'http://localhost:8010/api/v1';

    const els = {
        tbody:   document.getElementById('fees-body'),
        summary: document.getElementById('fees-summary'),
        form:    document.getElementById('fee-form'),
        exchange:document.getElementById('fee-exchange'),
        value:   document.getElementById('fee-value'),
        status:  document.getElementById('fee-form-status'),
        refresh: document.getElementById('refresh-btn'),
        connDot: document.querySelector('#conn-status .conn-dot'),
        connText:document.querySelector('#conn-status .conn-text'),
    };

    function fmtDate(iso) {
        if (!iso) return '—';
        return new Date(iso).toLocaleString('ru-RU');
    }

    function setConn(s) {
        els.connDot.className = 'conn-dot conn-dot--' + s;
        els.connText.textContent = s === 'ok' ? 'live' : s === 'wait' ? 'загрузка…' : 'ошибка';
    }

    async function load() {
        setConn('wait');
        try {
            const res = await fetch(`${API}/fees`, { headers: { 'Accept': 'application/json' } });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const data = await res.json();
            render(data.fees ?? []);
            setConn('ok');
        } catch (e) {
            console.error(e);
            setConn('err');
            els.tbody.innerHTML = '<tr><td colspan="5" class="empty">Ошибка загрузки</td></tr>';
        }
    }

    function render(fees) {
        if (!fees.length) {
            els.tbody.innerHTML = '<tr><td colspan="5" class="empty">Нет данных</td></tr>';
            return;
        }
        els.tbody.innerHTML = fees.map(f => `
            <tr>
                <td><b>${f.exchange}</b></td>
                <td class="num">${(f.taker_fee * 100).toFixed(4)}</td>
                <td class="num">${f.source}</td>
                <td>${fmtDate(f.effective_from)}</td>
                <td>${fmtDate(f.effective_to)}</td>
            </tr>
        `).join('');

        const total = fees.reduce((s, f) => s + f.taker_fee, 0);
        els.summary.innerHTML =
            `Бирж: <b>${fees.length}</b> · ` +
            `Сумма taker fee: <b>${(total * 100).toFixed(4)}%</b> · ` +
            `Обновлено: ${new Date().toLocaleTimeString('ru-RU')}`;
    }

    els.form.addEventListener('submit', async (e) => {
        e.preventDefault();
        els.status.textContent = 'отправка…';
        els.status.className = '';

        try {
            const res = await fetch(`${API}/fees`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                },
                body: JSON.stringify({
                    exchange: els.exchange.value,
                    taker_fee: parseFloat(els.value.value),
                    source: 'manual',
                }),
            });
            if (!res.ok) {
                const text = await res.text();
                throw new Error(`HTTP ${res.status}: ${text.slice(0, 200)}`);
            }
            els.status.textContent = 'Обновлено. Новая версия создана.';
            els.status.className = 'ok';
            load();
        } catch (e) {
            console.error(e);
            els.status.textContent = 'Ошибка: ' + e.message;
            els.status.className = 'err';
        }
    });

    els.refresh.addEventListener('click', load);
    load();
})();