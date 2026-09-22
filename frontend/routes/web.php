<?php

use App\Http\Controllers\SpreadsController;
use App\Http\Controllers\PeaksController;
use App\Http\Controllers\HeatmapController;
use Illuminate\Support\Facades\Route;
use App\Http\Controllers\FeesController;
// Экран 1: текущие спреды
Route::get('/', [SpreadsController::class, 'index'])->name('spreads.index');

// Экран 2: история (график)
Route::get('/history', [SpreadsController::class, 'history'])->name('spreads.history');

// Экран 3: пики
Route::get('/peaks', [PeaksController::class, 'index'])->name('peaks.index');

// Экран 4: тепловая карта
Route::get('/heatmap', [HeatmapController::class, 'index'])->name('heatmap.index');

Route::get('/fees', [FeesController::class, 'index'])->name('fees.index');