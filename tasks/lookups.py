"""
Поиск без учёта регистра для кириллицы в SQLite.

Встроенный в SQLite оператор LIKE приводит к одному регистру только латиницу,
поэтому запрос «питон» не находит «Питон». Здесь LIKE заменяется функцией на
Python со сравнением через casefold(). В PostgreSQL подмена не выполняется.
"""
import re
from functools import lru_cache

from django.db.backends.signals import connection_created

WILDCARDS = {'%': '.*', '_': '.'}


@lru_cache(maxsize=512)
def compile_pattern(pattern, escape):
    """Переводит шаблон LIKE в регулярное выражение."""
    parts = []
    index = 0
    while index < len(pattern):
        char = pattern[index]
        if escape and char == escape and index + 1 < len(pattern):
            parts.append(re.escape(pattern[index + 1]))
            index += 2
            continue
        parts.append(WILDCARDS.get(char) or re.escape(char))
        index += 1
    return re.compile(''.join(parts), re.DOTALL)


def like(pattern, value, escape=None):
    if pattern is None or value is None:
        return None
    return compile_pattern(pattern.casefold(), escape).fullmatch(str(value).casefold()) is not None


def register(sender, connection, **kwargs):
    if connection.vendor == 'sqlite':
        for argument_count in (2, 3):
            connection.connection.create_function('like', argument_count, like, deterministic=True)


def install():
    """Подключается один раз из AppConfig.ready()."""
    connection_created.connect(register, dispatch_uid='unicode_like')
