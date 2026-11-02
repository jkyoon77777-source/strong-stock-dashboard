"""나무증권(NH투자증권) namuh PLUG Open API로 국내 종목 일봉을 받아오는 모듈.

공식 SDK(pip install nhplug)를 사용합니다. 토큰 발급·캐시·초당 호출 제한은 SDK가 처리해요.
필요한 설정(.env): NHPLUG_APP_KEY, NHPLUG_APP_SECRET
참고: https://github.com/PLUG-OpenAPI/nhplug-sdk

※ PLUG 국내주식 API에는 코스피·코스닥 '지수' 시세가 없어서, 지수는 yfinance(^KS11, ^KQ11)로 받습니다.
"""
import pandas as pd

MARKET_NAME = {"1": "KOSPI", "4": "KOSDAQ"}


def stock_list():
    """종목마스터(m_new_stock)에서 코스피·코스닥 보통 종목 목록. 시가총액 큰 순서로 정렬.
    ETF·ETN, 거래정지, 정리매매 종목은 뺍니다."""
    from nhplug.instruments import load_master
    m = load_master("m_new_stock")
    m = pd.DataFrame(m)
    m = m[m["sMarket"].isin(["1", "4"])]
    m = m[m["sUpCodeM"].str.strip().ne("000000") & m["sUpCodeM"].str.strip().ne("")]  # ETF·ETN 제외
    m = m[m["eStop"].ne("Y") & m.get("sltr_yn", pd.Series("N", index=m.index)).ne("Y")]
    m["cap"] = pd.to_numeric(m.get("prdy_avls", 0), errors="coerce").fillna(0)  # 전일 시가총액(억)
    m = m.sort_values("cap", ascending=False)
    return pd.DataFrame({
        "code": m["sCode"].str.strip(),
        "name": m["name"] if "name" in m else m["sKorName"].str.lstrip("*#").str.strip(),
        "market": m["sMarket"].map(MARKET_NAME),
        "mrkt_cd": m["sMarket"],
        "cap_억": m["cap"],
    }).reset_index(drop=True)


def _num(s):
    return pd.to_numeric(s.astype(str).str.replace(",", "").str.lstrip("+-"), errors="coerce")


def parse_period(data):
    """period 응답(Output_1) → date 인덱스의 open/high/low/close/volume 표."""
    rows = (data or {}).get("Output_1") or []
    if isinstance(rows, dict):
        rows = [rows]
    df = pd.DataFrame(rows)
    if df.empty or "bsop_date" not in df:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
    out = pd.DataFrame({
        "date": pd.to_datetime(df["bsop_date"].astype(str).str.strip(), format="%Y%m%d", errors="coerce"),
        "open": _num(df["stck_oprc"]),
        "high": _num(df["stck_hgpr"]),
        "low": _num(df["stck_lwpr"]),
        "close": _num(df["stck_prpr"]),
        "volume": _num(df["vol"]),
    }).dropna(subset=["date", "close"])
    out = out[out["close"] > 0]
    return out.sort_values("date").drop_duplicates("date").set_index("date")


def stock_daily(code, mrkt_cd="1", days=260, end=None):
    """종목 일봉 (/krstock/quote/v1/period, 정규장 기준)."""
    from nhplug import call, status_of
    end = end or pd.Timestamp.today().strftime("%Y%m%d")
    data = call("/krstock/quote/v1/period", {
        "market_cd": "KRX",
        "iem_cd": code,
        "mrkt_div_cls_code": mrkt_cd,
        "edate": end,
        "array_cnt": str(days),
        "maxavg": "0",
        "gubun": "1",            # 1 = 일봉
        "xtick": "0",
        "today_cls_code": "0",
        "fake_tick": "1",        # 거래량 0인 봉 제외
        "sur_flag": "0",
        "out1_scale_change": "0",
        "out2_scale_change": "0",
        "view_main_yn": "Y",     # 정규장 시세
    })
    df = parse_period(data)
    if df.empty:
        _, msg = status_of(data)
        raise RuntimeError(f"일봉 없음: {msg}")
    return df


def check_login():
    """토큰 발급만 시험. 성공하면 True."""
    from nhplug import get_token, get_base_url
    get_token()
    return get_base_url()
