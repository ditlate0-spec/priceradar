<?php

namespace App\Http\Controllers;

use Illuminate\View\View;

class PeaksController extends Controller
{
    public function index(): View
    {
        return view('peaks.index', [
            'apiUrl' => config('services.priceradar.public_url', 'http://localhost:8010/api/v1'),
        ]);
    }
}