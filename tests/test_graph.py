"""Транзитивные зависимости, нерекурсивный обход, фильтры и циклы."""

import unittest

from depsview.graph import build_graph
from depsview.repository import Package


class MemoryRepository:
    """Явные зависимости и журнал обращений для проверки обхода."""

    def __init__(self, data):
        self.data, self.calls = data, []

    def dependencies(self, node):
        self.calls.append(node.name)
        return [Package(name) for name in self.data[node.name]]


class GraphTest(unittest.TestCase):
    """Зависимость анализируется один раз, независимо от числа путей."""

    def test_depth_first_order(self):
        repo = MemoryRepository({"A": ["B", "C"], "B": ["D"],
                                 "C": [], "D": []})
        graph = build_graph(repo, Package("A"))
        self.assertEqual(repo.calls, ["A", "B", "D", "C"])
        self.assertEqual(len(graph), 4)

    def test_diamond_has_no_duplicate_fetch(self):
        repo = MemoryRepository({"A": ["B", "C"], "B": ["D"],
                                 "C": ["D"], "D": []})
        graph = build_graph(repo, Package("A"))
        self.assertEqual(len(graph), 4)
        self.assertEqual(repo.calls.count("D"), 1)

    def test_cycle_is_preserved_without_loop(self):
        repo = MemoryRepository({"A": ["B"], "B": ["A"]})
        graph = build_graph(repo, Package("A"))
        self.assertEqual(repo.calls, ["A", "B"])
        self.assertEqual(graph[Package("B")], [Package("A")])

    def test_self_cycle(self):
        repo = MemoryRepository({"A": ["A"]})
        graph = build_graph(repo, Package("A"))
        self.assertEqual(len(graph), 1)

    def test_excluded_branch_is_not_traversed(self):
        repo = MemoryRepository({"A": ["SKIP", "B"], "B": [],
                                 "SKIP": ["X"], "X": []})
        graph = build_graph(repo, Package("A"), exclude="skip")
        self.assertEqual(set(map(str, graph)), {"A", "B"})
        self.assertNotIn("SKIP", repo.calls)

    def test_excluded_root_is_an_error(self):
        with self.assertRaisesRegex(ValueError, "Корневой"):
            build_graph(MemoryRepository({"A": []}), Package("A"),
                        exclude="A")

    def test_more_than_recursion_limit(self):
        count = 1100
        data = {f"N{i}": [f"N{i + 1}"] for i in range(count - 1)}
        data[f"N{count - 1}"] = []
        graph = build_graph(MemoryRepository(data), Package("N0"),
                            max_nodes=count)
        self.assertEqual(len(graph), count)

    def test_node_limit_boundary(self):
        repo = MemoryRepository({"A": ["B"], "B": []})
        self.assertEqual(len(build_graph(repo, Package("A"),
                                         max_nodes=2)), 2)
        with self.assertRaisesRegex(ValueError, "Лимит"):
            build_graph(repo, Package("A"), max_nodes=1)

    def test_package_names_are_case_insensitive(self):
        self.assertEqual(Package("Serilog", "3.0"),
                         Package("serilog", "3.0"))
        self.assertEqual(len({Package("A"), Package("a")}), 1)
