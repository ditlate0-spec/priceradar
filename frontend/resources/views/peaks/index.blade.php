@extends('layouts.app')

@section('title', 'Пики — PriceRadar')

@section('content')
<section class="panel">
    <div class="panel-head">
        <h1>Пики</h1>
        <div class="controls">
            <button id="refresh-btn" class="btn">Обновить</button>
        </div>
    </div>

    <div class="history-controls">
        <label class="field">
            <span>Пара</span>
            <select id="pair-select">
                <option value="">Все пары</option>
                <option value="BTC/USDT">BTC/USDT</option>
                <option value="ETH/USDT">ETH/USDT</option>
                <option value="SOL/USDT">SOL/USDT</option>
                <option value="BNB/USDT">BNB/USDT</option>
                <option value="XRP/USDT">XRP/USDT</option>
                <option value="DOGE/USDT">DOGE/USDT</option>
                <option value="ADA/USDT">ADA/USDT</option>
                <option value="AVAX/USDT">AVAX/USDT</option>
                <option value="LINK/USDT">LINK/USDT</option>
            </select>
        </label>

        <label class="field">
            <span>Пара бирж</span>
            <select id="exchanges-select">
                <option value="">Все</option>
                <option value="binance-bybit">binance ↔ bybit</option>
                <option value="binance-okx">binance ↔ okx</option>
                <option value="bybit-okx">bybit ↔ okx</option>
            </select>
        </label>

        <label class="field">
            <span>Направление</span>
            <select id="direction-select">
                <option value="">Все</option>
                <option value="binance-bybit">binance→bybit</option>
                <option value="bybit-binance">bybit→binance</option>
                <option value="binance-okx">binance→okx</option>
                <option value="okx-binance">okx→binance</option>
                <option value="bybit-okx">bybit→okx</option>
                <option value="okx-bybit">okx→bybit</option>
            </select>
        </label>

        <label class="field">
            <span>Порог</span>
            <select id="threshold-select">
                <option value="">Все</option>
                <option value="0.3">≥ 0.3%</option>
                <option value="0.5">≥ 0.5%</option>
                <option value="1.0">≥ 1.0%</option>
                <option value="2.0">≥ 2.0%</option>
            </select>
        </label>

        <label class="field">
            <span>Период</span>
            <select id="period-select">
                <option value="1h">1 час</option>
                <option value="24h" selected>24 часа</option>
                <option value="7d">7 дней</option>
                <option value="30d">30 дней</option>
            </select>
        </label>
    </div>

    <div class="history-summary" id="peaks-summary">
        <span>Загрузка…</span>
    </div>

    <div class="table-wrap">
        <table class="spreads-table" id="peaks-table">
            <thead>
                <tr>
                    <th>Начало (UTC)</th>
                    <th>Пара</th>
                    <th>Биржи</th>
                    <th>Направление</th>
                    <th class="num">Порог, %</th>
                    <th class="num">Длит., сек</th>
                    <th class="num">Данных, сек</th>
                    <th class="num">Max |net|, %</th>
                    <th class="num">Avg |net|, %</th>
                    <th class="num">Статус</th>
                </tr>
            </thead>
            <tbody id="peaks-body">
                <tr><td colspan="10" class="empty">Загрузка…</td></tr>
            </tbody>
        </table>
    </div>

    <div class="pagination-bar">
        <span id="pagination-info">—</span>
        <div class="pagination-controls">
            <button id="prev-btn" class="btn" disabled>← Назад</button>
            <button id="next-btn" class="btn" disabled>Вперёд →</button>
        </div>
    </div>
</section>
@endsection

@push('scripts')
    <script src="{{ asset('js/peaks.js') }}"></script>
@endpush