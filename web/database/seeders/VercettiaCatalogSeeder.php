<?php

namespace Database\Seeders;

use App\Models\Category;
use App\Models\Product;
use Illuminate\Database\Seeder;
use Illuminate\Support\Str;

class VercettiaCatalogSeeder extends Seeder
{
    public function run(): void
    {
        $categories = [
            'editing' => [
                'name' => 'Editing Apps',
                'description' => 'Aplikasi kreatif premium untuk desain, video, dan konten harian.',
                'sort_order' => 10,
            ],
            'streaming' => [
                'name' => 'Streaming',
                'description' => 'Akses hiburan premium untuk tontonan harian dengan proses cepat.',
                'sort_order' => 20,
            ],
        ];

        $categoryModels = [];
        foreach ($categories as $key => $category) {
            $categoryModels[$key] = Category::query()->updateOrCreate(
                ['slug' => $key],
                [
                    'name' => $category['name'],
                    'description' => $category['description'],
                    'sort_order' => $category['sort_order'],
                    'is_active' => true,
                ],
            );
        }

        foreach ($this->products() as $product) {
            Product::query()->updateOrCreate(
                ['supplier_code' => $product['supplier_code']],
                [
                    'category_id' => $categoryModels[$product['category']]->id,
                    'name' => $product['name'],
                    'slug' => Str::slug($product['name']),
                    'duration' => $product['duration'],
                    'access_type' => $product['access_type'],
                    'price' => $product['price'],
                    'stock' => $product['stock'],
                    'status' => $product['stock'] === 0 ? 'Kosong' : 'Ready',
                    'description' => $product['description'],
                    'is_active' => true,
                ],
            );
        }
    }

    private function products(): array
    {
        return [
            [
                'supplier_code' => 'ALIGHT MOTION PRIVATE 1 TAHUN',
                'name' => 'Alight Motion Private 1 Tahun',
                'duration' => '1 Tahun',
                'access_type' => 'Private',
                'price' => 49000,
                'stock' => 21,
                'description' => 'Akses premium tahunan untuk editing motion, efek visual, dan kebutuhan konten kreatif.',
                'category' => 'editing',
            ],
            [
                'supplier_code' => 'CANVA MEMBER 1 BULAN',
                'name' => 'Canva Pro Member 1 Bulan',
                'duration' => '1 Bulan',
                'access_type' => 'Shared',
                'price' => 15000,
                'stock' => 17,
                'description' => 'Akses Canva Pro untuk desain, template premium, brand kit, dan kebutuhan visual harian.',
                'category' => 'editing',
            ],
            [
                'supplier_code' => 'HBO MAX STANDARD SHAR',
                'name' => 'HBO Max Standard 1 Bulan',
                'duration' => '1 Bulan',
                'access_type' => 'Shared',
                'price' => 12000,
                'stock' => 1,
                'description' => 'Paket tontonan premium HBO Max Standard untuk akses film dan serial pilihan.',
                'category' => 'streaming',
            ],
            [
                'supplier_code' => 'IQIYI STD SHAR 1 BULAN',
                'name' => 'iQIYI Standard 1 Bulan',
                'duration' => '1 Bulan',
                'access_type' => 'Shared',
                'price' => 12000,
                'stock' => 3,
                'description' => 'Akses iQIYI Standard untuk menikmati drama, anime, dan entertainment Asia.',
                'category' => 'streaming',
            ],
            [
                'supplier_code' => 'LOKLOK STANDAR SHAR 1B',
                'name' => 'LokLok Standard 1 Bulan',
                'duration' => '1 Bulan',
                'access_type' => 'Shared',
                'price' => 35000,
                'stock' => 4,
                'description' => 'Akses LokLok Standard dengan katalog hiburan lengkap untuk pemakaian bulanan.',
                'category' => 'streaming',
            ],
            [
                'supplier_code' => 'PICSART SHAR 1 BULAN',
                'name' => 'PicsArt Premium 1 Bulan',
                'duration' => '1 Bulan',
                'access_type' => 'Shared',
                'price' => 10000,
                'stock' => 2,
                'description' => 'Akses fitur premium PicsArt untuk editing foto, template, dan aset kreatif.',
                'category' => 'editing',
            ],
            [
                'supplier_code' => 'PRIME VIDEO SHAR 1 BULAN',
                'name' => 'Prime Video 1 Bulan',
                'duration' => '1 Bulan',
                'access_type' => 'Shared',
                'price' => 15000,
                'stock' => 2,
                'description' => 'Akses Prime Video untuk film, series, dan hiburan premium selama satu bulan.',
                'category' => 'streaming',
            ],
            [
                'supplier_code' => 'VIU PRIVATE ANLIM 1 TAHUN',
                'name' => 'VIU Private 1 Tahun',
                'duration' => '1 Tahun',
                'access_type' => 'Private',
                'price' => 10000,
                'stock' => 31,
                'description' => 'Akun VIU private tahunan untuk menikmati drama, film, dan konten Asia favorit.',
                'category' => 'streaming',
            ],
            [
                'supplier_code' => 'WETV 6U SHAR 1 BULAN',
                'name' => 'WeTV Premium 1 Bulan',
                'duration' => '1 Bulan',
                'access_type' => 'Shared',
                'price' => 18000,
                'stock' => 3,
                'description' => 'Akses WeTV Premium untuk tontonan drama, serial, dan konten pilihan selama satu bulan.',
                'category' => 'streaming',
            ],
            [
                'supplier_code' => 'YOUKU SHAR 1 BULAN',
                'name' => 'Youku Premium 1 Bulan',
                'duration' => '1 Bulan',
                'access_type' => 'Shared',
                'price' => 10000,
                'stock' => 3,
                'description' => 'Akses Youku Premium untuk hiburan Asia dan katalog tontonan bulanan.',
                'category' => 'streaming',
            ],
        ];
    }
}
