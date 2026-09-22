@extends('layouts.app')

@section('title', 'История — PriceRadar')

@section('content')
<section class="panel">
    <div class="panel-head">
        <h1>История спреда</h1>
        <div class="controls">
            <button id="export-csv-btn" class="btn">Скачать CSV</button>
            <button id="export-json-btn" class="btn">Скачать JSON</button>
            <button id="refresh-btn" class="btn">Обновить</button>
        </div>
    </div>

    <div class="history-controls">
        <label class="field">
            <span>Пара</span>
            <select id="pair-select"></select>
        </label>

        <label class="field">
            <span>Пара бирж</span>
            <select id="exchanges-select"></select>
        </label>

        <label class="field">
            <span>Направление</span>
            <select id="direction-select"></select>
        </label>

        <label class="field">
            <span>Период</span>
<select id="period-select">
    <option value="1h">1 час</option>
    <option value="24h" selected>24 часа</option>
    <option value="7d">7 дней</option>
    <option value="30d">30 дней</option>
    <option value="all">Всё, что есть</option>
</select>
        </label>

        <label class="field">
            <span>Интервал</span>
            <select id="interval-select">
                <option value="1m">1 мин</option>
                <option value="5m" selected>5 мин</option>
                <option value="15m">15 мин</option>
                <option value="1h">1 час</option>
                <option value="1d">1 день</option>
            </select>
        </label>

        <label class="field">
            <span>Метрика</span>
            <select id="metric-select">
                <option value="net" selected>Net (с комиссиями)</option>
                <option value="gross">Gross (без комиссий)</option>
            </select>
        </label>
    </div>

    <div class="history-summary" id="history-summary">
        <span>Загрузка…</span>
    </div>

    <div class="chart-wrap">
        <canvas id="history-chart"></canvas>
    </div>

    <div class="chart-note">
        Пороги подсветки: <span class="dot dot--notice"></span> 0.3%
        · <span class="dot dot--significant"></span> 0.8%
        · <span class="dot dot--strong"></span> 1.5%
        · <span class="dot dot--extreme"></span> 2.0%
    </div>
</section>
@endsection

@push('scripts')
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <script src="{{ asset('js/history.js') }}"></script>
@endpush