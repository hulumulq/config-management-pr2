"""Параметры командной строки, проверяемые до сетевых запросов."""

import argparse
import re
from pathlib import Path
from urllib.parse import urlsplit

from depsview.frameworks import framework_key

DEFAULT_REPOSITORY = "https://api.nuget.org/v3/index.json"
PACKAGE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,99}\Z")
PARAMETERS, DIRECT, GRAPH, ORDER, VISUAL = range(1, 6)


def parser():
    """Создать открытый список настроек приложения."""
    cli = argparse.ArgumentParser(description="Граф зависимостей NuGet")
    cli.add_argument("--package", required=True, help="Имя пакета")
    cli.add_argument("--repository", default=DEFAULT_REPOSITORY)
    cli.add_argument("--test", dest="test_mode", action="store_true")
    cli.add_argument("--output", type=Path, default=Path("graph.svg"))
    cli.add_argument("--ascii", dest="ascii_tree", action="store_true")
    cli.add_argument("--exclude", default="", help="Исключаемая подстрока")
    cli.add_argument("--package-version", default="")
    cli.add_argument("--framework", default="net8.0")
    cli.add_argument("--stage", type=int, choices=range(1, 6), default=VISUAL)
    cli.add_argument("--max-nodes", type=int, default=200)
    return cli


def check_repository(cfg, cli):
    """Различить локальный тестовый файл и сетевой service index."""
    if cfg.test_mode:
        if not Path(cfg.repository).is_file():
            cli.error("Тестовый репозиторий не найден")
    else:
        url = urlsplit(cfg.repository)
        if url.scheme not in ("http", "https") or not url.hostname:
            cli.error("Репозиторий должен быть HTTP(S) URL")
        if url.username or url.password:
            cli.error("URL с учётными данными не поддерживается")


def parse_args(argv=None):
    """Прочитать настройки и отклонить некорректные комбинации."""
    cli = parser()
    cfg = cli.parse_args(argv)
    if not PACKAGE.fullmatch(cfg.package):
        cli.error("Некорректное имя пакета")
    if cfg.max_nodes < 1:
        cli.error("--max-nodes должен быть положительным")
    if cfg.output.suffix.lower() != ".svg":
        cli.error("--output должен оканчиваться на .svg")
    if not cfg.output.parent.is_dir() or cfg.output.is_dir():
        cli.error("Папка для --output не существует или указан каталог")
    try:
        framework_key(cfg.framework)
    except ValueError as error:
        cli.error(str(error))
    check_repository(cfg, cli)
    return cfg
