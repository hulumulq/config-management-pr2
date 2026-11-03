"""Полный CLI работает с HTTP-репозиторием, файлами и Graphviz."""

import http.server
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path

from http_support import MetadataHandler

ROOT = Path(__file__).resolve().parents[1]


def run_cli(*args):
    """Вызвать настоящий процесс приложения с отдельными аргументами."""
    env = dict(os.environ, PYTHONPATH=str(ROOT / "src"))
    return subprocess.run([sys.executable, str(ROOT / "src/main.py"),
                           *args], env=env, cwd=ROOT, capture_output=True,
                          text=True, timeout=15)


class CliTest(unittest.TestCase):
    """Проверки кодов выхода и конечного результата без сети NuGet."""

    def test_parameters_do_not_fetch_network(self):
        """На первом этапе параметры выводятся без обращения к сети."""
        result = run_cli("--package", "A", "--repository",
                         "http://127.0.0.1:1/index.json", "--stage", "1")
        self.assertEqual(result.returncode, 0)
        self.assertIn("package=A", result.stdout)

    def test_cycle_order_fails_clearly(self):
        """Для цикла сообщается, что порядка загрузки нет."""
        result = run_cli("--package", "A", "--test", "--repository",
                         "examples/cycle.json", "--stage", "4")
        self.assertEqual(result.returncode, 1)
        self.assertIn("Цикл", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_missing_file_fails_before_work(self):
        """Отсутствующий файл репозитория даёт понятную ошибку."""
        result = run_cli("--package", "A", "--test", "--repository",
                         "/missing/repository.json")
        self.assertEqual(result.returncode, 2)

    def test_malformed_json_is_not_traceback(self):
        """Битый JSON даёт сообщение об ошибке, а не трассировку."""
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "broken.json"
            path.write_text("not JSON")
            result = run_cli("--package", "A", "--test", "--repository",
                             str(path), "--stage", "2")
        self.assertEqual(result.returncode, 1)
        self.assertNotIn("Traceback", result.stderr)

    def test_http_nuspec_to_transitive_graph(self):
        """Динамический flat URL и XML проходят настоящий HTTP-слой."""
        with http.server.HTTPServer(
                ("127.0.0.1", 0), MetadataHandler) as server:
            thread = threading.Thread(target=server.serve_forever,
                                      daemon=True)
            thread.start()
            try:
                url = f"http://127.0.0.1:{server.server_port}/service.json"
                result = run_cli("--package", "A", "--repository", url,
                                 "--stage", "3")
            finally:
                server.shutdown()
                thread.join(timeout=2)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("A@1.0.0 -> B@1.0.0", result.stdout)
        self.assertIn("Вершин: 2", result.stdout)
