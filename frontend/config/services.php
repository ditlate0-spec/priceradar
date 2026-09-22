<?php

return [

    /*
    |--------------------------------------------------------------------------
    | PriceRadar backend API
    |--------------------------------------------------------------------------
    |
    | URL FastAPI-бекенда. В браузере используется публичный URL
    | (localhost:8010), внутри Docker — внутренний (backend:8000).
    */

    'priceradar' => [
        'public_url' => env('PRICERADAR_API_URL_PUBLIC', 'http://localhost:8010/api/v1'),
        'internal_url' => env('PRICERADAR_API_URL', 'http://backend:8000/api/v1'),
    ],

];