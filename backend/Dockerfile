FROM php:8.2-fpm-alpine

# Системные зависимости
RUN apk add --no-cache \
    bash \
    git \
    curl \
    libpng-dev \
    libxml2-dev \
    oniguruma-dev \
    zip \
    unzip \
    icu-dev

# PHP-расширения для Laravel
RUN docker-php-ext-install \
    pdo_mysql \
    mbstring \
    exif \
    pcntl \
    bcmath \
    gd \
    intl \
    opcache

# Composer
COPY --from=composer:2 /usr/bin/composer /usr/bin/composer

# Рабочая директория
WORKDIR /var/www/html

# Права: www-data — пользователь php-fpm
RUN chown -R www-data:www-data /var/www/html

# PHP-FPM слушает на 9000
EXPOSE 9000

CMD ["php-fpm"]