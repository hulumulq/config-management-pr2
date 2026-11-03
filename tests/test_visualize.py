"""Текст графа, ASCII и настоящее построение SVG."""

import shutil
import subprocess
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import patch

from depsview.repository import Package
from depsview.visualize import ascii_tree, render_svg, to_dot


def graph_of(data):
    """Преобразовать краткую запись графа в вершины приложения."""
    return {Package(n): [Package(c) for c in children]
            for n, children in data.items()}


class VisualizeTest(unittest.TestCase):
    """Повторная вершина и цикл не должны бесконечно разворачивать дерево."""

    def test_shared_dependency_is_marked(self):
        """Общая зависимость отмечается в ASCII-дереве."""
        graph = graph_of({"A": ["B", "C"], "B": ["D"],
                          "C": ["D"], "D": []})
        tree = ascii_tree(graph, Package("A"))
        self.assertIn("|-- B", tree)
        self.assertIn("`-- C", tree)
        self.assertIn("D [повтор]", tree)
        self.assertNotIn("[цикл]", tree)

    def test_cycle_is_marked(self):
        """Цикл отмечается в ASCII-дереве."""
        graph = graph_of({"A": ["B"], "B": ["A"]})
        tree = ascii_tree(graph, Package("A"))
        self.assertIn("A [цикл]", tree)
        self.assertEqual(len(tree.splitlines()), 3)

    def test_single_node(self):
        """Дерево одиночного пакета состоит из корня."""
        graph = graph_of({"A": []})
        self.assertEqual(ascii_tree(graph, Package("A")), "A")

    def test_dot_includes_isolated_vertex(self):
        """DOT содержит вершину без рёбер."""
        text = to_dot(graph_of({"A": []}))
        self.assertIn('"A";', text)
        self.assertIn("digraph", text)

    def test_dot_escapes_quotes(self):
        """Кавычки в именах экранируются в DOT."""
        text = to_dot({Package('A"B'): []})
        self.assertIn('"A\\"B";', text)

    def test_case_alias_does_not_create_a_phantom_vertex(self):
        """Разный регистр имени не создаёт лишнюю вершину."""
        text = to_dot({Package("A"): [Package("a")]})
        self.assertIn('"A" -> "A";', text)
        self.assertNotIn('"a"', text)

    @unittest.skipUnless(shutil.which("dot"), "Нужен Graphviz")
    def test_real_svg(self):
        """Graphviz строит настоящий SVG-файл."""
        graph = graph_of({"A": ["B"], "B": []})
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "graph.svg"
            render_svg(graph, path, Package("A"))
            root = ET.fromstring(path.read_text())
            self.assertTrue(root.tag.endswith("svg"))
            text = " ".join(root.itertext())
            self.assertIn("A", text)
            self.assertIn("B", text)
            self.assertTrue(path.with_suffix(".dot").is_file())

    def test_missing_graphviz_is_clear_error(self):
        """Отсутствие Graphviz даёт понятную ошибку."""
        with tempfile.TemporaryDirectory() as temp:
            with patch("subprocess.run", side_effect=FileNotFoundError):
                with self.assertRaisesRegex(ValueError, "Graphviz"):
                    render_svg(graph_of({"A": []}), Path(temp) / "x.svg")

    def test_bad_renderer_output_is_not_saved(self):
        """Не-SVG ответ отрисовщика не сохраняется в файл."""
        response = subprocess.CompletedProcess([], 0, "not SVG", "")
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "graph.svg"
            with patch("subprocess.run", return_value=response):
                with self.assertRaisesRegex(ValueError, "SVG"):
                    render_svg(graph_of({"A": []}), path)
            self.assertFalse(path.exists())
