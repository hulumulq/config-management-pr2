"""Выбор одной совместимой группы .nuspec вместо смешивания платформ."""

import re


def framework_key(value):
    """Нормализовать используемые net/netcoreapp/netstandard обозначения."""
    value = value.lower().replace(" ", "")
    for prefix, family in [
        (".netframework", "framework"),
        (".netstandard", "standard"),
        ("netstandard", "standard"),
        (".netcoreapp", "core"),
        ("netcoreapp", "core"),
        ("net", "modern"),
    ]:
        if not value.startswith(prefix):
            continue
        number = value[len(prefix):].removeprefix("v")
        if not re.fullmatch(r"\d+(?:\.\d+){0,2}", number):
            break
        if family == "modern" and "." not in number:
            family, parts = "framework", tuple(map(int, number))
        else:
            parts = tuple(map(int, number.split(".")))
        return family, parts + (0,) * (3 - len(parts))
    raise ValueError(f"Неподдерживаемая платформа: {value}")


def compatibility(candidate, target):
    """Вернуть ранг совместимости; None означает несовместимую группу."""
    family, number = framework_key(target)
    if not candidate:
        return (0, 0, 0, 0)
    try:
        source, version = framework_key(candidate)
    except ValueError:
        return None
    if source == family and version <= number:
        return (3,) + version
    if family == "modern" and source == "core" and version <= (3, 1, 0):
        return (2,) + version
    if family in ("modern", "core") and source == "standard":
        ceiling = (2, 1, 0) if number >= (3, 0, 0) else (2, 0, 0)
        if version <= ceiling:
            return (1,) + version
    return None
