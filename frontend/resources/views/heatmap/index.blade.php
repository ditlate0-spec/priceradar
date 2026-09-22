@extends('layouts.app')

@section('title', 'Тепловая карта — PriceRadar')

@section('content')
<section class="panel">
    <div class="panel-head">
        <h1>Тепловая карта по часам (UTC)</h1>
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
            <select id="days-select">
                <option value="1">1 день</option>
                <option value="7" selected>7 дней</option>
                <option value="30">30 дней</option>
                <option value="90">90 дней</option>
            </select>
        </label>

        <label class="field">
            <span>Метрика</span>
            <select id="metric-select">
                <option value="pct_above_03" selected>% времени ≥ 0.3%</option>
                <option value="avg_spread">Средний |net|</option>
            </select>
        </label>
    </div>

    <div class="history-summary" id="heatmap-summary">
        <span>Загрузка…</span>
    </div>

    <div class="heatmap-wrap">
        <div class="heatmap-grid" id="heatmap-grid"></div>
    </div>

    <div class="heatmap-legend">
        <span class="legend-label">меньше</span>
        <div class="legend-scale" id="legend-scale"></div>
        <span class="legend-label">больше</span>
    </div>
</section>
@endsection

@push('scripts')
    <script src="{{ asset('js/heatmap.js') }}"></script>
@endpush