<?php

use App\Http\Controllers\Api\ProductController;
use App\Http\Controllers\Api\StatisticController;
use Illuminate\Support\Facades\Route;

Route::prefix('v1')->group(function (): void {
    Route::get('/products', [ProductController::class, 'index']);
    Route::get('/products/{product:slug}', [ProductController::class, 'show']);
    Route::get('/statistics', StatisticController::class);
});
