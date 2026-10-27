"""Точка входа инструмента визуализации зависимостей."""

import sys

from depsview.config import DIRECT, GRAPH, ORDER, PARAMETERS, parse_args
from depsview.graph import build_graph, load_order
from depsview.repository import NuGetRepository, TestRepository
from depsview.visualize import ascii_tree, render_svg


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
    if cfg.stage == DIRECT:
        for dependency in repo.dependencies(root):
            print(dependency)
        return
    graph = build_graph(repo, root, cfg.exclude, cfg.max_nodes)
    if cfg.stage == ORDER:
        print("Порядок загрузки: " + " -> ".join(map(str, load_order(
            graph, root))))
    elif cfg.stage == GRAPH:
        show_graph(graph)
    else:
        render_svg(graph, cfg.output, root)
        print(f"Graphviz: {cfg.output.with_suffix('.dot')}")
        print(f"Изображение: {cfg.output}")
        if cfg.ascii_tree:
            print(ascii_tree(graph, root))


def main(argv=None):
    """Прочитать параметры и вернуть обычный код завершения CLI."""
    cfg = parse_args(argv)
    if cfg.stage == PARAMETERS:
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
