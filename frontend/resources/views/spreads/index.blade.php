@extends('layouts.app')

@section('title', 'Текущие спреды — PriceRadar')

@section('content')
<section class="panel">
    <div class="panel-head">
        <h1>Текущие спреды</h1>
        <div class="controls">
            <label class="filter">
                <input type="checkbox" id="filter-highlight" />
                <span>только с подсветкой</span>
            </label>
            <label class="filter">
                <input type="checkbox" id="filter-positive" />
                <span>только положительные</span>
            </label>
            <button id="reload-btn" class="btn">Обновить сейчас</button>
        </div>
    </div>

    <div class="summary" id="summary">
        <span>Загрузка…</span>
    </div>

    <div class="table-wrap">
        <table class="spreads-table" id="spreads-table">
                     <thead>
                <tr>
                    <th data-sort="pair" title="Торговая пара (например BTC/USDT)">Пара</th>
                    <th data-sort="exchanges" title="Пара бирж, между которыми считается спред">Биржи</th>
                    <th data-sort="direction" title="Направление: A→B — купить на B, продать на A">Напр.</th>
                    <th data-sort="spread_net" class="num"
                        title="Net-спред: gross минус taker-комиссии обеих бирж. Основная метрика проекта. Формула: net = gross − fee_A − fee_B.">
                        Net, %
                    </th>
                    <th data-sort="spread_gross" class="num"
                        title="Gross-спред: разница между bid на одной бирже и ask на другой, без учёта комиссий. Формула: (bid_A − ask_B) / ask_B × 100%.">
                        Gross, %
                    </th>
                    <th data-sort="fee" class="num"
                        title="Сумма taker-комиссий двух бирж (по умолчанию 0.1% + 0.1% = 0.2%).">
                        Fee, %
                    </th>
                    <th data-sort="level" class="num"
                        title="Уровень подсветки по |net|: norm < 0.3% · notice ≥ 0.3% · significant ≥ 0.8% · strong ≥ 1.5% · extreme ≥ 2.0%.">
                        Уровень
                    </th>
                    <th data-sort="stale" class="num"
                        title="Свежесть данных по каждой бирже: ok < 5 сек · stale 5–30 сек · unavailable > 30 сек.">
                        Статус
                    </th>
                </tr>
            </thead>
            <tbody id="spreads-body">
                <tr><td colspan="8" class="empty">Загрузка данных…</td></tr>
            </tbody>
        </table>
    </div>
</section>
@endsection

@push('scripts')
    <script src="{{ asset('js/spreads.js') }}"></script>
@endpush