"""Миниатюрный NuGet V3 по HTTP для интеграционного теста."""

import http.server
import json


class MetadataHandler(http.server.BaseHTTPRequestHandler):
    """Выдать индекс и два пакета A -> B на случайном локальном порту."""

    def do_GET(self):
        """Обработать один запрос метаданных без внешней сети."""
        base = f"http://127.0.0.1:{self.server.server_port}/custom/"
        responses = {
            "/service.json": json.dumps({"resources": [{
                "@type": "PackageBaseAddress/3.0.0", "@id": base,
            }]}),
            "/custom/a/index.json": '{"versions":["1.0.0"]}',
            "/custom/b/index.json": '{"versions":["1.0.0"]}',
            "/custom/a/1.0.0/a.nuspec": (
                '<package><metadata><dependencies>'
                '<dependency id="B" version="[1.0.0]"/>'
                '</dependencies></metadata></package>'),
            "/custom/b/1.0.0/b.nuspec": "<package><metadata/></package>",
        }
        self.send_response(200 if self.path in responses else 404)
        self.end_headers()
        self.wfile.write(responses.get(self.path, "").encode())

    def log_message(self, *args):
        """Не засорять журнал тестов служебным HTTP-выводом."""
