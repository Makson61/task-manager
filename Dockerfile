# Облегчённый официальный образ Python.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Зависимости ставятся первыми, чтобы Docker кэшировал этот слой.
COPY requirements.txt .
RUN python -m pip install --no-cache-dir -r requirements.txt

COPY . .

# Статические файлы собираются на этапе сборки образа.
# Ключ нужен только для запуска collectstatic и никуда не сохраняется.
RUN DJANGO_SECRET_KEY=build-stage-only DJANGO_DEBUG=False \
    python manage.py collectstatic --noinput

# Приложение работает не от root; каталог data - для базы SQLite на томе.
RUN useradd --create-home --uid 1000 app \
    && mkdir -p /app/data \
    && chown -R app:app /app/data
USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:%s/healthz/' % os.getenv('PORT', '8000'), timeout=3)"

CMD ["sh", "start.sh"]
