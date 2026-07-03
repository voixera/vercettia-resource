<?php

namespace App\Http\Controllers\Web;

use App\Http\Controllers\Controller;
use App\Services\ProductCatalogService;
use Illuminate\Contracts\View\View;

class HomeController extends Controller
{
    public function __construct(
        private readonly ProductCatalogService $catalog,
    ) {
    }

    public function __invoke(): View
    {
        return view('pages.home', [
            'catalog' => $this->catalog->catalog(),
        ]);
    }
}
