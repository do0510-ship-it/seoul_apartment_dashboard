#!/bin/bash
###############################################################################
# 서울시 자치구별 아파트 등락률 대시보드 — 더블클릭 실행 (데스크톱 앱 창)
#
#   Finder 에서 더블클릭하면:
#     1) (최초 1회) 파이썬 가상환경 .venv 생성 + 라이브러리 설치
#     2) 웹 브라우저가 아니라 '자체 앱 창(PyWebView)' 으로 대시보드가 뜸
#
#   * 처음 열 때 "확인되지 않은 개발자" 경고 -> 오른쪽 클릭 → 열기 → 열기 (한 번만)
#   * 종료: 앱 창을 닫으면 됩니다. (이 터미널 창은 로그용)
###############################################################################

cd "$(dirname "$0")" || { echo "폴더 이동 실패"; read -n 1 -s -r; exit 1; }

echo "=================================================="
echo " 🏢 서울시 자치구별 아파트 등락률 대시보드"
echo "=================================================="

if ! command -v python3 >/dev/null 2>&1; then
  echo "❌ python3 가 설치되어 있지 않습니다. https://www.python.org 에서 설치 후 다시 실행하세요."
  read -n 1 -s -r -p "아무 키나 누르면 창이 닫힙니다..."
  exit 1
fi

# 최초 실행 시 가상환경 + 라이브러리 설치 (pywebview 포함)
if ! ./.venv/bin/python -c "import webview, streamlit" >/dev/null 2>&1; then
  echo "🔧 최초 실행: 파이썬 환경을 준비합니다 (몇 분 걸릴 수 있어요)..."
  python3 -m venv .venv || { echo "가상환경 생성 실패"; read -n 1 -s -r; exit 1; }
  ./.venv/bin/python -m pip install --quiet --upgrade pip
  ./.venv/bin/python -m pip install --quiet -r requirements-desktop.txt \
    || { echo "라이브러리 설치 실패"; read -n 1 -s -r; exit 1; }
  echo "✅ 준비 완료."
fi

echo ""
echo "🚀 데스크톱 앱 창을 띄웁니다. (창을 닫으면 종료됩니다)"
echo ""

exec ./.venv/bin/python desktop.py
