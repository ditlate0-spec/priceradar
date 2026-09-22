<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>@yield('title', 'PriceRadar')</title>
    <link rel="stylesheet" href="{{ asset('css/spreads.css') }}">
</head>
<body>
       <header class="topbar">
        <div class="brand">
            <span class="brand-dot"></span>
            <strong>PriceRadar</strong>
            <span class="brand-sub">наблюдение за расхождениями цен</span>
        </div>

        <nav class="main-nav">
            <a href="{{ route('spreads.index') }}"
               class="nav-link {{ request()->routeIs('spreads.index') ? 'nav-link--active' : '' }}">
                Текущие
            </a>
            <a href="{{ route('spreads.history') }}"
               class="nav-link {{ request()->routeIs('spreads.history') ? 'nav-link--active' : '' }}">
                История
            </a>
            <a href="{{ route('peaks.index') }}"
               class="nav-link {{ request()->routeIs('peaks.*') ? 'nav-link--active' : '' }}">
                Пики
            </a>
            <a href="{{ route('heatmap.index') }}"
               class="nav-link {{ request()->routeIs('heatmap.*') ? 'nav-link--active' : '' }}">
                Тепловая карта
            </a>
            <a href="{{ route('fees.index') }}"
               class="nav-link {{ request()->routeIs('fees.*') ? 'nav-link--active' : '' }}">
                Комиссии
            </a>

        </nav>

        <div class="conn-status" id="conn-status">
            <span class="conn-dot conn-dot--wait"></span>
            <span class="conn-text">подключение…</span>
        </div>
    </header>
    <main class="container">
        @yield('content')
    </main>

    <script>
        // Прокидываем URL бэкенда в window, чтобы JS мог к нему обращаться.
        window.PRICERADAR_API_URL = @json($apiUrl ?? 'http://localhost:8010/api/v1');
    </script>
    @stack('scripts')
</body>
</html>