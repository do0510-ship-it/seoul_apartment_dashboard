"""
서울시 25개 자치구 '아파트' 실거래 등락률 대시보드 (Streamlit + Plotly).

실행:
    pip install -r requirements.txt
    python fetch_data.py          # data/apartment_data.json 생성(국토부 실거래가 등)
    streamlit run app.py          # 또는 데스크톱 창: python desktop.py

- 통계 대상: '아파트'만 포함 (단독/다세대/연립 제외)
- 데이터는 data_loader 를 통해서만 접근 (fetch_data.py 출력 형식만 알면 됨)
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import plotly.graph_objects as go
import streamlit as st

import data_loader as dl

APP_DIR = Path(__file__).resolve().parent
FETCH_SCRIPT = APP_DIR / "fetch_data.py"

# ---------------------------------------------------------------------------
# 페이지 설정
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="서울시 자치구별 아파트 등락률 대시보드",
    page_icon="🏢",
    layout="wide",
)

# 데스크톱 앱 창(PyWebView)으로 띄웠을 때 브라우저 느낌을 줄이기 위해
# 우측 상단 툴바(Deploy/메뉴)·헤더·푸터를 숨기고 상단 여백을 줄인다.
st.markdown(
    """
    <style>
      [data-testid="stToolbar"] {display: none !important;}
      [data-testid="stDecoration"] {display: none !important;}
      header {visibility: hidden; height: 0;}
      footer {visibility: hidden; height: 0;}
      #MainMenu {visibility: hidden;}
      .block-container {padding-top: 2.2rem;}
      /* 지도 클릭(선택) 후 Plotly 가 선택되지 않은 구를 흐리게(inline opacity↓) 만드는 것을
         CSS 로 강제 차단 -> 팝업을 닫아도 지도가 절대 뿌옇게 남지 않도록 함. */
      [data-testid="stPlotlyChart"] {opacity: 1 !important;}
      .js-plotly-plot .choroplethlocation {opacity: 1 !important;}
      .js-plotly-plot .choroplethlayer path {opacity: 1 !important;}
    </style>
    """,
    unsafe_allow_html=True,
)

# 색상 상수 (상승=빨강, 하락=파랑 톤 일관 유지)
COLOR_UP = "#d6301f"     # 상승(빨강)
COLOR_DOWN = "#2166ac"   # 하락(파랑)
COLOR_FLAT = "#bdbdbd"   # 보합(회색)
COLOR_NODATA = "#d9d9d9"  # 데이터 없음(옅은 회색)


# ---------------------------------------------------------------------------
# 데이터 갱신 헬퍼
#   - 로컬(인증키 보유): 버튼으로 fetch_data.py 재수집까지 실행
#   - 공개 배포(키 없음): 버튼은 최신 JSON 재로딩(캐시 비우기)만 수행
# ---------------------------------------------------------------------------
def _api_key_available() -> bool:
    """국토부 인증키가 로컬에 있는지 확인 (환경변수 또는 .env)."""
    if os.environ.get("MOLIT_API_KEY", "").strip():
        return True
    env_file = APP_DIR / ".env"
    if env_file.exists():
        try:
            for line in env_file.read_text(encoding="utf-8").splitlines():
                s = line.strip()
                if s.startswith("MOLIT_API_KEY=") and s.split("=", 1)[1].strip():
                    return True
        except OSError:
            return False
    return False


def _can_refetch() -> bool:
    """재수집(fetch_data.py 실행) 가능 여부. 공개 배포에는 키가 없어 False."""
    return FETCH_SCRIPT.exists() and _api_key_available()


def _run_refetch(months: int = 24) -> tuple[bool, str]:
    """fetch_data.py 를 실행해 data/apartment_data.json 재생성. (성공여부, 메시지)."""
    try:
        r = subprocess.run(
            [sys.executable, str(FETCH_SCRIPT), "--months", str(months)],
            cwd=str(APP_DIR), capture_output=True, text=True, timeout=900,
        )
    except subprocess.TimeoutExpired:
        return False, "재수집 시간 초과(900초)."
    except Exception as e:  # noqa: BLE001
        return False, f"실행 오류: {e}"
    if r.returncode == 0:
        lines = (r.stdout or "").strip().splitlines()
        return True, (lines[-1] if lines else "완료")
    return False, (r.stderr or r.stdout or "알 수 없는 오류").strip()[-400:]


@st.cache_data(show_spinner=False, ttl=3600)  # 1시간마다 데이터 재로딩(배포 시 자동 반영)
def _load():
    data = dl.load_data()
    geojson = dl.load_geojson()
    return data, geojson


# --- 데이터 로딩 (없으면 안내 후 중단) --------------------------------------
try:
    data, geojson = _load()
except dl.DataFileMissing:
    st.title("🏢 서울시 자치구별 아파트 등락률 대시보드")
    st.error(
        "데이터 파일 `data/apartment_data.json` 이 없습니다.\n\n"
        "터미널에서 아래를 먼저 실행해 실거래 데이터를 생성해 주세요:\n\n"
        "```\npython fetch_data.py\n```"
    )
    st.stop()

meta = dl.get_meta(data)
source = meta.get("source", "국토교통부 실거래가")
generated_at = meta.get("generated_at", "-")
price_unit = meta.get("unit", "만원/㎡")
note = meta.get("note", "")

# 지도 위젯 key 를 새로 바꾸기 위한 nonce (팝업 열 때마다 선택 상태 초기화용).
st.session_state.setdefault("map_nonce", 0)


# ---------------------------------------------------------------------------
# 헤더 + 출처/갱신일 표기
# ---------------------------------------------------------------------------
st.title("🏢 서울시 자치구별 아파트 등락률 대시보드")
st.caption(
    "통계 대상: **아파트** 만 포함 (단독주택·다세대/연립 제외) · "
    "색칠 기준: **직전(완결) 월 대비 아파트 등락률(%)** · "
    f"단위: **{price_unit}**"
)
st.info(f"📊 **{source}** 기준 · 데이터 갱신일: **{generated_at}**", icon="📊")
st.caption(
    "⚠️ 참고용 정보입니다. 국토교통부 공개 실거래가를 가공한 것으로 **투자·매매 판단의 근거로 사용하지 마세요.** "
    "표본이 적은 자치구·기간은 수치가 크게 변동할 수 있습니다."
)


# ---------------------------------------------------------------------------
# 지도(choropleth) 생성
# ---------------------------------------------------------------------------
def build_map() -> go.Figure:
    rows = dl.districts_table(data)
    valued = [r for r in rows if r["change_pct"] is not None]
    nulls = [r for r in rows if r["change_pct"] is None]

    # 0 중심 대칭 색상 범위 (극단값에도 견고하도록 max abs 사용)
    cabs = max((abs(r["change_pct"]) for r in valued), default=1.0)
    cmax = max(cabs, 0.5)

    fig = go.Figure()

    # (1) 등락률이 있는 구: diverging 색상
    if valued:
        fig.add_trace(
            go.Choropleth(
                geojson=geojson,
                locations=[r["name"] for r in valued],
                featureidkey=f"properties.{dl.GEOJSON_NAME_KEY}",
                z=[r["change_pct"] for r in valued],
                customdata=[
                    [r["name"], r["change_pct"], dl.format_price(r["latest_price"])]
                    for r in valued
                ],
                colorscale="RdBu_r",  # 높을수록 빨강(상승), 낮을수록 파랑(하락)
                zmid=0,
                zmin=-cmax,
                zmax=cmax,
                marker_line_color="white",
                marker_line_width=1.0,
                selected=dict(marker=dict(opacity=1.0)),
                unselected=dict(marker=dict(opacity=1.0)),
                colorbar=dict(title="등락률(%)", ticksuffix="%", thickness=14, len=0.85),
                hovertemplate=(
                    "<b>%{customdata[0]}</b><br>"
                    "아파트 등락률: %{customdata[1]:+.2f}%<br>"
                    "평균 거래단가: %{customdata[2]}<extra></extra>"
                ),
            )
        )

    # (2) 등락률이 없는(null) 구: 회색 '데이터 없음'
    if nulls:
        fig.add_trace(
            go.Choropleth(
                geojson=geojson,
                locations=[r["name"] for r in nulls],
                featureidkey=f"properties.{dl.GEOJSON_NAME_KEY}",
                z=[0] * len(nulls),
                customdata=[[r["name"]] for r in nulls],
                colorscale=[[0, COLOR_NODATA], [1, COLOR_NODATA]],
                showscale=False,
                marker_line_color="white",
                marker_line_width=1.0,
                selected=dict(marker=dict(opacity=1.0)),
                unselected=dict(marker=dict(opacity=1.0)),
                hovertemplate="<b>%{customdata[0]}</b><br>데이터 없음<extra></extra>",
            )
        )

    # 구 라벨 (이름 + 등락률 / 데이터 없음)
    lons, lats, texts = _label_points(rows)
    fig.add_trace(
        go.Scattergeo(
            lon=lons, lat=lats, text=texts, mode="text",
            textfont=dict(size=10, color="#111"),
            hoverinfo="skip", showlegend=False,
        )
    )

    fig.update_geos(fitbounds="locations", visible=False, projection_type="mercator")
    fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=620, dragmode=False)
    return fig


def _polygon_centroid(coords) -> tuple[float, float]:
    """단순 평균 기반 대표점(라벨 배치용)."""
    xs, ys = [], []

    def walk(c):
        if isinstance(c[0], (int, float)):
            xs.append(c[0])
            ys.append(c[1])
        else:
            for sub in c:
                walk(sub)

    walk(coords)
    return (sum(xs) / len(xs), sum(ys) / len(ys))


@st.cache_data(show_spinner=False)
def _centroids() -> dict[str, tuple[float, float]]:
    out: dict[str, tuple[float, float]] = {}
    for f in geojson["features"]:
        name = f["properties"][dl.GEOJSON_NAME_KEY]
        out[name] = _polygon_centroid(f["geometry"]["coordinates"])
    return out


def _label_points(rows):
    cents = _centroids()
    lons, lats, texts = [], [], []
    for r in rows:
        c = cents.get(r["name"])
        if not c:
            continue
        lons.append(c[0])
        lats.append(c[1])
        if r["change_pct"] is None:
            texts.append(f"{r['name']}<br>데이터 없음")
        else:
            texts.append(f"{r['name']}<br>{r['change_pct']:+.2f}%")
    return lons, lats, texts


# ---------------------------------------------------------------------------
# 팝업(모달) — 등락률 추이 그래프
# ---------------------------------------------------------------------------
def _trend_figure(name: str, kind: str) -> go.Figure:
    series = dl.get_series(data, name, kind)
    xkey = dl.series_x_key(kind)

    xs = [p.get(xkey) for p in series]
    ys = [None if p.get(dl.CHANGE_KEY) is None else float(p[dl.CHANGE_KEY]) for p in series]
    prices = [p.get(dl.PRICE_KEY) for p in series]
    counts = [p.get(dl.COUNT_KEY) for p in series]

    # 툴팁용: 평균 거래단가(만원/㎡) + 거래건수
    customdata = [
        [f"{pr:,.0f}" if pr is not None else "-", (c if c is not None else 0)]
        for pr, c in zip(prices, counts)
    ]
    colors = [
        COLOR_UP if (v is not None and v > 0)
        else (COLOR_DOWN if (v is not None and v < 0) else COLOR_FLAT)
        for v in ys
    ]

    hovertmpl = (
        "%{x}<br>등락률 %{y:+.2f}%<br>"
        "평균 %{customdata[0]} 만원/㎡ · 거래 %{customdata[1]}건<extra></extra>"
    )

    fig = go.Figure()
    if kind == "daily":
        # 일별: 라인(+마커). null 값은 자연스러운 끊김(gap)으로 처리.
        fig.add_trace(
            go.Scatter(
                x=xs, y=ys, mode="lines+markers",
                connectgaps=False,
                line=dict(color="#444", width=1.6),
                marker=dict(size=4, color=colors),
                customdata=customdata,
                hovertemplate=hovertmpl,
                name="등락률",
            )
        )
    else:
        # 월별/년별: 상승=빨강, 하락=파랑 막대 (null 은 막대 없음)
        fig.add_trace(
            go.Bar(
                x=xs, y=ys, marker_color=colors,
                customdata=customdata,
                hovertemplate=hovertmpl,
                name="등락률",
            )
        )
    fig.add_hline(y=0, line_width=1, line_color="#999")
    unit_label = {"daily": "일별", "monthly": "월별", "yearly": "년별"}[kind]
    fig.update_layout(
        title=f"{name} 아파트 등락률 추이 — {unit_label} (평균단가 {price_unit})",
        yaxis_title="등락률(%)",
        margin=dict(l=10, r=10, t=48, b=10),
        height=380,
        showlegend=False,
    )
    return fig


@st.dialog(" ", width="large")
def show_district_dialog(name: str):
    d = dl.get_district(data, name)
    if not d:
        st.error(f"'{name}' 데이터를 찾을 수 없습니다.")
        return

    cp = d.get("latest_change_pct")
    latest_date = d.get("latest_date") or "-"
    # 최근 평균 거래단가
    latest_price = None
    for r in reversed(d.get("daily") or []):
        if r.get(dl.PRICE_KEY) is not None:
            latest_price = r[dl.PRICE_KEY]
            break

    if cp is None:
        change_str, delta, trend = "데이터 없음", None, "⚪ 데이터 없음"
    else:
        change_str = f"{cp:+.2f}%"
        delta = f"{cp:+.2f}%"
        trend = "🔴 상승" if cp > 0 else ("🔵 하락" if cp < 0 else "⚪ 보합")

    st.subheader(f"🏢 {name} · 아파트")
    c1, c2, c3 = st.columns(3)
    c1.metric("직전(완결) 월 대비 등락률", change_str, delta=delta)
    c2.metric("최근 평균 거래단가", dl.format_price(latest_price))
    c3.metric("최근 실거래일", latest_date)
    st.caption(
        f"현재 방향: {trend}  ·  대표값은 진행 중인 이번 달을 제외한 '직전 완결 월' 기준 · "
        f"단위: 등락률(%), 평균단가 {price_unit}"
    )

    tab_d, tab_m, tab_y = st.tabs(["📅 일별", "🗓️ 월별", "📆 년별"])
    with tab_d:
        st.plotly_chart(_trend_figure(name, "daily"), use_container_width=True,
                        key=f"dlg_daily_{name}")
        if note:
            st.caption(f"ℹ️ {note}")
    with tab_m:
        st.plotly_chart(_trend_figure(name, "monthly"), use_container_width=True,
                        key=f"dlg_monthly_{name}")
    with tab_y:
        st.plotly_chart(_trend_figure(name, "yearly"), use_container_width=True,
                        key=f"dlg_yearly_{name}")

    if st.button("닫기", type="primary", use_container_width=True):
        st.rerun()


# ---------------------------------------------------------------------------
# 레이아웃: 지도 + 사이드 요약/선택
# ---------------------------------------------------------------------------
left, right = st.columns([3, 1], gap="large")

with right:
    if st.session_state.pop("_refetch_done", False):
        st.success("✅ 재수집 완료 — 최신 데이터를 반영했습니다.")

    if _can_refetch():
        # 로컬(인증키 보유): 국토부 API 재수집 후 새로고침 (자동 갱신과 별개로 수동 즉시 갱신용)
        st.markdown("#### 🔄 데이터")
        st.caption(f"마지막 갱신: {generated_at}")
        if st.button("🔄 실거래 재수집 후 새로고침", use_container_width=True):
            with st.spinner("국토부 실거래가 재수집 중… (약 1분)"):
                ok, msg = _run_refetch()
            if ok:
                st.cache_data.clear()
                st.session_state["_refetch_done"] = True
                st.rerun()
            else:
                st.error(f"재수집 실패: {msg}")
        st.caption("국토부 API로 실거래를 다시 수집합니다. (로컬 전용 · 약 1분) · 6시간마다(00·06·12·18시) 자동 갱신")
    else:
        # 공개 배포(키 없음): 수동 갱신 비활성화 — 데이터는 자동으로만 갱신
        st.markdown("#### 📅 데이터")
        st.caption(f"마지막 갱신: {generated_at}")
        st.caption("데이터는 매일 자동으로 갱신됩니다.")

    st.divider()
    st.markdown("#### 🔎 구 선택")
    st.caption("지도에서 구를 클릭하거나, 아래에서 선택해 추이를 확인하세요.")
    all_names = [r["name"] for r in dl.districts_table(data)]
    picked = st.selectbox("자치구", all_names, index=None, placeholder="자치구 선택…")
    if st.button("📈 추이 그래프 열기", use_container_width=True, disabled=picked is None):
        show_district_dialog(picked)

    st.divider()
    stats = dl.market_summary_stats(data)
    st.markdown("#### 📊 시장 스냅샷")
    st.metric("자치구 평균 등락률", f"{stats['mean']:+.2f}%")
    st.write(
        f"- 상승 **{stats['up_count']}** · 하락 **{stats['down_count']}** · "
        f"보합 **{stats['flat_count']}**"
    )
    if stats["null_count"]:
        st.write(f"- 데이터 없음 **{stats['null_count']}**곳 (평균·총평에서 제외)")
    if stats["top"] and stats["bottom"]:
        st.write(
            f"- 최고 🔴 **{stats['top']['name']}** {stats['top']['change_pct']:+.2f}%"
        )
        st.write(
            f"- 최저 🔵 **{stats['bottom']['name']}** {stats['bottom']['change_pct']:+.2f}%"
        )

with left:
    fig = build_map()
    event = st.plotly_chart(
        fig,
        use_container_width=True,
        on_select="rerun",
        selection_mode="points",
        key=f"seoul_map_{st.session_state.map_nonce}",
    )

    # 지도 클릭 -> 선택된 구로 팝업 열기
    clicked = None
    try:
        pts = event["selection"]["points"] if event else []
        if pts:
            clicked = pts[0].get("location")
    except (KeyError, TypeError):
        clicked = None

    if clicked:
        st.session_state.map_nonce += 1  # 다음 렌더에서 선택 상태 초기화
        show_district_dialog(clicked)


# ---------------------------------------------------------------------------
# 하단 총평 (이상 징후 자동 탐지)
# ---------------------------------------------------------------------------
st.divider()
st.header("🧭 총평 — 이상 징후 자동 분석")
st.caption(
    "전체 평균이 아니라, **일반적이지 않은 상황(이상치)** 을 데이터에서 자동으로 골라 정리합니다. "
    "추정 원인은 데이터만으로 단정하지 않은 **추정**이며, 등락률이 없는(데이터 없음) 구는 계산에서 제외합니다."
)

anomalies = dl.detect_anomalies(data)

_kind_style = {
    "spike": ("🔴", "이례적 급등"),
    "plunge": ("🔵", "이례적 급락"),
    "contrarian": ("🔀", "시장과 반대 흐름"),
    "volatile": ("⚡", "변동성 급확대"),
}

if not anomalies:
    st.success("현재 데이터에서 통계적으로 특이한 이상 징후는 감지되지 않았습니다.")
else:
    st.write(f"감지된 이상 징후: **{len(anomalies)}건**")
    for a in anomalies:
        icon, label = _kind_style.get(a.kind, ("•", a.kind))
        with st.container(border=True):
            st.markdown(f"**{icon} [{label}] {a.headline}**")
            st.write(a.detail)

st.divider()
st.caption(
    f"ℹ️ 출처: {source} · 갱신일 {generated_at} · 단위 {price_unit}. "
    "데이터 계층(`data_loader.py`)과 데이터 파일(`data/apartment_data.json`)이 분리되어 있어, "
    "`python fetch_data.py` 로 데이터만 갱신하면 화면 수정 없이 동작합니다."
)
