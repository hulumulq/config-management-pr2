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
        self.assertEqual(choose_version(["1.0", "2.0", "3.0-rc"]),
                         "2.0")

    def test_plain_version_means_minimum(self):
        versions = ["1.0", "1.2", "2.0"]
        self.assertEqual(choose_version(versions, "1.1"), "1.2")

    def test_exact_version(self):
        self.assertEqual(choose_version(["1.0", "2.0"], "[1.0]"),
                         "1.0")

    def test_exclusive_boundaries(self):
        versions = ["1.0", "1.1", "2.0"]
        self.assertEqual(choose_version(versions, "(1.0,2.0)"), "1.1")
        with self.assertRaises(ValueError):
            choose_version(["1.0", "2.0"], "(1.0,2.0)")

    def test_open_boundaries(self):
        self.assertEqual(choose_version(["1.0", "2.0"], "(,2.0]"),
                         "1.0")

    def test_floating_version(self):
        self.assertEqual(choose_version(["1.0", "1.9", "2.0"], "1.*"),
                         "1.9")

    def test_numeric_prerelease(self):
        self.assertLess(version_key("1.0-rc.2"),
                        version_key("1.0-rc.10"))
        self.assertLess(version_key("1.0-rc.10"), version_key("1.0"))

    def test_missing_version(self):
        with self.assertRaises(ValueError):
            choose_version(["1.0"], "[2.0]")

    def test_invalid_range(self):
        with self.assertRaises(ValueError):
            choose_version(["1.0"], "[bad]")


class NuGetTest(unittest.TestCase):
    """Клиент сам читает service index, список версий и XML nuspec."""

    def client(self, framework="net8.0", spec=SPEC):
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
        fetch = lambda url: responses[url].encode("utf-8")
        return NuGetRepository("https://repo/index.json", framework, fetch)

    def test_nearest_framework(self):
        repo = self.client()
        deps = repo.dependencies(repo.resolve("Root"))
        self.assertEqual([str(p) for p in deps], ["Modern@2.0.0"])

    def test_netstandard_fallback(self):
        repo = self.client("net6.0")
        deps = repo.dependencies(repo.resolve("Root"))
        self.assertEqual([str(p) for p in deps], ["Shared@1.0.0"])

    def test_incompatible_framework_is_not_empty_success(self):
        repo = self.client("netstandard1.0")
        with self.assertRaisesRegex(ValueError, "совместим"):
            repo.dependencies(repo.resolve("Root"))

    def test_package_without_dependencies(self):
        repo = self.client(spec="<package><metadata/></package>")
        self.assertEqual(repo.dependencies(repo.resolve("Root")), [])

    def test_ungrouped_dependencies(self):
        spec = ('<package><metadata><dependencies>'
                '<dependency id="Shared" version="[1.0.0]"/>'
                '</dependencies></metadata></package>')
        repo = self.client(spec=spec)
        self.assertEqual(str(repo.dependencies(repo.resolve("Root"))[0]),
                         "Shared@1.0.0")

    def test_invalid_xml(self):
        repo = self.client(spec="not XML")
        with self.assertRaises(ValueError):
            repo.dependencies(repo.resolve("Root"))


class TestFileTest(unittest.TestCase):
    """Тестовый репозиторий задаётся явным графом из JSON."""

    def test_reads_graph(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "repo.json"
            path.write_text('{"A":["B"],"B":[]}')
            repo = TestRepository(path)
            root = repo.resolve("A")
            self.assertEqual([str(n) for n in repo.dependencies(root)],
                             ["B"])

    def test_missing_node_is_an_error(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "repo.json"
            path.write_text('{"A":["B"]}')
            with self.assertRaisesRegex(ValueError, "B"):
                TestRepository(path)

    def test_invalid_names(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "repo.json"
            path.write_text('{"bad":[]}')
            with self.assertRaises(ValueError):
                TestRepository(path)
