"""Операции над графом; все обходы выполняются без рекурсии."""

VISITING, FINISHED = 1, 2


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


def load_order(graph, root):
    """Постфиксный DFS: зависимости раньше пакета; для цикла отказ."""
    state, order = {root: VISITING}, []
    stack = [(root, iter(graph[root]))]
    while stack:
        node, children = stack[-1]
        child = next(children, None)
        if child is None:
            state[node] = FINISHED
            order.append(node)
            stack.pop()
        elif state.get(child) == VISITING:
            path = [item[0] for item in stack]
            cycle = path[path.index(child):] + [child]
            raise ValueError("Цикл: " + " -> ".join(map(str, cycle)))
        elif not state.get(child):
            state[child] = VISITING
            stack.append((child, iter(graph[child])))
    return order
