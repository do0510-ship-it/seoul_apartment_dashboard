# 📘 서울 아파트 대시보드 — 운영 가이드북 (관리자용)

이 문서 하나로 **로컬에서 쓰는 법 + 외부에 공개하는 법 + 문제 해결**까지 다룹니다.
처음 인수받은 관리자도 이 문서만 보면 운영할 수 있게 정리했습니다.

- 프로젝트 폴더: **`~/seoul_apartment_dashboard`** (= `/Users/<사용자>/seoul_apartment_dashboard`)
- 데이터 출처: **국토교통부 아파트 매매 실거래가** (공공데이터포털 15126469)
- 단위: **만원/㎡** (전용면적 기준 평균 거래단가)

---

## 1. 한눈에 — 로컬 vs 외부 (가장 중요)

이 대시보드는 **두 가지 방식**으로 존재합니다. 헷갈리면 이 표만 기억하세요.

| 구분 | 🛠 **로컬 (관리자용)** | 🌐 **외부 (공개용)** |
|---|---|---|
| **무엇** | 내 Mac에서 창으로 뜨는 데스크톱 앱 | 인터넷에 올린 웹 사이트 |
| **누가 씀** | 관리자(나) 혼자 | 누구나 (외부 사용자) |
| **어떻게 열어** | `서울 아파트 대시보드 (관리자).app` **더블클릭** | 브라우저에서 **웹 URL 접속** |
| **어디서 돎** | 내 Mac 안에서만 (남은 못 봄) | 클라우드 서버 (모두가 같은 걸 봄) |
| **데이터 갱신** | 재수집 버튼 + **6시간마다 자동**(launchd) | **GitHub Actions가 매일 자동** |
| **인증키 필요?** | ✅ (`.env`) | ❌ (읽기 전용) |

> ⚠️ **핵심 오해 주의:** 로컬 `.app`을 남에게 줘도 그 사람은 내 데이터를 못 봅니다(각자 자기 Mac에서 자기 서버가 돎).
> **외부 공유는 오직 "웹 URL"로만** 됩니다. → [4. 외부 공개](#4-외부에-공개하기-streamlit-cloud)

---

## 2. 로컬에서 사용하기 (관리자)

### 2-1. 앱 열기

1. Finder에서 프로젝트 폴더(`~/seoul_apartment_dashboard`)를 엽니다.
2. **`서울 아파트 대시보드 (관리자).app`** 더블클릭 → 데스크톱 창이 뜹니다.
   - 처음 열 때 "확인되지 않은 개발자" 경고 → 앱 **오른쪽 클릭 → 열기 → 열기** (한 번만 허용)
   - **최초 1회**는 `run.command`를 먼저 더블클릭해 파이썬 환경(`.venv`)을 구성하세요. 이후엔 `.app`으로 바로 열립니다.
3. 종료: **창을 닫으면** 됩니다.

### 2-2. 화면 보는 법

- **지도**: 자치구 색 = **직전(완결) 월 대비 등락률**. 빨강=상승, 파랑=하락, 옅은색=보합, 회색=데이터 없음.
- **구 클릭 / 우측 셀렉트박스**: 팝업으로 일별·월별·년별 추이 그래프.
- **하단 총평**: 유독 튀는 구(급등/급락/역방향/변동성)를 자동으로 골라 "추정" 설명.
- **우측 상단 "🔄 실거래 재수집 후 새로고침"**: 지금 당장 국토부에서 다시 수집(약 1분).

### 2-3. 데이터가 갱신되는 3가지 경로 (로컬)

1. **수동 버튼** — 앱의 "🔄 실거래 재수집 후 새로고침" 클릭 → 즉시 재수집.
2. **자동(launchd)** — **매일 00·06·12·18시**에 백그라운드로 재수집 (앱을 안 켜도 됨).
3. **파일만 다시 읽기** — 앱은 `@st.cache_data(ttl=3600)` 라, 파일이 바뀌면 **최대 1시간 내** 자동 반영.
   (당장 반영하려면 재수집 버튼을 누르거나 앱을 다시 실행)

---

## 3. 자동 갱신 스케줄러 (launchd) 관리

매일 00·06·12·18시에 `fetch_data.py`가 자동 실행됩니다. 정의 파일: `scripts/com.local.seoul.apt.fetch.plist`.

```bash
# 상태 확인 (등록돼 있으면 한 줄 출력)
launchctl list | grep seoul

# 지금 즉시 한 번 실행(테스트) + 로그 실시간 보기
launchctl kickstart -k gui/$(id -u)/com.local.seoul.apt.fetch
tail -f ~/Library/Logs/seoul-apt-fetch.log     # 끝에 "완료 → ..." 나오면 성공

# 재설치(정의 바꿨을 때)
cp scripts/com.local.seoul.apt.fetch.plist ~/Library/LaunchAgents/
launchctl bootout   gui/$(id -u)/com.local.seoul.apt.fetch 2>/dev/null
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.local.seoul.apt.fetch.plist

# 중지·삭제
launchctl bootout gui/$(id -u)/com.local.seoul.apt.fetch
rm ~/Library/LaunchAgents/com.local.seoul.apt.fetch.plist
```

> ⚠️ **폴더 위치 규칙:** 프로젝트는 **`~/Documents`·`~/Desktop`·`~/Downloads` 밖**에 있어야 자동 실행이 됩니다.
> (macOS가 이 폴더들을 백그라운드 앱으로부터 보호 → `PermissionError` 발생) 그래서 `~/seoul_apartment_dashboard` 에 둡니다.
> 주기·시각을 바꾸려면 `scripts/…plist` 의 `StartCalendarInterval` 을 수정하고 위 "재설치"를 실행하세요.

---

## 4. 외부에 공개하기 (Streamlit Cloud)

외부 사용자는 **웹 URL**로 접속합니다. 무료로 공개하는 순서:

1. **GitHub에 올리기** (`.env`·인증키는 자동 제외됨)
   ```bash
   cd ~/seoul_apartment_dashboard
   git remote add origin https://github.com/<사용자명>/<저장소>.git
   git push -u origin main
   ```
   > 푸시 전 확인: `git status` 에 `.env` / `example.env.py` 가 **안 보여야** 정상.

2. **Streamlit Cloud 배포** — <https://share.streamlit.io> → GitHub 연결 → **New app** →
   저장소·브랜치 `main`·메인 파일 `app.py` 선택 → **Deploy** → 공개 URL 생성.

3. **데이터 자동 갱신 (GitHub Actions)** — 저장소 **Settings → Secrets and variables → Actions →
   New repository secret** 에 `MOLIT_API_KEY` = 공공데이터포털 인증키 등록.
   → 매일 자동 수집·커밋 → 앱 자동 재배포. (`.github/workflows/update-data.yml`)

> 외부 사용자에게는 **웹 URL 링크 하나만** 주면 됩니다. 폰/PC 어디서든 접속되고, 원하면 브라우저의
> "홈 화면에 추가 / 설치(PWA)"로 앱 아이콘처럼 쓸 수 있습니다. **읽기 전용**이라 갱신 버튼은 안 보입니다.

---

## 5. 인증키(.env) & 데이터 수집

- `fetch_data.py` 가 국토부 API로 실거래를 수집해 `data/apartment_data.json` 을 만듭니다.
- 인증키는 프로젝트 폴더의 **`.env`** 파일에서 읽습니다:
  ```
  MOLIT_API_KEY=<공공데이터포털 인증키>
  ```
- 수동 수집(터미널):
  ```bash
  cd ~/seoul_apartment_dashboard
  ./.venv/bin/python fetch_data.py            # 최근 24개월
  ./.venv/bin/python fetch_data.py --months 36
  ```

### 🔐 보안 (중요)
- **`.env` 와 `example.env.py` 는 절대 GitHub에 올리지 마세요.** (이미 `.gitignore` 로 제외됨)
- 외부(클라우드) 자동 갱신용 키는 **GitHub Secrets** 에만 넣습니다.
- 로컬 관리자 `.app` 에는 키가 들어있지 않고, 실행 시 프로젝트 `.env` 를 참조합니다.

---

## 6. 문제 해결 (FAQ)

| 증상 | 원인 / 해결 |
|---|---|
| 앱을 더블클릭해도 안 열림 | 최초 1회 `run.command` 로 `.venv` 구성. "확인되지 않은 개발자"면 **우클릭 → 열기 → 열기** |
| 앱에 **재수집 버튼이 안 보임** | 프로젝트 `.env`(인증키)가 없거나, `.app`을 프로젝트 폴더 밖으로 옮긴 경우 |
| 자동 갱신이 안 됨 | `launchctl list \| grep seoul` 확인. 로그 `~/Library/Logs/seoul-apt-fetch.log` 에 `PermissionError` 면 폴더가 `~/Documents` 안 → **밖으로 이동** 후 [3장](#3-자동-갱신-스케줄러-launchd-관리) 재설치 |
| 데이터가 안 바뀜 | 캐시 TTL(1시간) 때문. 재수집 버튼을 누르거나 앱 재실행 |
| 지도 색이 이상하게 극단적 | 특정 구 거래가 적어 변동성이 큰 것(총평이 이상치로 표시). 데이터 특성상 정상 |
| 수집했는데 `0/25` | 인증키 오류·활용신청 미승인·일일 한도 초과. 공공데이터포털에서 키 상태 확인 |
| "먼저 python fetch_data.py 실행" 화면 | `data/apartment_data.json` 이 없음 → 수집 1회 실행 |

---

## 7. 파일 구조 요약

```
~/seoul_apartment_dashboard/
├── app.py                         # 웹 앱 본체(화면·총평·갱신 버튼)
├── desktop.py                     # 데스크톱 창 런처(PyWebView)
├── data_loader.py                 # 데이터 읽기/이상치 탐지
├── fetch_data.py                  # 국토부 실거래 수집 → data/apartment_data.json
├── requirements.txt               # 웹/클라우드용(streamlit, plotly)
├── requirements-desktop.txt       # 로컬 데스크톱용(+pywebview)
├── requirements-data.txt          # 수집용(requests)
├── .env / .env.example            # 인증키 (.env 는 git 제외)
├── run.command                    # 로컬 실행(최초 .venv 자동 생성)
├── 서울 아파트 대시보드 (관리자).app  # 로컬 관리자 클릭 실행 앱 (git 제외)
├── scripts/…plist                 # 자동 갱신(launchd) 정의
├── .github/workflows/…yml         # 외부 배포 자동 갱신(GitHub Actions)
├── README.md / GUIDE.md           # 문서
└── data/
    ├── apartment_data.json        # 실거래 데이터(앱이 읽음)
    └── seoul_districts.geojson    # 자치구 경계
```

---

## 8. 자주 쓰는 명령 모음

```bash
cd ~/seoul_apartment_dashboard

# 로컬에서 열기(브라우저)
./.venv/bin/streamlit run app.py            # http://localhost:8501
# 로컬에서 열기(데스크톱 창)
./.venv/bin/python desktop.py

# 데이터 즉시 수집
./.venv/bin/python fetch_data.py

# 자동 갱신 상태/테스트
launchctl list | grep seoul
launchctl kickstart -k gui/$(id -u)/com.local.seoul.apt.fetch

# 외부 배포(최초 1회)
git push -u origin main                      # 이후 Streamlit Cloud에서 연결
```
