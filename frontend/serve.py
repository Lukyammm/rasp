"""
Servidor estático da interface (porta 8080).
Envia Cache-Control: no-cache para o Chrome sempre revalidar index.html/app.js — assim uma atualização do
RASP aparece imediatamente, sem precisar de Ctrl+F5 (arquivos inalterados continuam respondendo 304, rápido).
"""
import functools
import http.server
import os
import sys


class NoCacheHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def log_message(self, format, *args):  # silencioso (roda oculto)
        pass


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    handler = functools.partial(NoCacheHandler, directory=os.path.dirname(os.path.abspath(__file__)))
    with http.server.ThreadingHTTPServer(("127.0.0.1", port), handler) as httpd:
        httpd.serve_forever()
