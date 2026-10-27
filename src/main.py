"""Точка входа инструмента визуализации зависимостей."""

import sys

from depsview.config import parse_args
from depsview.graph import build_graph
from depsview.repository import NuGetRepository, TestRepository


def show_graph(graph):
    """Вывести вершины и рёбра построенного графа."""
    print(f"Вершин: {len(graph)}")
    for node, children in graph.items():
        print(f"{node} -> {', '.join(map(str, children)) or '(нет)'}")


def run(cfg):
    """Выполнить выбранный этап после проверки параметров."""
    repo = (TestRepository(cfg.repository) if cfg.test_mode else
            NuGetRepository(cfg.repository, cfg.framework))
    root = repo.resolve(cfg.package, cfg.package_version)
    print(f"Пакет: {root}; платформа: {cfg.framework}")
    if cfg.stage == 2:
        for dependency in repo.dependencies(root):
            print(dependency)
        return
    graph = build_graph(repo, root, cfg.exclude, cfg.max_nodes)
    show_graph(graph)


def main(argv=None):
    """Прочитать параметры и вернуть обычный код завершения CLI."""
    cfg = parse_args(argv)
    if cfg.stage == 1:
        for key, value in vars(cfg).items():
            print(f"{key}={value}")
        return 0
    try:
        run(cfg)
    except (ValueError, OSError, KeyError) as error:
        print(f"Ошибка: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
