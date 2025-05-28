import contextlib
import io
import os
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import socket

from fezcompile import precompile_module


class RequestHandler(SimpleHTTPRequestHandler):
    CACHED_MODULES: dict[str, bytes] = {}

    def do_GET(self):
        """Serve a GET request."""
        f = self.send_head()
        if f:
            try:
                if ".py?" in self.path:
                    content = f.read().decode()
                    content = precompile_module(content)
                    f = io.BytesIO()
                    f.write(content.encode())
                    f.seek(0)

                self.copyfile(f, self.wfile)
            finally:
                f.close()


def _get_best_family(*address):
    infos = socket.getaddrinfo(
        *address,
        type=socket.SOCK_STREAM,
        flags=socket.AI_PASSIVE,
    )
    family, type, proto, canonname, sockaddr = next(iter(infos))
    return family, sockaddr


def test(HandlerClass, ServerClass, protocol="HTTP/1.0", port=8000, bind=None):
    """Test the HTTP request handler class.

    This runs an HTTP server on port 8000 (or the port argument).

    """
    ServerClass.address_family, addr = _get_best_family(bind, port)
    HandlerClass.protocol_version = protocol
    with ServerClass(addr, HandlerClass) as httpd:
        host, port = httpd.socket.getsockname()[:2]
        url_host = f"[{host}]" if ":" in host else host
        print(f"Serving HTTP on {host} port {port} " f"(http://{url_host}:{port}/) ...")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nKeyboard interrupt received, exiting.")
            sys.exit(0)


if __name__ == "__main__":

    # ensure dual-stack is not disabled; ref #38907
    class DualStackServer(ThreadingHTTPServer):

        def server_bind(self):
            # suppress exception when protocol is IPv4
            with contextlib.suppress(Exception):
                self.socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
            return super().server_bind()

        def finish_request(self, request, client_address):
            self.RequestHandlerClass(
                request,
                client_address,
                self,
                directory=os.getcwd(),
            )

    test(RequestHandler, DualStackServer)
