@extends('layouts.app')

@section('title', 'Комиссии — PriceRadar')

@section('content')
<section class="panel">
    <div class="panel-head">
        <h1>Комиссии бирж</h1>
        <div class="controls">
            <button id="refresh-btn" class="btn">Обновить</button>
        </div>
    </div>

    <div class="history-summary" id="fees-summary">
        <span>Загрузка…</span>
    </div>

    <div class="table-wrap">
        <table class="spreads-table" id="fees-table">
            <thead>
                <tr>
                    <th>Биржа</th>
                    <th class="num">Taker fee, %</th>
                    <th class="num">Источник</th>
                    <th>Действует с</th>
                    <th>Действует до</th>
                </tr>
            </thead>
            <tbody id="fees-body">
                <tr><td colspan="5" class="empty">Загрузка…</td></tr>
            </tbody>
        </table>
    </div>

    <div class="fees-form">
        <h2>Обновить комиссию</h2>
        <p class="fees-hint">
            Создаётся новая версия с <code>effective_from = сейчас</code>.
            Старая запись закрывается автоматически. Агрегаты и пики
            не пересчитываются — они сохраняют свою <code>fee_version</code>.
        </p>
        <form id="fee-form">
            <label class="field">
                <span>Биржа</span>
                <select id="fee-exchange">
                    <option value="binance">binance</option>
                    <option value="bybit">bybit</option>
                    <option value="okx">okx</option>
                </select>
            </label>
            <label class="field">
                <span>Taker fee (доля, 0.001 = 0.1%)</span>
                <input type="number" id="fee-value" step="0.0001" min="0" max="1" value="0.001" />
            </label>
            <button type="submit" class="btn">Обновить</button>
        </form>
        <div id="fee-form-status"></div>
    </div>
</section>
@endsection

@push('scripts')
    <script src="{{ asset('js/fees.js') }}"></script>
@endpush