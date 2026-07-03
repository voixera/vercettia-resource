<?php

namespace App\Repositories;

use App\Models\Product;
use Illuminate\Database\Eloquent\Collection;

class ProductRepository
{
    public function activeCatalog(): Collection
    {
        return Product::query()
            ->with('category')
            ->where('is_active', true)
            ->orderBy('name')
            ->get();
    }

    public function findBySlug(string $slug): ?Product
    {
        return Product::query()
            ->with('category')
            ->where('slug', $slug)
            ->where('is_active', true)
            ->first();
    }
}
