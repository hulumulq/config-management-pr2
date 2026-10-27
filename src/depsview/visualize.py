"""Визуализация Graphviz и читаемое дерево без рекурсии."""

import json
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path


def to_dot(graph, root=None):
    """Сформировать безопасно экранированный текст DOT."""
    lines = ["digraph Dependencies {",
             '  graph [rankdir=LR, bgcolor="#fcfaf6", pad=0.3];',
             '  node [shape=box, style="rounded,filled",',
             '        fillcolor="#e3e9e4", fontname="Arial"];',
             '  edge [color="#64756b"];']
    names = {node: str(node) for node in graph}
    quote = lambda node: json.dumps(names[node], ensure_ascii=False)
    for node, children in graph.items():
        style = ' [fillcolor="#ffc78c"]' if node == root else ""
        lines.append(f"  {quote(node)}{style};")
        for child in children:
            lines.append(f"  {quote(node)} -> {quote(child)};")
    return "\n".join(lines + ["}", ""])


def ascii_tree(graph, root):
    """Отличить цикл в текущем пути от общей повторной зависимости."""
    lines, expanded = [str(root)], {root}
    stack = [(node, "", index == len(graph[root]) - 1, frozenset([root]))
             for index, node in reversed(list(enumerate(graph[root])))]
    while stack:
        node, prefix, last, path = stack.pop()
        cycle, repeated = node in path, node in expanded
        mark = " [цикл]" if cycle else " [повтор]" if repeated else ""
        lines.append(prefix + ("`-- " if last else "|-- ") + str(node)
                     + mark)
        if cycle or repeated:
            continue
        expanded.add(node)
        branch = prefix + ("    " if last else "|   ")
        children = graph[node]
        stack.extend((child, branch, index == len(children) - 1,
                      path | {node}) for index, child in
                     reversed(list(enumerate(children))))
    return "\n".join(lines)


def render_svg(graph, output, root=None):
    """Построить настоящий SVG; ошибочный ответ не выдаётся за рисунок."""
    source = to_dot(graph, root)
    try:
        response = subprocess.run(["dot", "-Tsvg"], input=source,
                                  capture_output=True, text=True,
                                  timeout=30, check=True)
    except FileNotFoundError as error:
        raise ValueError("Не найден Graphviz: установи команду dot") from error
    except (subprocess.SubprocessError, OSError) as error:
        raise ValueError(f"Graphviz не построил SVG: {error}") from error
    try:
        svg = ET.fromstring(response.stdout)
    except ET.ParseError as error:
        raise ValueError("Graphviz вернул некорректный SVG") from error
    if not svg.tag.endswith("svg"):
        raise ValueError("Graphviz вернул другой формат вместо SVG")
    output = Path(output)
    output.with_suffix(".dot").write_text(source, encoding="utf-8")
    output.write_text(response.stdout, encoding="utf-8")
