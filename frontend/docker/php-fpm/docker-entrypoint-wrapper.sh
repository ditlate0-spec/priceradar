#!/bin/sh
set -e

# При каждом старте контейнера даём www-data права на те папки,
# куда Laravel пишет (storage, bootstrap/cache, database).
# Это нужно, потому что при host-mount с Windows владельцем файлов
# становится root, а php-fpm работает под www-data.

mkdir -p storage/logs storage/framework/sessions storage/framework/views storage/framework/cache/data

chown -R www-data:www-data storage bootstrap/cache database 2>/dev/null || true
chmod -R 775 storage bootstrap/cache database 2>/dev/null || true

# Запускаем оригинальный entrypoint
exec docker-php-entrypoint "$@"