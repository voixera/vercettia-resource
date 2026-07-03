<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Services\ProductCatalogService;
use Illuminate\Http\JsonResponse;

class ProductController extends Controller
{
    public function __construct(
        private readonly ProductCatalogService $catalog,
    ) {
    }

    public function index(): JsonResponse
    {
        return response()->json([
            'data' => $this->catalog->catalog(),
        ]);
    }

    public function show(string $slug): JsonResponse
    {
        $product = $this->catalog->detail($slug);

        abort_if($product === null, 404);

        return response()->json([
            'data' => $product,
        ]);
    }
}
