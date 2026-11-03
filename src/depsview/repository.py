"""Чтение NuGet V3 и локального тестового графа стандартной библиотекой."""

import json
import re
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

from depsview.frameworks import compatibility
from depsview.versions import choose_version

MAX_RESPONSE = 8 * 1024 * 1024


@dataclass(frozen=True, eq=False)
class Package:
    """Вершина графа: имя и точная версия пакета."""

    name: str
    version: str = ""

    def __str__(self):
        """Вернуть имя пакета с версией через @."""
        return self.name + ("@" + self.version if self.version else "")

    def __hash__(self):
        """Хешировать имя и версию без учёта регистра."""
        return hash((self.name.lower(), self.version.lower()))

    def __eq__(self, other):
        """Сравнить пакеты по имени и версии без учёта регистра."""
        return (isinstance(other, Package)
                and self.name.lower() == other.name.lower()
                and self.version.lower() == other.version.lower())


def read_url(url):
    """Загрузить ограниченный объём метаданных, сохраняя проверку TLS."""
    request = urllib.request.Request(url, headers={
        "User-Agent": "config-management-pr2/1.0",
    })
    try:
        with urllib.request.urlopen(request, timeout=25) as response:
            data = response.read(MAX_RESPONSE + 1)
    except urllib.error.URLError as error:
        raise ValueError(f"Не удалось прочитать репозиторий: {error}")
    if len(data) > MAX_RESPONSE:
        raise ValueError("Ответ репозитория превышает 8 МБ")
    return data


def dependencies_xml(data, framework):
    """Прочитать XML и выбрать одну ближайшую совместимую TFM-группу."""
    try:
        root = ET.fromstring(data)
    except ET.ParseError as error:
        raise ValueError("Некорректный XML nuspec") from error
    for element in root.iter():
        element.tag = element.tag.rsplit("}", 1)[-1]
    if root.tag != "package" or root.find("metadata") is None:
        raise ValueError("Ответ не является документом nuspec")
    container = root.find("metadata/dependencies")
    if container is None:
        return []
    selected = list(container.findall("dependency"))
    groups = container.findall("group")
    if groups:
        selected += _select_group(groups, framework).findall("dependency")
    return [(node.attrib["id"], node.get("version") or "(,)")
            for node in selected]


def _select_group(groups, framework):
    """Выбрать только одну группу с максимальным рангом совместимости."""
    eligible = [(compatibility(g.get("targetFramework", ""), framework), g)
                for g in groups]
    eligible = [(score, group) for score, group in eligible
                if score is not None]
    if not eligible:
        raise ValueError(f"Нет совместимой группы зависимостей: {framework}")
    return max(eligible, key=lambda item: item[0])[1]


def _service_base(data):
    """Проверить структуру service index и найти flat container."""
    index = json.loads(data)
    if not isinstance(index, dict):
        raise ValueError("Service index должен быть JSON-объектом")
    resources = index.get("resources")
    if not isinstance(resources, list):
        raise ValueError("В service index нет списка resources")
    for resource in resources:
        if not isinstance(resource, dict):
            continue
        if resource.get("@type") != "PackageBaseAddress/3.0.0":
            continue
        base = resource.get("@id")
        if isinstance(base, str) and base.startswith(("http://", "https://")):
            return base.rstrip("/")
    raise ValueError("В service index нет PackageBaseAddress")


class NuGetRepository:
    """Динамически найти PackageBaseAddress, затем читать .nuspec."""

    def __init__(self, url, framework="net8.0", fetch=read_url):
        """Запомнить адрес источника NuGet и целевую платформу."""
        self.fetch, self.framework = fetch, framework
        self.base = _service_base(fetch(url))
        self.versions_cache, self.dependencies_cache = {}, {}

    def resolve(self, name, requirement=""):
        """Подобрать версию по списку из flat container."""
        key = name.lower()
        if key not in self.versions_cache:
            url = f"{self.base}/{key}/index.json"
            self.versions_cache[key] = json.loads(self.fetch(url))["versions"]
        version = choose_version(self.versions_cache[key], requirement)
        return Package(name, version)

    def dependencies(self, package):
        """Вернуть прямые зависимости одной версии и целевой платформы."""
        if package not in self.dependencies_cache:
            name, version = package.name.lower(), package.version.lower()
            url = f"{self.base}/{name}/{version}/{name}.nuspec"
            raw = dependencies_xml(self.fetch(url), self.framework)
            self.dependencies_cache[package] = [
                self.resolve(name, version) for name, version in raw
            ]
        return self.dependencies_cache[package]


class TestRepository:
    """Граф {A: [B, C], B: [], C: []}; циклы допускаются."""

    def __init__(self, path):
        """Прочитать JSON-описание тестового репозитория."""
        self.data = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(self.data, dict) or not self.data:
            raise ValueError("Тестовый граф должен быть непустым объектом")
        for name, dependencies in self.data.items():
            if not re.fullmatch(r"[A-Z]+", name):
                raise ValueError("Имена тестовых пакетов: большие A–Z")
            if not isinstance(dependencies, list):
                raise ValueError(f"Зависимости {name} должны быть списком")
            for dependency in dependencies:
                if (not isinstance(dependency, str)
                        or dependency not in self.data):
                    raise ValueError(f"Не описана зависимость {dependency}")

    def resolve(self, name, requirement=""):
        """Проверить наличие корневого пакета."""
        if name not in self.data:
            raise ValueError(f"Пакета {name} нет в тестовом репозитории")
        return Package(name)

    def dependencies(self, package):
        """Получить рёбра из явно заданного файла."""
        return [Package(name) for name in self.data[package.name]]
