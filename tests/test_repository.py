"""Версии и прямые зависимости из настоящего формата NuGet."""

import json
import tempfile
import unittest
from pathlib import Path

from depsview.repository import NuGetRepository, TestRepository
from depsview.versions import choose_version, version_key

SPEC = '''<package
xmlns="http://schemas.microsoft.com/packaging/2013/05/nuspec.xsd">
<metadata><dependencies>
<group targetFramework=".NETFramework4.6.2">
 <dependency id="WindowsOnly" version="[1.0.0]"/>
</group>
<group targetFramework=".NETStandard2.0">
 <dependency id="Shared" version="[1.0,2.0)"/>
</group>
<group targetFramework="net8.0">
 <dependency id="Modern" version="2.0.0"/>
</group>
</dependencies></metadata></package>'''


class VersionsTest(unittest.TestCase):
    """Учитываются диапазоны и числовая часть prerelease."""

    def test_latest_root_is_stable(self):
        """Без указания версии выбирается последняя стабильная."""
        self.assertEqual(choose_version(["1.0", "2.0", "3.0-rc"]),
                         "2.0")

    def test_plain_version_means_minimum(self):
        """Обычная версия означает минимально допустимую."""
        versions = ["1.0", "1.2", "2.0"]
        self.assertEqual(choose_version(versions, "1.1"), "1.2")

    def test_exact_version(self):
        """Версия в квадратных скобках выбирается точно."""
        self.assertEqual(choose_version(["1.0", "2.0"], "[1.0]"),
                         "1.0")

    def test_exclusive_boundaries(self):
        """Круглые скобки исключают границы диапазона."""
        versions = ["1.0", "1.1", "2.0"]
        self.assertEqual(choose_version(versions, "(1.0,2.0)"), "1.1")
        with self.assertRaises(ValueError):
            choose_version(["1.0", "2.0"], "(1.0,2.0)")

    def test_open_boundaries(self):
        """Диапазон без нижней границы поддерживается."""
        self.assertEqual(choose_version(["1.0", "2.0"], "(,2.0]"),
                         "1.0")

    def test_floating_version(self):
        """Плавающая версия 1.* выбирает старшую из 1.x."""
        self.assertEqual(choose_version(["1.0", "1.9", "2.0"], "1.*"),
                         "1.9")

    def test_numeric_prerelease(self):
        """Числовые части предварительной версии сравниваются как числа."""
        self.assertLess(version_key("1.0-rc.2"),
                        version_key("1.0-rc.10"))
        self.assertLess(version_key("1.0-rc.10"), version_key("1.0"))

    def test_missing_version(self):
        """Отсутствие подходящей версии считается ошибкой."""
        with self.assertRaises(ValueError):
            choose_version(["1.0"], "[2.0]")

    def test_invalid_range(self):
        """Некорректная запись диапазона отклоняется."""
        with self.assertRaises(ValueError):
            choose_version(["1.0"], "[bad]")


class NuGetTest(unittest.TestCase):
    """Клиент сам читает service index, список версий и XML nuspec."""

    def client(self, framework="net8.0", spec=SPEC):
        """Создать клиент NuGet с подставными ответами сервера."""
        responses = {
            "https://repo/index.json": json.dumps({"resources": [{
                "@type": "PackageBaseAddress/3.0.0",
                "@id": "https://cdn/flat/",
            }]}),
            "https://cdn/flat/root/index.json": '{"versions":["1.0.0"]}',
            "https://cdn/flat/root/1.0.0/root.nuspec": spec,
            "https://cdn/flat/modern/index.json":
                '{"versions":["2.0.0","3.0.0"]}',
            "https://cdn/flat/shared/index.json":
                '{"versions":["1.0.0","1.9.0","2.0.0"]}',
        }

        def fetch(url):
            """Вернуть подставной ответ сервера."""
            return responses[url].encode("utf-8")

        return NuGetRepository("https://repo/index.json", framework, fetch)

    def test_nearest_framework(self):
        """Выбирается ближайшая совместимая платформа."""
        repo = self.client()
        deps = repo.dependencies(repo.resolve("Root"))
        self.assertEqual([str(p) for p in deps], ["Modern@2.0.0"])

    def test_netstandard_fallback(self):
        """Для старой платформы берётся группа netstandard."""
        repo = self.client("net6.0")
        deps = repo.dependencies(repo.resolve("Root"))
        self.assertEqual([str(p) for p in deps], ["Shared@1.0.0"])

    def test_incompatible_framework_is_not_empty_success(self):
        """Несовместимая платформа даёт ошибку, а не пустой список."""
        repo = self.client("netstandard1.0")
        with self.assertRaisesRegex(ValueError, "совместим"):
            repo.dependencies(repo.resolve("Root"))

    def test_package_without_dependencies(self):
        """Пакет без зависимостей даёт пустой список."""
        repo = self.client(spec="<package><metadata/></package>")
        self.assertEqual(repo.dependencies(repo.resolve("Root")), [])

    def test_ungrouped_dependencies(self):
        """Зависимости без групп по платформам тоже читаются."""
        spec = ('<package><metadata><dependencies>'
                '<dependency id="Shared" version="[1.0.0]"/>'
                '</dependencies></metadata></package>')
        repo = self.client(spec=spec)
        self.assertEqual(str(repo.dependencies(repo.resolve("Root"))[0]),
                         "Shared@1.0.0")

    def test_invalid_xml(self):
        """Некорректный XML nuspec даёт понятную ошибку."""
        repo = self.client(spec="not XML")
        with self.assertRaises(ValueError):
            repo.dependencies(repo.resolve("Root"))

    def test_html_is_not_a_nuspec(self):
        """HTML-страница не принимается за nuspec."""
        repo = self.client(spec="<html><body>Error</body></html>")
        with self.assertRaisesRegex(ValueError, "nuspec"):
            repo.dependencies(repo.resolve("Root"))

    def test_invalid_index_structure(self):
        """Неверная структура индекса сервиса отклоняется."""
        for data in [b"[]", b'{"resources":["bad"]}']:
            with self.assertRaises(ValueError):
                NuGetRepository("https://repo/index.json",
                                fetch=lambda url: data)


class TestFileTest(unittest.TestCase):
    """Тестовый репозиторий задаётся явным графом из JSON."""

    def test_reads_graph(self):
        """Тестовый репозиторий читается из JSON-файла."""
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "repo.json"
            path.write_text('{"A":["B"],"B":[]}')
            repo = TestRepository(path)
            root = repo.resolve("A")
            self.assertEqual([str(n) for n in repo.dependencies(root)],
                             ["B"])

    def test_missing_node_is_an_error(self):
        """Ссылка на неописанный пакет считается ошибкой."""
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "repo.json"
            path.write_text('{"A":["B"]}')
            with self.assertRaisesRegex(ValueError, "B"):
                TestRepository(path)

    def test_invalid_names(self):
        """Имена не из больших латинских букв отклоняются."""
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "repo.json"
            path.write_text('{"bad":[]}')
            with self.assertRaises(ValueError):
                TestRepository(path)
