-- init.sql (в корне проекта)
-- Этот файл выполнится автоматически при первом запуске PostgreSQL

-- Создаем базу данных если её нет
SELECT 'CREATE DATABASE hrdb'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'hrdb')\gexec

-- Подключаемся к базе
\c hrdb;

-- Создаем схему если нужно
CREATE SCHEMA IF NOT EXISTS public;

-- Даем права пользователю
GRANT ALL PRIVILEGES ON DATABASE hrdb TO hruser;
GRANT ALL ON SCHEMA public TO hruser;

-- Проверочный запрос
SELECT current_database(), current_user;