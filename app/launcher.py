"""Start DiaWise, wait for model readiness, then open the local UI."""
from __future__ import annotations

import json
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from typing import Protocol


class ProcessState(Protocol):
    def poll(self) -> int | None: ...


def wait_until_ready(
    url: str,
    process: ProcessState,
    timeout_seconds: float,
    poll_interval: float = 0.1,
) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        returncode = process.poll()
        if returncode is not None:
            raise RuntimeError(f'DiaWise server exited with code {returncode} before becoming ready.')
        try:
            remaining = max(0.05, deadline - time.monotonic())
            with urllib.request.urlopen(url, timeout=min(1.0, remaining)) as response:
                body = json.load(response)
                if response.status == 200 and body.get('status') == 'ok' and body.get('models_loaded') == 3:
                    return
        except urllib.error.HTTPError as exc:
            if exc.code == 503:
                try:
                    body = json.load(exc)
                    detail = body.get('detail', '') if isinstance(body, dict) else ''
                except (OSError, ValueError):
                    detail = ''
                raise RuntimeError(detail or 'DiaWise reported that its model artifacts are unavailable.') from exc
        except (OSError, ValueError, urllib.error.URLError):
            pass
        time.sleep(poll_interval)
    raise TimeoutError(f'DiaWise did not become ready within {timeout_seconds:g} seconds.')


def _existing_instance_ready(health_url: str) -> bool:
    try:
        with urllib.request.urlopen(health_url, timeout=0.5) as response:
            body = json.load(response)
            return response.status == 200 and body.get('status') == 'ok' and body.get('models_loaded') == 3
    except (OSError, ValueError, urllib.error.URLError):
        return False


def _port_in_use(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.settimeout(0.5)
        return probe.connect_ex((host, port)) == 0


def run_server(open_browser: bool = True, host: str = '127.0.0.1', port: int = 8000) -> int:
    base_url = f'http://{host}:{port}'
    health_url = f'{base_url}/api/health'
    if _existing_instance_ready(health_url):
        print(f'DiaWise is already running: {base_url}', flush=True)
        if open_browser:
            webbrowser.open(base_url)
        return 0
    if _port_in_use(host, port):
        print(f'Startup failed: port {port} is already used by another application.', file=sys.stderr, flush=True)
        return 1
    process = subprocess.Popen([
        sys.executable, '-m', 'uvicorn', 'app.main:app',
        '--host', host, '--port', str(port),
    ])
    try:
        wait_until_ready(health_url, process, timeout_seconds=45)
        time.sleep(0.05)
        if process.poll() is not None:
            raise RuntimeError(f'DiaWise server exited with code {process.poll()} after readiness check.')
        print(f'DiaWise is ready: {base_url}', flush=True)
        if open_browser:
            webbrowser.open(base_url)
        return process.wait()
    except KeyboardInterrupt:
        print('\nStopping DiaWise...', flush=True)
        return 0
    except (RuntimeError, TimeoutError) as exc:
        print(f'Startup failed: {exc}', file=sys.stderr, flush=True)
        return 1
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


if __name__ == '__main__':
    raise SystemExit(run_server())
