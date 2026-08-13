"""
데이터 계층 (Data Layer).

화면(app.py)은 이 모듈이 제공하는 함수/자료구조만 알면 된다.
실제 데이터는 `fetch_data.py`(국토교통부 실거래가 등)가 생성한
`data/apartment_data.json` 을 읽는다.

--- JSON 스키마 (fetch_data.py 출력) -------------------------------------
{
  "meta": {
    "source": "국토교통부 실거래가 ...",   # 출처 문구
    "generated_at": "YYYY-MM-DD HH:MM:SS",  # 데이터 생성/갱신 시각
    "unit": "만원/㎡ (전용면적 기준 평균 거래단가)",
    "note": "일별은 실거래 평균 기반 참고치"
  },
  "districts": {
    "강남구": {
      "code": "11680",
      "latest_change_pct": 0.42,     # 지도 색칠용 대표 등락률(%). null 가능
      "latest_date": "2026-08-11",
      "daily":   [{"date":   "YYYY-MM-DD", "avg_manwon_per_m2": 숫자, "count": 정수, "pct": 숫자|null}, ...],
      "monthly": [{"period": "YYYY-MM",    "avg_manwon_per_m2": 숫자, "count": 정수, "pct": 숫자|null}, ...],
      "yearly":  [{"period": "YYYY",       "avg_manwon_per_m2": 숫자, "count": 정수, "pct": 숫자|null}, ...]
    },
    ... (25개 자치구)
  }
}
---------------------------------------------------------------------------
"""

from __future__ import annotations

import json
import statistics
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).parent / "data"
DATA_PATH = DATA_DIR / "apartment_data.json"
GEOJSON_PATH = DATA_DIR / "seoul_districts.geojson"

# GeoJSON 의 자치구 이름이 담긴 property 키 (southkorea/seoul-maps 기준: "name")
GEOJSON_NAME_KEY = "name"

# 시계열 종류별 x축 키 / 등락률 키
CHANGE_KEY = "pct"                       # 등락률(%) 필드명
PRICE_KEY = "avg_manwon_per_m2"          # 평균 거래단가(만원/㎡) 필드명
COUNT_KEY = "count"                      # 거래 건수 필드명


class DataFileMissing(FileNotFoundError):
    """data/apartment_data.json 이 없을 때 발생 (앱에서 안내 메시지로 처리)."""


# ---------------------------------------------------------------------------
# 로딩
# ---------------------------------------------------------------------------
def load_data(path: Path | str = DATA_PATH) -> dict[str, Any]:
    """아파트 실거래 데이터 JSON 로드. 파일이 없으면 DataFileMissing."""
    p = Path(path)
    if not p.exists():
        raise DataFileMissing(str(p))
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def load_geojson(path: Path | str = GEOJSON_PATH) -> dict[str, Any]:
    """서울시 자치구 경계 GeoJSON 로드."""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def get_meta(data: dict[str, Any]) -> dict[str, Any]:
    return data.get("meta", {})


# ---------------------------------------------------------------------------
# 화면에서 쓰기 좋은 형태로 변환
# ---------------------------------------------------------------------------
def _latest_price(d: dict[str, Any]) -> float | None:
    """가장 최근 일별 평균 거래단가(만원/㎡). 없으면 None."""
    daily = d.get("daily") or []
    for row in reversed(daily):
        v = row.get(PRICE_KEY)
        if v is not None:
            return float(v)
    return None


def districts_table(data: dict[str, Any]) -> list[dict[str, Any]]:
    """구별 요약 리스트: name, code, change_pct(None 가능), latest_date, latest_price."""
    rows: list[dict[str, Any]] = []
    for name, d in data["districts"].items():
        cp = d.get("latest_change_pct")
        rows.append(
            {
                "name": name,
                "code": d.get("code"),
                "change_pct": None if cp is None else float(cp),
                "latest_date": d.get("latest_date"),
                "latest_price": _latest_price(d),
            }
        )
    rows.sort(key=lambda r: r["name"])
    return rows


def get_district(data: dict[str, Any], name: str) -> dict[str, Any] | None:
    return data["districts"].get(name)


def get_series(data: dict[str, Any], name: str, kind: str) -> list[dict[str, Any]]:
    """kind in {'daily','monthly','yearly'} 의 시계열 반환."""
    d = get_district(data, name)
    if not d:
        return []
    return d.get(kind, [])


def series_x_key(kind: str) -> str:
    """시계열 x축 키 이름 ('daily'->date, else 'period')."""
    return "date" if kind == "daily" else "period"


def format_price(value: int | float | None) -> str:
    """평균 거래단가(만원/㎡)를 사람이 읽기 좋은 문자열로."""
    if value is None:
        return "데이터 없음"
    return f"{value:,.0f} 만원/㎡"


# ---------------------------------------------------------------------------
# 총평(이상 징후) 자동 탐지
#   latest_change_pct 기준. null 인 구는 계산에서 제외.
#   추정 원인은 데이터만으로 단정하지 않고 '추정'임을 명시한다.
# ---------------------------------------------------------------------------
@dataclass
class Anomaly:
    kind: str            # spike | plunge | contrarian | volatile
    district: str        # 구 이름
    headline: str        # 한 줄 요약
    detail: str          # 상세/추정 원인
    value: float         # 관련 수치(등락률 또는 변동성)


def _stdev(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    return statistics.pstdev(values)


def _monthly_volatility(d: dict[str, Any]) -> float:
    """월별 pct 의 표준편차(변동성). 유효 표본이 부족하면 0."""
    monthly = d.get("monthly") or []
    pcts = [float(m[CHANGE_KEY]) for m in monthly if m.get(CHANGE_KEY) is not None]
    return _stdev(pcts)


def detect_anomalies(
    data: dict[str, Any],
    z_threshold: float = 1.5,
    vol_z_threshold: float = 1.5,
) -> list[Anomaly]:
    """구별 대표 등락률/변동성에서 이상 징후를 탐지 (null 구는 제외)."""
    districts = data["districts"]

    # latest_change_pct 가 유효한(숫자) 구만 대상
    changes = {
        n: float(d["latest_change_pct"])
        for n, d in districts.items()
        if d.get("latest_change_pct") is not None
    }
    names = list(changes.keys())
    if len(names) < 3:
        return []  # 표본 부족 -> 이상치 판단 보류

    change_vals = list(changes.values())
    mean_c = statistics.fmean(change_vals)
    std_c = _stdev(change_vals) or 1e-9
    market_median = statistics.median(change_vals)
    market_dir = "상승" if market_median > 0 else ("하락" if market_median < 0 else "보합")

    # 월별 변동성 (유효 구만)
    vols = {n: _monthly_volatility(districts[n]) for n in names}
    vol_vals = [v for v in vols.values() if v > 0]
    mean_v = statistics.fmean(vol_vals) if vol_vals else 0.0
    std_v = _stdev(vol_vals) or 1e-9

    anomalies: list[Anomaly] = []
    extreme_flagged: set[str] = set()

    # 1) spike / plunge : z-score 로 극단 등락 탐지
    for n in names:
        z = (changes[n] - mean_c) / std_c
        if z >= z_threshold and changes[n] > 0:
            anomalies.append(
                Anomaly(
                    kind="spike",
                    district=n,
                    headline=f"{n} 아파트값 이례적 급등 ({changes[n]:+.2f}%)",
                    detail=(
                        f"전체 자치구 평균({mean_c:+.2f}%) 대비 {z:.1f}σ 높은 상승. "
                        f"(추정) 국지적 개발호재·재건축 기대·특정 단지 신고가 거래 등이 "
                        f"평균을 끌어올렸을 가능성 — 데이터만으로 단정할 수 없는 추정임."
                    ),
                    value=changes[n],
                )
            )
            extreme_flagged.add(n)
        elif z <= -z_threshold and changes[n] < 0:
            anomalies.append(
                Anomaly(
                    kind="plunge",
                    district=n,
                    headline=f"{n} 아파트값 이례적 급락 ({changes[n]:+.2f}%)",
                    detail=(
                        f"전체 자치구 평균({mean_c:+.2f}%) 대비 {abs(z):.1f}σ 낮은 하락. "
                        f"(추정) 급매물 출회·거래 위축·입주물량 집중 등 하방 압력 "
                        f"가능성 — 데이터만으로 단정할 수 없는 추정임."
                    ),
                    value=changes[n],
                )
            )
            extreme_flagged.add(n)

    # 2) contrarian : 시장 다수 방향과 반대 + 절대값이 유의미
    if market_dir in ("상승", "하락"):
        for n in names:
            if n in extreme_flagged:
                continue
            c = changes[n]
            opposite = (market_dir == "상승" and c < 0) or (
                market_dir == "하락" and c > 0
            )
            if opposite and abs(c) >= max(0.5, 0.8 * std_c):
                anomalies.append(
                    Anomaly(
                        kind="contrarian",
                        district=n,
                        headline=f"{n} 시장과 반대 흐름 ({c:+.2f}%)",
                        detail=(
                            f"시장 전반은 '{market_dir}'(중앙값 {market_median:+.2f}%)인데 "
                            f"{n}만 반대 방향으로 움직임. (추정) 지역 고유의 수급 요인"
                            f"(재건축 이슈·학군 수요·공급 부족 등)에 따른 디커플링 "
                            f"가능성 — 데이터만으로 단정할 수 없는 추정임."
                        ),
                        value=c,
                    )
                )

    # 3) volatile : 월별 변동성이 비정상적으로 큼
    for n in names:
        if vols[n] <= 0:
            continue
        zv = (vols[n] - mean_v) / std_v
        if zv >= vol_z_threshold:
            anomalies.append(
                Anomaly(
                    kind="volatile",
                    district=n,
                    headline=f"{n} 변동성 비정상 확대 (월별 σ={vols[n]:.2f})",
                    detail=(
                        f"월별 등락률의 변동성이 평균({mean_v:.2f}) 대비 {zv:.1f}σ 큼. "
                        f"(추정) 거래량이 얇아 소수 거래에도 평균단가가 크게 출렁이는 "
                        f"'저유동성 구간'일 가능성 — 데이터만으로 단정할 수 없는 추정임."
                    ),
                    value=vols[n],
                )
            )

    anomalies.sort(key=lambda a: abs(a.value), reverse=True)
    return anomalies


def market_summary_stats(data: dict[str, Any]) -> dict[str, Any]:
    """총평 상단/스냅샷용 시장 전반 요약 수치 (null 구 제외)."""
    rows = [r for r in districts_table(data) if r["change_pct"] is not None]
    n_null = len(data["districts"]) - len(rows)
    if not rows:
        return {
            "count": 0, "mean": 0.0, "median": 0.0,
            "up_count": 0, "down_count": 0, "flat_count": 0,
            "null_count": n_null, "top": None, "bottom": None,
        }
    changes = [r["change_pct"] for r in rows]
    ups = [r for r in rows if r["change_pct"] > 0]
    downs = [r for r in rows if r["change_pct"] < 0]
    return {
        "count": len(rows),
        "mean": statistics.fmean(changes),
        "median": statistics.median(changes),
        "up_count": len(ups),
        "down_count": len(downs),
        "flat_count": len(rows) - len(ups) - len(downs),
        "null_count": n_null,
        "top": max(rows, key=lambda r: r["change_pct"]),
        "bottom": min(rows, key=lambda r: r["change_pct"]),
    }
