"""Tests for the local server supervisor."""
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

import pytest


class _HealthyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/api/health':
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"status":"ok","models_loaded":3}')
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, *_):
        pass


class _UnavailableHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(503)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(b'{"detail":"Model artifacts are unavailable. Missing model artifact: pima_model.pkl. Run python train_models.py."}')

    def log_message(self, *_):
        pass


class _Process:
    def __init__(self, returncode=None):
        self.returncode = returncode

    def poll(self):
        return self.returncode


@contextmanager
def _healthy_server():
    server = ThreadingHTTPServer(('127.0.0.1', 0), _HealthyHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f'http://127.0.0.1:{server.server_port}/api/health'
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


@contextmanager
def _unavailable_server():
    server = ThreadingHTTPServer(('127.0.0.1', 0), _UnavailableHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f'http://127.0.0.1:{server.server_port}/api/health'
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_wait_until_ready_returns_after_healthy_response():
    from app.launcher import wait_until_ready

    with _healthy_server() as url:
        wait_until_ready(url, _Process(), timeout_seconds=1, poll_interval=0.01)


def test_wait_until_ready_fails_when_server_exits():
    from app.launcher import wait_until_ready

    with pytest.raises(RuntimeError, match='exited with code 7'):
        wait_until_ready(
            'http://127.0.0.1:1/api/health',
            _Process(returncode=7),
            timeout_seconds=1,
            poll_interval=0.01,
        )


def test_wait_until_ready_times_out():
    from app.launcher import wait_until_ready

    with pytest.raises(TimeoutError, match='did not become ready'):
        wait_until_ready(
            'http://127.0.0.1:1/api/health',
            _Process(),
            timeout_seconds=0.05,
            poll_interval=0.01,
        )


def test_run_server_reuses_an_existing_healthy_instance(monkeypatch):
    from app import launcher

    def unexpected_spawn(*_args, **_kwargs):
        raise AssertionError('A second server must not be spawned on an occupied DiaWise port.')

    monkeypatch.setattr(launcher.subprocess, 'Popen', unexpected_spawn)
    with _healthy_server() as url:
        port = int(url.split(':')[2].split('/')[0])
        assert launcher.run_server(open_browser=False, port=port) == 0


def test_wait_until_ready_surfaces_terminal_artifact_failure():
    from app.launcher import wait_until_ready

    with _unavailable_server() as url:
        with pytest.raises(RuntimeError, match=r'pima_model\.pkl.*train_models\.py'):
            wait_until_ready(url, _Process(), timeout_seconds=1, poll_interval=0.01)


def test_spawned_server_disables_access_logging(monkeypatch):
    from app import launcher

    captured = []

    class FakeProcess:
        def poll(self):
            return 1

    monkeypatch.setattr(launcher, '_existing_instance_ready', lambda _url: False)
    monkeypatch.setattr(launcher, '_port_in_use', lambda _host, _port: False)
    monkeypatch.setattr(launcher.subprocess, 'Popen', lambda command: captured.extend(command) or FakeProcess())

    assert launcher.run_server(open_browser=False, port=8765) == 1
    assert '--no-access-log' in captured
