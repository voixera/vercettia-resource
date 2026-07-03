<?php

namespace App\Services;

use App\Models\Product;
use App\Repositories\ProductRepository;
use Illuminate\Support\Collection;

class ProductCatalogService
{
    public function __construct(
        private readonly ProductRepository $products,
    ) {
    }

    public function catalog(): Collection
    {
        return $this->products->activeCatalog()
            ->groupBy(fn (Product $product): string => $product->category->name)
            ->map(fn (Collection $items): array => [
                'products' => $items->map(fn (Product $product): array => $this->serialize($product))->values(),
            ]);
    }

    public function detail(string $slug): ?array
    {
        $product = $this->products->findBySlug($slug);

        return $product ? $this->serialize($product) : null;
    }

    private function serialize(Product $product): array
    {
        return [
            'id' => $product->id,
            'name' => $product->name,
            'slug' => $product->slug,
            'category' => $product->category->name,
            'duration' => $product->duration,
            'access_type' => $product->access_type,
            'price' => $product->price,
            'stock' => $product->stock,
            'status' => $product->stock === 0 ? 'Kosong' : $product->status,
            'description' => $product->description,
        ];
    }
}
