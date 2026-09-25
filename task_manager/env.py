"""Чтение настроек из переменных окружения.

Вынесено в отдельный модуль, чтобы settings.py оставался списком настроек,
а не смесью настроек и разбора строк.
"""
import os

TRUE_VALUES = ('1', 'true', 'yes', 'on')


def text(name, default=''):
    """Строка из окружения."""
    return os.getenv(name, default).strip()


def flag(name, default=False):
    """Логическое значение: 1/true/yes/on считаются истиной."""
    return os.getenv(name, str(default)).strip().lower() in TRUE_VALUES


def number(name, default=0):
    """Целое число; при пустом или неверном значении берётся default."""
    try:
        return int(os.getenv(name, '').strip())
    except ValueError:
        return default


def items(name, default=''):
    """Список из строки вида "a, b, c"."""
    return [part.strip() for part in os.getenv(name, default).split(',') if part.strip()]
