<!doctype html>
<html lang="id">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="theme-color" content="#000000">
    <meta name="description" content="Vercettia Store, marketplace APK premium dengan checkout QRIS dan support ticket.">
    <title>{{ $title ?? 'Vercettia Store' }}</title>
    @vite(['resources/css/app.css', 'resources/js/app.ts'])
</head>
<body>
    <div class="site-shell">
        {{ $slot }}
    </div>
</body>
</html>
