# 🏢 서울시 자치구별 아파트 등락률 대시보드

서울시 25개 자치구의 **아파트** 실거래 등락률을 지도 위에서 한눈에 보여주는 Streamlit 앱입니다.
지도를 구 단위로 색칠하고, 구를 클릭하면 등락률 추이 그래프가 팝업으로 뜨며, 하단에 이상 징후 총평을 자동 생성합니다.

> 데이터는 **`fetch_data.py`가 생성한 `data/apartment_data.json`** (국토교통부 실거래가 등)을 읽습니다.
> 화면(app.py)과 데이터가 분리되어 있어, 같은 형식의 파일만 있으면 화면 코드는 수정할 필요가 없습니다.

## 통계 대상

- 포함: **아파트(APT)만**
- 제외: 단독주택, 다세대 / 연립 등 그 외 주택 유형
- 지도 색칠 기준: **직전(완결) 월 대비 아파트 등락률(%)** (`latest_change_pct`)
  - 일별 실거래는 하루 1~2건뿐이라 평균단가가 크게 요동치므로, 대표 등락률은 **진행 중인 이번 달을 제외한
    마지막 완결 월의 전월 대비 변동률**로 계산합니다(안정적·의미 있는 값). 일별 그래프는 참고용입니다.
- 평균 거래단가 단위: **만원/㎡ (전용면적 기준 평균 거래단가)**

## 주요 기능

- **지도 대시보드**: 서울시 25개 자치구를 개별 영역으로 그리고, `latest_change_pct` 에 따라 색칠
  - 상승 → 빨강(진할수록 큰 상승), 하락 → 파랑(진할수록 큰 하락), 0% 근처 → 옅은 색
  - 0을 중심으로 하는 연속 diverging 스케일(`RdBu_r`, `zmid=0`, 대칭 범위) + 색상 범례(colorbar)
  - 각 구에 이름 + 등락률 라벨, 호버 시 평균 거래단가까지 표시
  - **`latest_change_pct` 가 `null`(거래 없음/부족)인 구는 회색으로 칠하고 라벨에 "데이터 없음"** 표기 (에러 없이 처리)
- **구 클릭 팝업(`st.dialog`)**: 지도에서 구를 클릭하면 해당 구의 추이 그래프가 모달로 표시
  - **일별 / 월별 / 년별** 탭 전환 — 각각 `daily` / `monthly` / `yearly` 배열의 `pct` 를 그래프로 표시
  - x축: 일별=`date`, 월별=`period(YYYY-MM)`, 년별=`period(YYYY)`
  - 일별은 라인, 월별·년별은 막대 (상승=빨강 / 하락=파랑). `pct` 가 `null` 인 시작점은 자연스러운 끊김(gap)으로 처리
  - 툴팁에 평균 거래단가(만원/㎡)와 거래건수 함께 표시
  - 팝업 상단에 구 이름, `latest_change_pct`, `latest_date` + 닫기 버튼
  - 지도 클릭이 어려운 환경을 위해 우측 셀렉트박스로도 팝업을 열 수 있음
- **하단 총평(이상 징후 자동 분석)**: 전체 평균이 아니라 *일반적이지 않은 상황*을 통계로 자동 탐지
  - `spike` 이례적 급등 / `plunge` 이례적 급락 (전 자치구 `latest_change_pct` 분포 대비 z-score)
  - `contrarian` 시장 다수 방향(중앙값 부호)과 반대로 이동
  - `volatile` 월별 `pct` 의 표준편차(변동성)가 비정상적으로 큼
  - 각 항목마다 "어느 구 / 어떤 현상 / **추정** 원인"을 서술 (데이터만으로 단정하지 않고 '추정'임을 명시)
  - `latest_change_pct` 가 `null` 인 구는 평균·총평 계산에서 **제외**

## 데이터 준비 — `fetch_data.py`

앱은 `data/apartment_data.json` 을 읽습니다. 파일이 없으면 화면에 안내가 뜨며, 아래로 먼저 생성합니다.

```bash
python fetch_data.py
```

> `fetch_data.py` 는 국토교통부 실거래가 등에서 아파트 거래를 수집·집계해 아래 [데이터 형식](#데이터-형식-스키마)의
> JSON을 생성합니다. (본 저장소에는 동일 형식의 **샘플/테스트 데이터**가 들어 있어 바로 실행해 볼 수 있으며,
> `fetch_data.py` 를 실행하면 실제 데이터로 덮어써집니다.)

## 실행 방법

> 💡 **웹 브라우저가 아니라, 자체 데스크톱 앱 창(native window)으로 뜹니다.**
> 기존 Streamlit UI를 그대로 유지하되 **PyWebView**(macOS: WKWebView/Cocoa)로 감싸서, 주소창·탭 같은
> 브라우저 크롬 없이 일반 데스크톱 프로그램처럼 실행됩니다. 창을 닫으면 내부 서버도 함께 종료됩니다.

### 방법 A. 더블클릭으로 실행 (macOS, 추천 · 터미널 명령 불필요)

- **`서울 아파트 대시보드.app`** — **자체 완결형 앱**. 파이썬 실행 환경과 라이브러리(streamlit, plotly, pywebview 등)가
  앱 내부(`Contents/Resources/venv`)에 통째로 들어 있어 별도 설치 없이 바로 실행됩니다(약 340MB).
  더블클릭하면 **터미널·브라우저 없이 데스크톱 앱 창**이 바로 뜹니다. Dock이나 `응용 프로그램` 폴더로 옮겨 두고 써도 됩니다.
- **`run.command`** — 가벼운 실행 스크립트. 더블클릭하면 (최초 1회) 프로젝트 폴더에 `.venv`를 만들어 라이브러리를
  설치한 뒤 데스크톱 앱 창을 띄웁니다. 이 경우 로그 확인용 터미널 창이 함께 뜹니다.

> - `.app`은 라이브러리가 내장돼 **처음부터 즉시 실행**됩니다. `run.command`는 최초 1회만 설치로 몇 분 걸립니다.
> - 처음 열 때 "확인되지 않은 개발자" 경고가 뜨면, 앱을 **오른쪽 클릭 → 열기 → 열기**로 한 번만 허용해 주세요.
> - 종료: **앱 창을 닫으면** 됩니다. (`.app` 로그는 `~/Library/Logs/서울아파트대시보드.log` 에 기록)
> - `.app`은 이 Mac의 파이썬(Command Line Tools)에 맞춰 빌드되어 **이 컴퓨터에서 바로 동작**합니다.

### 방법 A-2. 개발 중 데스크톱 창으로 직접 실행

```bash
cd seoul_apartment_dashboard
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python fetch_data.py       # data/apartment_data.json 생성(없을 때)
python desktop.py          # 브라우저 대신 데스크톱 앱 창으로 실행
```

### 방법 B. 터미널에서 브라우저로 실행

```bash
cd seoul_apartment_dashboard
python -m venv .venv
source .venv/bin/activate         # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python fetch_data.py              # data/apartment_data.json 생성(없을 때)
streamlit run app.py
```

브라우저에서 `http://localhost:8501` 이 자동으로 열립니다.

> `st.dialog` 와 플롯 클릭 이벤트(`on_select`)를 사용하므로 **Streamlit 1.35 이상**이 필요합니다.

## 폴더 구조

```
seoul_apartment_dashboard/
├── app.py                     # 메인 Streamlit 앱 (화면/인터랙션)
├── desktop.py                 # 데스크톱 창 런처 (Streamlit 서버 + PyWebView 네이티브 창)
├── data_loader.py             # 데이터 계층: 로딩·정규화·이상치 탐지 (화면과 데이터 분리)
├── fetch_data.py              # 실거래 데이터 수집 -> data/apartment_data.json 생성 (사용자 스크립트)
├── requirements.txt           # 의존성 (streamlit, plotly, pywebview)
├── README.md
├── run.command                # ▶ 더블클릭 실행 스크립트 (최초 1회 .venv 자동 생성)
├── 서울 아파트 대시보드.app     # ▶ 자체 완결형 앱 (파이썬 환경/라이브러리 내장, 약 340MB)
│   └── Contents/
│       ├── MacOS/launcher              # 진입점: 내장 venv 로 desktop.py 실행
│       └── Resources/
│           ├── run.command             # 내장 venv 로 desktop.py 실행(로그용)
│           ├── app/                     # app.py 등 소스 사본
│           └── venv/                    # 내장 파이썬 가상환경(streamlit·plotly·pywebview…)
└── data/
    ├── apartment_data.json     # 아파트 실거래 데이터 (fetch_data.py 가 생성)
    └── seoul_districts.geojson # 서울시 25개 자치구 경계 (출처: southkorea/seoul-maps)
```

## 데이터 형식 (스키마)

화면 코드는 **이 형식만** 알면 됩니다. `data/apartment_data.json`:

```jsonc
{
  "meta": {
    "source": "국토교통부 실거래가 ...",          // 화면 상단 출처 문구
    "generated_at": "2026-08-12 09:00:00",       // 데이터 생성/갱신 시각
    "unit": "만원/㎡ (전용면적 기준 평균 거래단가)",
    "note": "일별은 실거래 평균 기반 참고치"        // 일별 그래프 아래 안내 문구
  },
  "districts": {
    "강남구": {
      "code": "11680",
      "latest_change_pct": 0.42,        // 지도 색칠용 대표 등락률(%). null 가능
      "latest_date": "2026-08-11",
      "daily":   [ { "date":   "2026-08-11", "avg_manwon_per_m2": 2438, "count": 32, "pct": 0.42 }, ... ],
      "monthly": [ { "period": "2026-08",    "avg_manwon_per_m2": 2410, "count": 210, "pct": 0.6 }, ... ],
      "yearly":  [ { "period": "2026",       "avg_manwon_per_m2": 2390, "count": 2400, "pct": 5.1 }, ... ]
    }
    // ... 나머지 24개 구
  }
}
```

핵심 규칙:

- `districts` 의 키(구 이름)는 `seoul_districts.geojson` 의 `properties.name` 값과 **정확히 일치**해야 지도에 색이 칠해집니다.
  (강남구, 서초구, 송파구, 강동구, 마포구, 용산구, 종로구, 중구, 성동구, 광진구, 동대문구, 중랑구, 성북구,
  강북구, 도봉구, 노원구, 은평구, 서대문구, 양천구, 강서구, 구로구, 금천구, 영등포구, 동작구, 관악구 — 총 25개)
- 시계열의 x축 키: `daily` 는 `date`, `monthly`/`yearly` 는 `period`.
- 등락률은 각 시계열 항목의 `pct` (%, 양수=상승/음수=하락). 데이터가 없으면 `null` (그래프에서 끊김 처리).
- `latest_change_pct` 가 `null` 이면 지도에서 회색 "데이터 없음"으로 칠해지고, 평균·총평 계산에서 제외됩니다.

## 실제 데이터로 갱신

화면(`app.py`)과 데이터(`data/apartment_data.json`)가 분리되어 있어, **위 스키마로 파일만 다시 만들면 화면 수정 없이 동작**합니다.

1. `fetch_data.py` 로 국토교통부 실거래가 등에서 **아파트** 거래를 수집·집계해 위 형식의 JSON을 생성합니다.
   - `latest_change_pct` ← 대표 등락률(%). fetch_data.py 는 일별 노이즈를 피해 **진행 중인 달을 제외한
     마지막 완결 월의 전월 대비 변동률**로 계산합니다.
   - `daily/monthly/yearly[].pct` ← 각 기간 단위 등락률, `avg_manwon_per_m2` ← 평균 거래단가(만원/㎡), `count` ← 거래건수
   - `meta.source`, `meta.generated_at` 을 실제 값으로 채우면 화면 상단 문구가 자동으로 바뀝니다.
2. 앱을 다시 실행(또는 새로고침)하면 반영됩니다.

> ⚠️ **`.app`은 소스/데이터의 사본을 내부에 갖고 있습니다.** 데이터·코드를 수정 중이라면 프로젝트 루트 파일을
> 그대로 쓰는 **`run.command`** 로 실행하면 즉시 반영됩니다. 수정 내용을 `.app`에도 반영하려면
> 아래 한 줄로 앱 내부 사본만 갱신하세요(파이썬 환경은 그대로 재사용):
>
> ```bash
> cd "seoul_apartment_dashboard" && rsync -a --delete app.py desktop.py data_loader.py requirements.txt data "서울 아파트 대시보드.app/Contents/Resources/app/"
> ```

## 외부 공개 배포 (Streamlit Community Cloud)

앱 실행에는 **API 키가 필요 없습니다.** 키는 데이터를 만드는 `fetch_data.py` 에만 쓰이고,
앱은 커밋된 `data/apartment_data.json` 을 읽습니다. 아래 순서로 무료 공개할 수 있습니다.

### 1) GitHub 저장소에 올리기

`.gitignore` 가 **`.env`(인증키)·`.venv/`·`*.app/`·`_raw_transactions.json`** 을 자동 제외합니다. (검증됨)

```bash
cd seoul_apartment_dashboard
git init && git add -A && git commit -m "init"
git branch -M main
git remote add origin https://github.com/<사용자명>/<저장소>.git
git push -u origin main
```

> ⚠️ 푸시 전 반드시 확인: `git status` 에 `.env` / `example.env.py` 가 보이면 안 됩니다.
> (`git check-ignore .env` 가 `.env` 를 출력하면 정상적으로 무시되는 것)

### 2) Streamlit Community Cloud 배포

1. <https://share.streamlit.io> 접속 → GitHub 계정 연결
2. **New app** → 저장소/브랜치(`main`)/메인 파일 `app.py` 선택 → Deploy
3. 클라우드가 `requirements.txt`(streamlit, plotly)만 설치하고 공개 URL을 생성합니다.
   - 데스크톱용 `pywebview` 는 웹 배포에 불필요하므로 `requirements-desktop.txt` 로 분리되어 있습니다.

### 3) 데이터 자동 갱신 (GitHub Actions)

`.github/workflows/update-data.yml` 이 **매일 KST 06:00** 에 `fetch_data.py` 를 실행해
`data/apartment_data.json` 을 갱신·커밋합니다. 푸시가 일어나면 Streamlit Cloud가 자동 재배포됩니다.

- **저장소 설정 필요**: GitHub 저장소 → **Settings → Secrets and variables → Actions → New repository secret**
  - 이름: `MOLIT_API_KEY`, 값: 공공데이터포털 인증키
- 수동 실행: 저장소 **Actions 탭 → "아파트 실거래 데이터 자동 갱신" → Run workflow**
- 앱은 `@st.cache_data(ttl=3600)` 으로 최대 1시간 내 최신 데이터를 반영합니다.

### 배포 시 주의

- **인증키 유출 금지**: `.env` / `example.env.py` 는 절대 커밋하지 마세요(이미 gitignore 처리됨). 키는 GitHub Secrets 로만.
- **출처·면책**: 화면에 출처(국토부 실거래가)와 "참고용, 투자 판단 근거 아님" 문구가 표시됩니다.
- **약관**: 공공데이터포털 활용 약관(출처 표기·재배포)과 GeoJSON 라이선스(southkorea/seoul-maps)를 확인하세요.
- 서버가 국토부 API를 직접 호출하지 않고(사전 생성된 JSON 서비스), 트래픽 제한 걱정이 없습니다.

## 총평(이상 징후) 로직

`data_loader.detect_anomalies()` 가 데이터 수치만으로 이상치를 자동 탐지합니다 (`latest_change_pct` 가 `null` 인 구는 제외).

- **급등/급락(spike/plunge)**: 각 구의 `latest_change_pct` 를 전 자치구 분포와 비교해 z-score 가 임계값(기본 1.5σ)을 넘으면 탐지
- **역방향(contrarian)**: 시장 전체 방향(중앙값 부호)과 반대로 유의미하게 움직이는 구 탐지 (급등/급락으로 이미 설명된 구는 제외)
- **고변동성(volatile)**: 월별 `pct` 의 표준편차가 다른 구 대비 임계값(기본 1.5σ)을 넘으면 탐지

추정 원인은 데이터만으로 단정하지 않고 **'추정'** 임을 명시합니다.
임계값은 `detect_anomalies(z_threshold=..., vol_z_threshold=...)` 인자로 조정할 수 있습니다.

## 데이터 출처

- 자치구 경계 GeoJSON: [southkorea/seoul-maps](https://github.com/southkorea/seoul-maps) (`kostat/2013/json/seoul_municipalities_geo_simple.json`)
- 아파트 실거래: 국토교통부 실거래가 공개시스템 (참고: 한국부동산원 R-ONE, KB부동산)
