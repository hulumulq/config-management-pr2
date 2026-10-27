"""Небольшая реализация используемых NuGet диапазонов версий."""

import re

VERSION = re.compile(r"(\d+(?:\.\d+){0,3})(?:-([\w.-]+))?(?:\+[\w.-]+)?\Z")


def version_key(value):
    """Ключ NuGet/SemVer: числа, затем prerelease, затем стабильная версия."""
    match = VERSION.fullmatch(value)
    if not match:
        raise ValueError(f"Некорректная версия: {value}")
    numbers = tuple(int(n) for n in match[1].split("."))
    numbers += (0,) * (4 - len(numbers))
    suffix = match[2]
    parts = tuple((0, int(p)) if p.isdigit() else (1, p.lower())
                  for p in (suffix or "").split("."))
    return numbers, suffix is None, parts


def _lower_matches(key, boundary, inclusive):
    """Проверить нижнюю границу, если она задана."""
    if not boundary:
        return True
    bound = version_key(boundary)
    return key >= bound if inclusive else key > bound


def _upper_matches(key, boundary, inclusive):
    """Проверить верхнюю границу, если она задана."""
    if not boundary:
        return True
    bound = version_key(boundary)
    return key <= bound if inclusive else key < bound


def _interval_matches(key, requirement):
    """Прочитать [точную] или интервальную форму ограничения."""
    if not requirement.endswith(("]", ")")):
        raise ValueError("Незакрытый диапазон версии")
    body = requirement[1:-1]
    if "," not in body:
        if requirement[0] != "[" or requirement[-1] != "]":
            raise ValueError("Точная версия задаётся как [1.0.0]")
        return key == version_key(body)
    low, high = (p.strip() for p in body.split(",", 1))
    return (_lower_matches(key, low, requirement[0] == "[")
            and _upper_matches(key, high, requirement[-1] == "]"))


def in_range(value, requirement):
    """Проверить точную, минимальную, интервальную или floating-версию."""
    if not requirement or requirement == "*":
        return True
    if "*" in requirement:
        if not re.fullmatch(r"(?:\d+\.)*\*", requirement):
            raise ValueError("Неподдерживаемый floating-диапазон")
        return value.startswith(requirement[:-1])
    key = version_key(value)
    if requirement.startswith(("[", "(")):
        return _interval_matches(key, requirement)
    return key >= version_key(requirement)


def choose_version(versions, requirement=""):
    """Корень: последняя stable; зависимость: наименьшая подходящая."""
    candidates = [v for v in versions
                  if ("-" in requirement or "-" not in v)
                  and in_range(v, requirement)]
    if not candidates:
        raise ValueError(f"Нет подходящей версии: {requirement or 'stable'}")
    pick = max if not requirement or "*" in requirement else min
    return pick(candidates, key=version_key)
