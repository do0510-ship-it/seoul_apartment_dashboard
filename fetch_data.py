#!/usr/bin/env python3
"""
서울 25개 자치구 아파트 매매 실거래가 수집 → 앱용 JSON 생성 스크립트

데이터 출처: 국토교통부 아파트 매매 실거래가 자료 (공공데이터포털 data.go.kr, ID 15126469)
  엔드포인트: https://apis.data.go.kr/1613000/RTMSDataSvcAptTrade/getRTMSDataSvcAptTrade

실행 전 준비:
  1) pip install requests
  2) 같은 폴더에 .env 파일을 만들고  MOLIT_API_KEY=<본인 인증키>  한 줄 넣기
     - 인코딩 키(%2F, %2B, %3D 포함)를 넣어도 자동 디코딩됩니다.

실행:
  python fetch_data.py               # 최근 24개월
  python fetch_data.py --months 36   # 기간 조절

결과:
  data/apartment_data.json  (앱이 읽는 파일)
  data/_raw_transactions.json  (원본 거래 캐시, 디버깅용)
"""

import os
import sys
import time
import json
import argparse
import datetime as dt
from urllib.parse import unquote
from collections import defaultdict
import xml.etree.ElementTree as ET

import requests

API_URL = "https://apis.data.go.kr/1613000/RTMSDataSvcAptTrade/getRTMSDataSvcAptTrade"

# 서울 25개 자치구 법정동코드(시군구코드 5자리)
SEOUL_DISTRICTS = {
    "종로구": "11110", "중구": "11140", "용산구": "11170", "성동구": "11200",
    "광진구": "11215", "동대문구": "11230", "중랑구": "11260", "성북구": "11290",
    "강북구": "11305", "도봉구": "11320", "노원구": "11350", "은평구": "11380",
    "서대문구": "11410", "마포구": "11440", "양천구": "11470", "강서구": "11500",
    "구로구": "11530", "금천구": "11545", "영등포구": "11560", "동작구": "11590",
    "관악구": "11620", "서초구": "11650", "강남구": "11680", "송파구": "11710",
    "강동구": "11740",
}

OUT_DIR = "data"


def load_api_key() -> str:
    key = os.environ.get("MOLIT_API_KEY")
    if not key and os.path.exists(".env"):
        with open(".env", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("MOLIT_API_KEY="):
                    key = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break
    if not key:
        sys.exit("[에러] MOLIT_API_KEY가 없습니다. .env 파일에 MOLIT_API_KEY=<인증키>를 넣어주세요.")
    if "%" in key:
        key = unquote(key)
    return key


def month_list(months_back: int):
    today = dt.date.today()
    y, m = today.year, today.month
    result = []
    for _ in range(months_back):
        result.append(f"{y:04d}{m:02d}")
        m -= 1
        if m == 0:
            m = 12
            y -= 1
    return sorted(result)


def fetch_month(session, key, lawd_cd, deal_ymd, max_retry=3):
    params = {
        "serviceKey": key,
        "LAWD_CD": lawd_cd,
        "DEAL_YMD": deal_ymd,
        "pageNo": "1",
        "numOfRows": "1000",
    }
    for attempt in range(1, max_retry + 1):
        try:
            r = session.get(API_URL, params=params, timeout=30)
            r.raise_for_status()
            return parse_items(r.text)
        except Exception as e:
            if attempt == max_retry:
                print(f"    [실패] {lawd_cd} {deal_ymd}: {e}")
                return []
            time.sleep(1.5 * attempt)
    return []


def _tag(item, *names):
    for n in names:
        el = item.find(n)
        if el is not None and el.text is not None:
            return el.text.strip()
    return ""


def parse_items(xml_text):
    out = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return out

    header_msg = root.find(".//resultMsg")
    header_code = root.find(".//resultCode")
    if header_code is not None and header_code.text not in ("00", "000", None):
        msg = header_msg.text if header_msg is not None else "unknown"
        print(f"    [API 응답코드 {header_code.text}] {msg}")

    for item in root.iter("item"):
        year = _tag(item, "dealYear", "년")
        month = _tag(item, "dealMonth", "월")
        day = _tag(item, "dealDay", "일")
        amount = _tag(item, "dealAmount", "거래금액")
        area = _tag(item, "excluUseAr", "전용면적")
        apt = _tag(item, "aptNm", "아파트")
        dong = _tag(item, "umdNm", "법정동")
        if not (year and month and day and amount):
            continue
        try:
            amount_manwon = int(amount.replace(",", "").strip())
            area_f = float(area) if area else 0.0
            date_str = f"{int(year):04d}-{int(month):02d}-{int(day):02d}"
        except ValueError:
            continue
        out.append({
            "date": date_str,
            "amount_manwon": amount_manwon,
            "area": area_f,
            "apt": apt,
            "dong": dong,
        })
    return out


def unit_price(tx):
    if tx["area"] and tx["area"] > 0:
        return tx["amount_manwon"] / tx["area"]
    return None


def pct_change(cur, prev):
    if prev is None or prev == 0:
        return None
    return round((cur - prev) / prev * 100, 2)


def aggregate(transactions):
    daily_bucket = defaultdict(list)
    monthly_bucket = defaultdict(list)
    yearly_bucket = defaultdict(list)
    for tx in transactions:
        up = unit_price(tx)
        if up is None:
            continue
        daily_bucket[tx["date"]].append(up)
        monthly_bucket[tx["date"][:7]].append(up)
        yearly_bucket[tx["date"][:4]].append(up)

    def series(bucket, key_field):
        rows = []
        prev_avg = None
        for k in sorted(bucket.keys()):
            vals = bucket[k]
            avg = round(sum(vals) / len(vals), 1)
            rows.append({
                key_field: k,
                "avg_manwon_per_m2": avg,
                "count": len(vals),
                "pct": pct_change(avg, prev_avg),
            })
            prev_avg = avg
        return rows

    daily = series(daily_bucket, "date")
    monthly = series(monthly_bucket, "period")
    yearly = series(yearly_bucket, "period")

    # 대표 등락률(지도 색칠/총평용): 일별은 거래가 하루 1~2건뿐이라 평균단가가
    # 그날 거래된 아파트에 따라 ±100%씩 요동친다. 따라서 '직전(완결) 월 대비'를
    # 대표값으로 사용해 안정적이고 의미 있는 값이 되게 한다.
    # 진행 중인 현재 달은 거래가 불완전하므로 제외한다.
    latest_change = _representative_monthly_pct(monthly)
    latest_date = daily[-1]["date"] if daily else None  # 표시용: 가장 최근 실거래일
    return daily, monthly, yearly, latest_change, latest_date


def _representative_monthly_pct(monthly):
    """지도/총평용 대표 등락률 = 마지막 '완결 월'의 전월 대비 pct.
    진행 중인 현재 달(수집 시점)은 거래가 불완전하므로 건너뛴다."""
    if not monthly:
        return None
    this_month = dt.date.today().strftime("%Y-%m")
    for row in reversed(monthly):
        if row["period"] != this_month and row["pct"] is not None:
            return row["pct"]
    return monthly[-1]["pct"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--months", type=int, default=24, help="수집할 최근 개월 수 (기본 24)")
    args = ap.parse_args()

    key = load_api_key()
    months = month_list(args.months)
    session = requests.Session()

    os.makedirs(OUT_DIR, exist_ok=True)

    all_raw = {}
    result = {
        "meta": {
            "source": "국토교통부 아파트 매매 실거래가 (공공데이터포털 15126469)",
            "generated_at": dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "months_span": args.months,
            "unit": "만원/㎡ (전용면적 기준 평균 거래단가)",
            "note": "일별은 실거래 평균 기반 참고치이며 거래건수가 적은 날은 변동성이 큼",
        },
        "districts": {},
    }

    for name, code in SEOUL_DISTRICTS.items():
        print(f"[{name}] 수집 중... ({code})")
        txs = []
        for ym in months:
            got = fetch_month(session, key, code, ym)
            txs.extend(got)
            time.sleep(0.3)
        print(f"    거래 {len(txs)}건")
        all_raw[name] = txs

        daily, monthly, yearly, latest_change, latest_date = aggregate(txs)
        result["districts"][name] = {
            "code": code,
            "latest_change_pct": latest_change,
            "latest_date": latest_date,
            "daily": daily,
            "monthly": monthly,
            "yearly": yearly,
        }

    with open(os.path.join(OUT_DIR, "apartment_data.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    with open(os.path.join(OUT_DIR, "_raw_transactions.json"), "w", encoding="utf-8") as f:
        json.dump(all_raw, f, ensure_ascii=False, indent=2)

    print("\n완료 → data/apartment_data.json")
    filled = sum(1 for d in result["districts"].values() if d["daily"])
    print(f"데이터가 있는 자치구: {filled}/25")
    if filled == 0:
        print("[주의] 모든 구가 비었습니다. 인증키가 올바른지, 활용신청 승인이 됐는지 확인하세요.")


if __name__ == "__main__":
    main()