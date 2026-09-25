#!/bin/sh
# Запуск в контейнере: подготовка данных, затем веб-сервер.
set -e

# Миграции, администратор и демо-данные - одной командой.
python manage.py prestart

# --preload: код загружается один раз до создания рабочих процессов.
# gthread: один процесс с несколькими потоками; этого хватает слабому
# процессору бесплатного хостинга и ускоряет запуск.
exec gunicorn task_manager.wsgi:application \
    --bind "0.0.0.0:${PORT:-8000}" \
    --preload \
    --worker-class gthread \
    --workers "${WEB_CONCURRENCY:-2}" \
    --threads "${GUNICORN_THREADS:-4}" \
    --timeout 60 \
    --access-logfile -
