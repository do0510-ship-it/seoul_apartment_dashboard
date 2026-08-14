#!/bin/bash
# 로컬(한국)에서 국토부 실거래를 수집한 뒤, 데이터가 바뀌었으면 GitHub 에 push.
# -> 그러면 Streamlit Cloud(외부 웹앱)가 자동으로 최신 데이터로 재배포된다.
#    (해외 GitHub 서버는 한국 API에 접속이 안 되므로, 수집은 반드시 로컬에서 한다.)

set -o pipefail
cd "$(dirname "$0")/.." || exit 1        # scripts/ 의 부모 = 프로젝트 루트
PROJECT="$(pwd)"

echo "===== $(date '+%Y-%m-%d %H:%M:%S') 수집 시작 ====="

# 1) 실거래 수집 (로컬 .venv 파이썬, .env 인증키 사용)
"$PROJECT/.venv/bin/python" "$PROJECT/fetch_data.py" --months 24 || { echo "수집 실패"; exit 1; }

# 2) 데이터가 바뀐 경우에만 커밋 + push
if git diff --quiet -- data/apartment_data.json; then
  echo "데이터 변경 없음 - push 생략."
  exit 0
fi

git add data/apartment_data.json
git commit -m "data: 실거래 자동 갱신 ($(date '+%Y-%m-%d %H:%M'))" || { echo "커밋 실패"; exit 1; }

if git push origin main; then
  echo "✅ push 완료 - 웹앱이 곧 자동 갱신됩니다."
else
  echo "❌ push 실패 - GitHub 인증(토큰) 설정을 확인하세요."
  exit 1
fi
