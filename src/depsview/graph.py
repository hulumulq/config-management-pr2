"""Операции над графом; все обходы выполняются без рекурсии."""


def build_graph(repository, root, exclude="", max_nodes=200):
    """Обойти зависимости DFS со стеком и сохранить циклические рёбра."""
    blocked = exclude.lower()
    if blocked and blocked in root.name.lower():
        raise ValueError("Корневой пакет исключён фильтром")
    graph, stack = {}, [root]
    while stack:
        node = stack.pop()
        if node in graph:
            continue
        if len(graph) >= max_nodes:
            raise ValueError(f"Лимит {max_nodes} вершин превышен")
        children = [child for child in repository.dependencies(node)
                    if not blocked or blocked not in child.name.lower()]
        graph[node] = sorted(dict.fromkeys(children), key=str)
        stack.extend(reversed(graph[node]))
    return graph
