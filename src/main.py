"""Точка входа инструмента визуализации зависимостей."""

from depsview.config import parse_args


def main(argv=None):
    """На первом этапе показать все пользовательские параметры."""
    cfg = parse_args(argv)
    for key, value in vars(cfg).items():
        print(f"{key}={value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
