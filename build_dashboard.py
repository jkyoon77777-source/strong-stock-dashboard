"""랭킹 결과로 dashboard.html 생성 (브라우저로 열면 됨).
사용법: python build_dashboard.py   (data/kr_*, data/us_* 중 있는 것 사용)
"""
import json
import os
import pandas as pd

TOP = 50
DAYS = 120  # 차트에 보여줄 거래일


def ohlc_map(path, codes, dates):
    df = pd.read_csv(path, dtype={"code": str}, parse_dates=["date"])
    df["code"] = df["code"].str.zfill(6) if df["code"].str.isdigit().all() else df["code"]
    df = df[df["code"].isin(codes) & df["date"].isin(dates)]
    out = {}
    for c, g in df.groupby("code"):
        g = g.set_index("date").reindex(dates)
        out[c] = [None if pd.isna(r.close) else [round(r.open, 2), round(r.high, 2), round(r.low, 2), round(r.close, 2)]
                  for r in g.itertuples()]
    return out


def market_payload(m):
    if not os.path.exists(f"data/{m}_ranking.csv"):
        return None
    rk = pd.read_csv(f"data/{m}_ranking.csv", index_col=0, dtype={"코드": str}).head(TOP)
    if m == "kr":
        rk["코드"] = rk["코드"].str.zfill(6)
    rk = rk.fillna({"돌파일": ""})
    idx_close = pd.read_csv(f"data/{m}_index.csv", index_col=0, parse_dates=True)
    dates = idx_close.index[-DAYS:]
    return {
        "rows": json.loads(rk.to_json(orient="records", force_ascii=False)),
        "dates": [d.strftime("%Y-%m-%d") for d in dates],
        "index": ohlc_map(f"data/{m}_index_ohlc.csv", list(idx_close.columns), dates),
        "stocks": ohlc_map(f"data/{m}_ohlc.csv", rk["코드"].tolist(), dates),
        "asof": dates[-1].strftime("%Y-%m-%d"),
    }


data = {m: market_payload(m) for m in ("kr", "us")}
html = open("dashboard_template.html", encoding="utf-8").read()
html = html.replace("/*DATA*/null", json.dumps(data, ensure_ascii=False))
open("dashboard.html", "w", encoding="utf-8").write(html)
print("dashboard.html 생성 완료")
