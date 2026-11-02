"""장 마감 후 실행: 국내/미국 지수와 종목 일봉(시가·고가·저가·종가)을 data/ 폴더에 저장.

사용법:
  python fetch_data.py kr --limit 50   # 국내 (나무증권 PLUG, 시총 상위 50종목만)
  python fetch_data.py us              # 미국 (S&P500 전체)

만들어지는 파일 ({m} = kr 또는 us)
  data/{m}_index_ohlc.csv  지수 일봉 (긴 표: date, code, open, high, low, close, volume)
  data/{m}_ohlc.csv        종목 일봉 (같은 형식)
  data/{m}_index.csv       지수 종가 (날짜 x 지수)
  data/{m}_close.csv       종목 종가 (날짜 x 종목)
  data/{m}_stocks.csv      종목 목록 (code, name, market)
"""
import argparse
import warnings

warnings.filterwarnings("ignore")  # yfinance·pandas 버전 경고 숨김 (동작에는 영향 없음)
import os
import pandas as pd
from dotenv import load_dotenv

# .env 를 읽고, 윈도우에서 .env.txt 로 저장된 경우도 읽어줌
load_dotenv(".env") or load_dotenv(".env.txt")


def save(market, idx_long, stk_long, stocks):
    idx_long.to_csv(f"data/{market}_index_ohlc.csv", index=False)
    stk_long.to_csv(f"data/{market}_ohlc.csv", index=False)
    idx_long.pivot(index="date", columns="code", values="close").to_csv(f"data/{market}_index.csv")
    stk_long.pivot(index="date", columns="code", values="close").to_csv(f"data/{market}_close.csv")
    stocks.to_csv(f"data/{market}_stocks.csv", index=False)
    print(f"{market} 저장 완료: 지수 {idx_long['code'].nunique()}개, 종목 {stk_long['code'].nunique()}개")


def fetch_kr(limit):
    """국내: 종목은 나무증권 PLUG, 지수(코스피·코스닥)는 yfinance."""
    import nh_client
    import us_data
    idx = us_data.ohlc_long(["^KS11", "^KQ11"], rename={"^KS11": "KOSPI", "^KQ11": "KOSDAQ"})
    stocks = nh_client.stock_list()   # 시가총액 큰 순서
    if limit:
        stocks = stocks.head(limit)   # --limit 50 이면 시총 상위 50종목
    parts = []
    for i, r in enumerate(stocks.itertuples(), 1):
        try:
            parts.append(nh_client.stock_daily(r.code, r.mrkt_cd).assign(code=r.code).reset_index())
        except Exception as e:
            print(f"{r.code} {r.name} 건너뜀: {e}")
        if i % 100 == 0:
            print(f"{i}/{len(stocks)}")
    if not parts:
        raise SystemExit("국내 종목 일봉을 하나도 못 받았어요. 위 오류 메시지를 확인해 주세요.")
    save("kr", idx, pd.concat(parts), stocks[["code", "name", "market"]])


def fetch_us(limit):
    import us_data
    idx = us_data.ohlc_long(list(us_data.US_INDEX.values()),
                            rename={v: k for k, v in us_data.US_INDEX.items()})
    tickers, names = us_data.sp500_tickers()
    if limit:
        tickers = tickers[:limit]
    stk = us_data.ohlc_long(tickers)
    stocks = pd.DataFrame({"code": tickers, "name": [names.get(t, t) for t in tickers], "market": "SP500"})
    save("us", idx, stk, stocks)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("market", choices=["kr", "us"])
    p.add_argument("--limit", type=int, default=0, help="테스트용 종목 수 제한")
    a = p.parse_args()
    os.makedirs("data", exist_ok=True)
    (fetch_kr if a.market == "kr" else fetch_us)(a.limit)
