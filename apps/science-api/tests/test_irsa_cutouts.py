from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Event, Thread

import httpx
import pytest
import socket

from app.clients.irsa import (
    IrsaResponseError,
    IrsaTimeoutError,
    IrsaUnavailableError,
)
from app.clients.irsa_cutouts import (
    _fetch_cutout,
    download_irsa_cutout,
)


class CutoutHandler(BaseHTTPRequestHandler):
    """Servidor HTTP de prueba con respuestas controladas."""

    protocol_version = "HTTP/1.1"

    def log_message(self, format, *args):
        pass

    def do_GET(self):
        if self.path == "/slow":
            self.send_response(200)
            self.send_header("Content-Length", "10")
            self.end_headers()
            self.wfile.flush()

            # El cliente agotará su espera antes de recibir el cuerpo.
            Event().wait(0.5)
            self.close_connection = True
            return

        if self.path == "/truncated":
            self.send_response(200)
            self.send_header("Content-Length", "100")
            self.end_headers()
            self.wfile.write(b"short")
            self.wfile.flush()
            self.close_connection = True
            return

        responses = {
            "/ok": (200, b"example-content"),
            "/error": (503, b"external-error"),
            "/empty": (200, b""),
            "/large": (200, b"x" * 1024),
            "/redirect": (302, b""),
        }

        status, content = responses[self.path]

        self.send_response(status)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)


@pytest.fixture
def servidor():
    server = ThreadingHTTPServer(
        ("127.0.0.1", 0),
        CutoutHandler,
    )
    server.daemon_threads = True

    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()

    host, port = server.server_address

    try:
        yield f"http://{host}:{port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def descargar(url, *, max_bytes=4096, read_timeout=2.0):
    return _fetch_cutout(
        url=url,
        params={},
        timeout=httpx.Timeout(
            connect=2.0,
            read=read_timeout,
            write=2.0,
            pool=2.0,
        ),
        max_bytes=max_bytes,
    )


def test_descarga_correcta(servidor):
    assert descargar(f"{servidor}/ok") == b"example-content"


@pytest.mark.parametrize("path", ["/error", "/empty", "/redirect"])
def test_rechaza_respuesta_fallida_o_vacia(servidor, path):
    with pytest.raises(IrsaResponseError):
        descargar(f"{servidor}{path}")


def test_limite_de_tamano(servidor):
    with pytest.raises(IrsaResponseError, match="tamaño permitido"):
        descargar(f"{servidor}/large", max_bytes=100)


def test_descarga_incompleta(servidor):
    with pytest.raises(IrsaUnavailableError):
        descargar(f"{servidor}/truncated")


def test_timeout_durante_descarga(servidor):
    with pytest.raises(IrsaTimeoutError):
        descargar(
            f"{servidor}/slow",
            read_timeout=0.1,
        )


@pytest.mark.parametrize(
    "url",
    [
        "http://irsa.ipac.caltech.edu/ibe/data/spherex/test.fits",
        "https://example.org/ibe/data/spherex/test.fits",
        "https://irsa.ipac.caltech.edu/otro/test.fits",
        "https://irsa.ipac.caltech.edu/ibe/data/spherex/test.txt",
        "https://irsa.ipac.caltech.edu/ibe/data/spherex/test.fits?x=1",
        "https://irsa.ipac.caltech.edu/ibe/data/spherex/test.fits#fragment",
        "https://[irsa.ipac.caltech.edu/ibe/data/spherex/test.fits",
    ],
)
def test_rechaza_url_no_permitida(url):
    with pytest.raises(IrsaResponseError, match="URL del producto"):
     download_irsa_cutout(url, ra=210.8, dec=54.3)

@pytest.fixture
def servidor_error_contado():
    """Servidor local que cuenta solicitudes y devuelve un error HTTP."""
    state = {"status": 503, "requests": 0}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            pass

        def do_GET(self):
            state["requests"] += 1
            content = b"external-error"

            self.send_response(state["status"])
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.daemon_threads = True

    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()

    host, port = server.server_address

    try:
        yield f"http://{host}:{port}/cutout", state
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


@pytest.mark.parametrize(
    "status",
    [400, 401, 403, 404, 429, 500, 502, 503, 504],
)
def test_recorte_no_reintenta_respuestas_http_fallidas(
    servidor_error_contado,
    status,
):
    url, state = servidor_error_contado
    state["status"] = status

    with pytest.raises(IrsaResponseError):
        descargar(url)

    assert state["requests"] == 1

def test_recorte_controla_conexion_rechazada():
    """Una conexión rechazada debe convertirse en un error del backend."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as reserved:
        reserved.bind(("127.0.0.1", 0))
        host, port = reserved.getsockname()

    # Windows puede tardar más de dos segundos en comunicar el rechazo.
    # Usamos el timeout de conexión predeterminado del cliente real.
    with pytest.raises(IrsaUnavailableError):
        _fetch_cutout(
            url=f"http://{host}:{port}/cutout",
            params={},
            timeout=httpx.Timeout(
                connect=10.0,
                read=2.0,
                write=2.0,
                pool=2.0,
            ),
            max_bytes=4096,
        )

@pytest.fixture
def servidor_con_cierre():
    """Detecta cuándo termina la conexión atendida por el servidor."""
    connection_finished = Event()

    class Handler(CutoutHandler):
        def finish(self):
            try:
                super().finish()
            finally:
                connection_finished.set()

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.daemon_threads = True

    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()

    host, port = server.server_address

    try:
        yield f"http://{host}:{port}", connection_finished
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


@pytest.mark.parametrize(
    ("path", "max_bytes", "expected_error"),
    [
        ("/ok", 4096, None),
        ("/error", 4096, IrsaResponseError),
        ("/empty", 4096, IrsaResponseError),
        ("/large", 100, IrsaResponseError),
    ],
)
def test_recorte_cierra_conexion(
    servidor_con_cierre,
    path,
    max_bytes,
    expected_error,
):
    base_url, connection_finished = servidor_con_cierre

    if expected_error is None:
        content = descargar(
            f"{base_url}{path}",
            max_bytes=max_bytes,
        )
        assert content == b"example-content"
    else:
        with pytest.raises(expected_error):
            descargar(
                f"{base_url}{path}",
                max_bytes=max_bytes,
            )

    assert connection_finished.wait(timeout=2.0), (
        "El servidor no detectó el cierre de la conexión"
    )