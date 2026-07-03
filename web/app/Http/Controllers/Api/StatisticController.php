<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Models\Product;
use Illuminate\Http\JsonResponse;

class StatisticController extends Controller
{
    public function __invoke(): JsonResponse
    {
        return response()->json([
            'data' => [
                'products' => Product::query()->where('is_active', true)->count(),
                'ready_products' => Product::query()->where('is_active', true)->where('stock', '!=', 0)->count(),
                'categories' => Product::query()->where('is_active', true)->distinct('category_id')->count('category_id'),
            ],
        ]);
    }
}
