"""
데스크톱 앱 런처.

Streamlit 서버를 백그라운드로 띄우고, 웹 브라우저 대신 PyWebView 의
'자체 앱 창(native window)'으로 대시보드를 표시한다.

실행:
    python desktop.py         # (가상환경의 python 권장)

창을 닫으면 Streamlit 서버도 함께 종료된다.
"""

from __future__ import annotations

import atexit
import socket
import subprocess
import sys
import time
from pathlib import Path

import webview  # pywebview

HERE = Path(__file__).resolve().parent
APP_PATH = HERE / "app.py"

WINDOW_TITLE = "서울시 자치구별 아파트 등락률 대시보드"


def _free_port() -> int:
    """비어 있는 로컬 포트 하나를 확보."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _wait_until_ready(port: int, timeout: float = 90.0) -> bool:
    """Streamlit 서버가 응답할 때까지 대기."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=1):
                return True
        except OSError:
            time.sleep(0.3)
    return False


def _start_streamlit(port: int) -> subprocess.Popen:
    """현재 파이썬(가상환경)으로 Streamlit 서버를 headless 실행."""
    cmd = [
        sys.executable, "-m", "streamlit", "run", str(APP_PATH),
        "--server.address", "127.0.0.1",
        "--server.port", str(port),
        "--server.headless", "true",          # 브라우저 자동 오픈 방지 (우리는 앱 창을 씀)
        "--browser.gatherUsageStats", "false",
        "--server.runOnSave", "false",
        "--global.developmentMode", "false",
    ]
    return subprocess.Popen(cmd, cwd=str(HERE))


def main() -> int:
    port = _free_port()
    proc = _start_streamlit(port)

    def _cleanup():
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except Exception:
                proc.kill()

    atexit.register(_cleanup)

    if not _wait_until_ready(port):
        _cleanup()
        print("❌ Streamlit 서버 시작에 실패했습니다.", file=sys.stderr)
        return 1

    # 네이티브 앱 창 생성 (브라우저 크롬 없음)
    webview.create_window(
        WINDOW_TITLE,
        f"http://127.0.0.1:{port}",
        width=1440,
        height=960,
        min_size=(1024, 720),
        resizable=True,
    )
    # 창이 닫힐 때까지 블록. (macOS: Cocoa/WKWebView)
    webview.start()

    # 창이 닫히면 서버 종료
    _cleanup()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
