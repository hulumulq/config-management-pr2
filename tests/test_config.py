"""Проверки параметров первого этапа."""

import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from depsview.config import parse_args


class ConfigTest(unittest.TestCase):
    """Ошибки параметров обнаруживаются до обращения к NuGet."""

    def rejects(self, args):
        """Проверить понятный отказ argparse."""
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as error:
                parse_args(args)
        self.assertEqual(error.exception.code, 2)

    def test_defaults(self):
        """Обычный пакет получает явные воспроизводимые настройки."""
        cfg = parse_args(["--package", "Serilog"])
        self.assertEqual(cfg.package, "Serilog")
        self.assertEqual(cfg.framework, "net8.0")
        self.assertEqual(cfg.stage, 5)
        self.assertTrue(str(cfg.output).endswith(".svg"))

    def test_all_parameters(self):
        """Тестовый файл и режимы считываются без догадок."""
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "repo.json"
            path.write_text('{"A": []}', encoding="utf-8")
            cfg = parse_args([
                "--package", "A", "--repository", str(path), "--test",
                "--output", "diagram.svg", "--ascii", "--exclude", "SKIP",
                "--stage", "1", "--package-version", "1.2.3",
            ])
        self.assertTrue(cfg.test_mode)
        self.assertTrue(cfg.ascii_tree)
        self.assertEqual(cfg.exclude, "SKIP")
        self.assertEqual(cfg.package_version, "1.2.3")

    def test_invalid_package(self):
        """Пустое имя и разделители пути не являются именем пакета."""
        for value in ["", "../foo", "A B", "!bad"]:
            self.rejects(["--package", value])

    def test_invalid_repository(self):
        """Неизвестная схема и пароль в URL отвергаются."""
        for value in ["abc", "ftp://example.org", "https://u:p@host/a"]:
            self.rejects(["--package", "A", "--repository", value])

    def test_missing_test_file(self):
        """Режим теста требует существующий файл."""
        self.rejects(["--package", "A", "--repository", "/no/repo.json",
                      "--test"])

    def test_invalid_output(self):
        """Изображение должно быть SVG с доступной папкой."""
        for value in ["out.png", "/no/such/directory/out.svg"]:
            self.rejects(["--package", "A", "--output", value])

    def test_invalid_stage(self):
        """За пределами пяти этапов нет скрытого режима."""
        for value in ["0", "6", "wrong"]:
            self.rejects(["--package", "A", "--stage", value])

    def test_invalid_node_limit(self):
        """Проверены границы положительного лимита."""
        self.rejects(["--package", "A", "--max-nodes", "0"])
        self.assertEqual(parse_args([
            "--package", "A", "--max-nodes", "1"
        ]).max_nodes, 1)


if __name__ == "__main__":
    unittest.main()
