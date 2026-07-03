<?php

use Illuminate\Support\Facades\Artisan;

Artisan::command('vercettia:about', function (): void {
    $this->info('Vercettia Store marketplace core is ready.');
});
