<?php

namespace App\Http\Controllers;

use Illuminate\View\View;

class SpreadsController extends Controller
{
    /**
     * Экран 1 — таблица текущих спредов.
     */
    public function index(): View
    {
        return view('spreads.index', [
            'apiUrl' => config('services.priceradar.public_url', 'http://localhost:8010/api/v1'),
        ]);
    }

    /**
     * Экран 2 — график истории.
     */
    public function history(): View
    {
        return view('spreads.history', [
            'apiUrl' => config('services.priceradar.public_url', 'http://localhost:8010/api/v1'),
        ]);
    }
}