"""Точка входа инструмента визуализации зависимостей."""

from depsview.config import parse_args
from depsview.repository import NuGetRepository, TestRepository


def main(argv=None):
    """Показать настройки или прочитать прямые зависимости NuGet."""
    cfg = parse_args(argv)
    if cfg.stage == 1:
        for key, value in vars(cfg).items():
            print(f"{key}={value}")
        return 0
    try:
        repo = (TestRepository(cfg.repository) if cfg.test_mode else
                NuGetRepository(cfg.repository, cfg.framework))
        root = repo.resolve(cfg.package, cfg.package_version)
        print(f"Пакет: {root}; платформа: {cfg.framework}")
        for dependency in repo.dependencies(root):
            print(dependency)
    except (ValueError, OSError, KeyError) as error:
        print(f"Ошибка: {error}", file=__import__("sys").stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
