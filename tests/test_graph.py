"""Транзитивные зависимости, нерекурсивный обход, фильтры и циклы."""

import unittest

from depsview.graph import build_graph, load_order
from depsview.repository import Package


class MemoryRepository:
    """Явные зависимости и журнал обращений для проверки обхода."""

    def __init__(self, data):
        """Запомнить граф и начать пустой журнал обращений."""
        self.data, self.calls = data, []

    def dependencies(self, node):
        """Записать обращение и вернуть прямые зависимости узла."""
        self.calls.append(node.name)
        return [Package(name) for name in self.data[node.name]]


class GraphTest(unittest.TestCase):
    """Зависимость анализируется один раз, независимо от числа путей."""

    def test_depth_first_order(self):
        """Обход идёт в глубину: A, B, D, затем C."""
        repo = MemoryRepository({"A": ["B", "C"], "B": ["D"],
                                 "C": [], "D": []})
        graph = build_graph(repo, Package("A"))
        self.assertEqual(repo.calls, ["A", "B", "D", "C"])
        self.assertEqual(len(graph), 4)

    def test_diamond_has_no_duplicate_fetch(self):
        """Общая зависимость ромба запрашивается один раз."""
        repo = MemoryRepository({"A": ["B", "C"], "B": ["D"],
                                 "C": ["D"], "D": []})
        graph = build_graph(repo, Package("A"))
        self.assertEqual(len(graph), 4)
        self.assertEqual(repo.calls.count("D"), 1)

    def test_cycle_is_preserved_without_loop(self):
        """Цикл сохраняется в графе и не зацикливает обход."""
        repo = MemoryRepository({"A": ["B"], "B": ["A"]})
        graph = build_graph(repo, Package("A"))
        self.assertEqual(repo.calls, ["A", "B"])
        self.assertEqual(graph[Package("B")], [Package("A")])

    def test_self_cycle(self):
        """Пакет, зависящий от себя, обрабатывается корректно."""
        repo = MemoryRepository({"A": ["A"]})
        graph = build_graph(repo, Package("A"))
        self.assertEqual(len(graph), 1)

    def test_excluded_branch_is_not_traversed(self):
        """Ветка с исключённой подстрокой не обходится."""
        repo = MemoryRepository({"A": ["SKIP", "B"], "B": [],
                                 "SKIP": ["X"], "X": []})
        graph = build_graph(repo, Package("A"), exclude="skip")
        self.assertEqual(set(map(str, graph)), {"A", "B"})
        self.assertNotIn("SKIP", repo.calls)

    def test_excluded_root_is_an_error(self):
        """Исключение корневого пакета считается ошибкой."""
        with self.assertRaisesRegex(ValueError, "Корневой"):
            build_graph(MemoryRepository({"A": []}), Package("A"),
                        exclude="A")

    def test_more_than_recursion_limit(self):
        """Цепочка длиннее предела рекурсии Python обходится."""
        count = 1100
        data = {f"N{i}": [f"N{i + 1}"] for i in range(count - 1)}
        data[f"N{count - 1}"] = []
        graph = build_graph(MemoryRepository(data), Package("N0"),
                            max_nodes=count)
        self.assertEqual(len(graph), count)

    def test_node_limit_boundary(self):
        """Ограничение числа вершин срабатывает на границе."""
        repo = MemoryRepository({"A": ["B"], "B": []})
        self.assertEqual(len(build_graph(repo, Package("A"),
                                         max_nodes=2)), 2)
        with self.assertRaisesRegex(ValueError, "Лимит"):
            build_graph(repo, Package("A"), max_nodes=1)

    def test_package_names_are_case_insensitive(self):
        """Имена пакетов NuGet сравниваются без учёта регистра."""
        self.assertEqual(Package("Serilog", "3.0"),
                         Package("serilog", "3.0"))
        self.assertEqual(len({Package("A"), Package("a")}), 1)


class LoadOrderTest(unittest.TestCase):
    """В допустимом порядке каждая зависимость предшествует пакету."""

    def test_dependencies_precede_users(self):
        """Зависимости в порядке загрузки идут раньше пакетов."""
        repo = MemoryRepository({"A": ["B", "C"], "B": ["D"],
                                 "C": ["D"], "D": []})
        graph = build_graph(repo, Package("A"))
        order = load_order(graph, Package("A"))
        positions = {node: index for index, node in enumerate(order)}
        for node, children in graph.items():
            for child in children:
                self.assertLess(positions[child], positions[node])
        self.assertEqual(len(order), 4)
        self.assertEqual(str(order[-1]), "A")

    def test_single_node(self):
        """Порядок загрузки одиночного пакета состоит из него."""
        root = Package("A")
        self.assertEqual(load_order({root: []}, root), [root])

    def test_cycle_has_no_valid_order(self):
        """Для цикла допустимого порядка загрузки нет."""
        repo = MemoryRepository({"A": ["B"], "B": ["C"], "C": ["A"]})
        graph = build_graph(repo, Package("A"))
        with self.assertRaisesRegex(ValueError, "A -> B -> C -> A"):
            load_order(graph, Package("A"))

    def test_self_cycle_has_no_valid_order(self):
        """Для самозависимости порядка загрузки нет."""
        root = Package("A")
        with self.assertRaisesRegex(ValueError, "Цикл"):
            load_order({root: [root]}, root)

    def test_deep_order_without_recursion(self):
        """Порядок длинной цепочки строится без рекурсии."""
        count = 1100
        data = {f"N{i}": [f"N{i + 1}"] for i in range(count - 1)}
        data[f"N{count - 1}"] = []
        root = Package("N0")
        graph = build_graph(MemoryRepository(data), root, max_nodes=count)
        order = load_order(graph, root)
        self.assertEqual(str(order[0]), f"N{count - 1}")
        self.assertEqual(len(order), count)
