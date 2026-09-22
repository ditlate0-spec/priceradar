"""
Модуль порогов.

ВАЖНО: в проекте два независимых множества порогов (см. ТЗ 6.1):
- пороги подсветки (highlight):  0.3 / 0.8 / 1.5 / 2.0
- пороги пиков и счётчиков (peak): 0.3 / 0.5 / 1.0 / 2.0

Не путать. Подсветка — для UI, пики — для событий и счётчиков seconds_above_*.
"""
from enum import StrEnum

from app.core.config import get_settings


class HighlightLevel(StrEnum):
    NORM = "norm"
    NOTICE = "notice"           # 0.3 <= |x| < 0.8
    SIGNIFICANT = "significant" # 0.8 <= |x| < 1.5
    STRONG = "strong"           # 1.5 <= |x| < 2.0
    EXTREME = "extreme"         # |x| >= 2.0


def get_highlight_level(spread_net: float) -> HighlightLevel:
    """
    Возвращает уровень подсветки по значению net-спреда (в процентах).

    Пороги: 0.3 / 0.8 / 1.5 / 2.0. Сравнение — по модулю.
    """
    x = abs(spread_net)
    thresholds = get_settings().highlight_thresholds_list  # [0.3, 0.8, 1.5, 2.0]

    if x < thresholds[0]:
        return HighlightLevel.NORM
    if x < thresholds[1]:
        return HighlightLevel.NOTICE
    if x < thresholds[2]:
        return HighlightLevel.SIGNIFICANT
    if x < thresholds[3]:
        return HighlightLevel.STRONG
    return HighlightLevel.EXTREME


def is_peak(threshold: float, spread_net: float) -> bool:
    """Превышает ли |spread_net| указанный порог пика (в процентах)."""
    return abs(spread_net) >= threshold


def get_active_peak_threshold(spread_net: float) -> float | None:
    """
    Возвращает наибольший порог пика, который превышен.
    Если ни один не превышен — None.
    """
    x = abs(spread_net)
    active: float | None = None
    for threshold in get_settings().peak_thresholds_list:
        if x >= threshold:
            active = threshold
    return active