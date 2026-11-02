"""지수보다 강한 종목 스크리닝.

기준 (모두 최근 거래일 기준)
  RS20  = 종목 20일 수익률 - 지수 20일 수익률 (%p)
  RS60  = 종목 60일 수익률 - 지수 60일 수익률 (%p)
  버팀  = 최근 60일 중 지수가 하락한 날, (종목 등락률 - 지수 등락률)의 평균 (%p)
  버팀승률 = 그 하락일 중 종목이 지수보다 덜 빠지거나 오른 날의 비율 (%)

종합점수 = RS20, RS60, 버팀 각각을 0~100 백분위로 바꾼 뒤
           RS20 30% + RS60 30% + 버팀 40% 가중평균.
"강한 종목" 표시 = RS20 > 0, RS60 > 0, 버팀 > 0 을 모두 만족.

사용법: python screener.py kr   /   python screener.py us
"""
import sys
import pandas as pd

WEIGHTS = {"RS20": 0.3, "RS60": 0.3, "버팀": 0.4}
LOOKBACK = 60
PEAK_WINDOW = 120  # 전고점/저점 이탈을 찾는 기간 (거래일)
LOW_PRIOR = 60     # "직전 저점"을 찾는 이탈일 이전 기간 (거래일)


def ret(s, n):
    return (s.iloc[-1] / s.iloc[-1 - n] - 1) * 100


def score_one(stock, index):
    df = pd.concat([stock, index], axis=1, keys=["s", "i"]).dropna()
    if len(df) < LOOKBACK + 1:
        return None
    chg = df.pct_change().iloc[-LOOKBACK:] * 100
    down = chg[chg["i"] < 0]
    excess = down["s"] - down["i"]
    return {
        "종가": df["s"].iloc[-1],
        "20일수익률": ret(df["s"], 20),
        "60일수익률": ret(df["s"], 60),
        "RS20": ret(df["s"], 20) - ret(df["i"], 20),
        "RS60": ret(df["s"], 60) - ret(df["i"], 60),
        "버팀": excess.mean() if len(down) else 0.0,
        "버팀승률": (excess > 0).mean() * 100 if len(down) else 0.0,
        "지수하락일수": len(down),
        **breakout(df["s"], df["i"]),
        **support(df["s"], df["i"]),
    }


def support(s, i, window=PEAK_WINDOW, prior=LOW_PRIOR):
    """영상 방식(저점 버전): 지수는 직전 저점을 깼는데 종목은 자기 저점을 지켰는가.
    지수 이탈일 = 최근 window일 중 지수 종가 최저일 (그 전 prior일 최저 종가보다 낮아야 '이탈').
    종목 저점 = 이탈일 전 prior일 동안의 종목 최저 종가.
    종목만지지 = 이탈일부터 지금까지 종목 종가가 한 번도 자기 저점 아래로 안 내려감."""
    s, i = s.iloc[-(window + prior):], i.iloc[-(window + prior):]
    recent = i.iloc[-window:]
    low_day = recent.idxmin()
    before_i = i.loc[:low_day].iloc[:-1].iloc[-prior:]
    before_s = s.loc[:low_day].iloc[:-1].iloc[-prior:]
    if len(before_i) < 10:
        return {"지수저점이탈일": "", "지수직전저점": None, "종목저점": None, "종목저점대비": None, "종목만지지": False}
    idx_prev_low = before_i.min()
    stk_low = before_s.min()
    broke = i.loc[low_day] < idx_prev_low
    held = s.loc[low_day:].min() >= stk_low
    return {
        "지수저점이탈일": low_day.strftime("%Y-%m-%d") if broke else "",
        "지수직전저점": idx_prev_low,
        "종목저점": stk_low,
        "종목저점대비": (s.iloc[-1] / stk_low - 1) * 100,
        "종목만지지": bool(broke and held),
    }


def breakout(s, i, window=PEAK_WINDOW):
    """영상 방식: 지수는 전고점을 못 넘었는데 종목만 자기 전고점을 돌파했는가.
    지수 전고점 = 최근 window일 중 지수 종가 최고일.
    종목 기준선 = 그 날까지(포함) window일 동안의 종목 종가 최고값."""
    s, i = s.iloc[-window:], i.iloc[-window:]
    peak_day = i.idxmax()
    line = s.loc[:peak_day].max()
    after = s.loc[peak_day:].iloc[1:]
    hit = after[after > line]
    idx_gap = (i.iloc[-1] / i.max() - 1) * 100
    return {
        "지수전고점일": peak_day.strftime("%Y-%m-%d"),
        "지수전고점대비": idx_gap,
        "종목기준선": line,
        "돌파일": hit.index[0].strftime("%Y-%m-%d") if len(hit) else "",
        "종목만돌파": bool(len(hit)) and s.iloc[-1] > line and idx_gap < 0,
    }


def screen(close, index, names=None, bench=None):
    """close: 날짜 x 종목 종가, index: 날짜 x 지수 종가,
    bench: 종목별 비교 지수 이름 (없으면 index 첫 열)."""
    rows = []
    for code in close.columns:
        b = bench.get(code, index.columns[0]) if bench else index.columns[0]
        r = score_one(close[code], index[b])
        if r:
            rows.append({"코드": code, "이름": (names or {}).get(code, code), "비교지수": b, **r})
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    out["종합점수"] = sum(out[k].rank(pct=True) * 100 * w for k, w in WEIGHTS.items())
    out["RS강세"] = (out["RS20"] > 0) & (out["RS60"] > 0) & (out["버팀"] > 0)
    # 지수보다 강한 종목 = RS 강세 또는 종목만 돌파 또는 종목만 지지
    out["강한종목"] = out["RS강세"] | out["종목만돌파"] | out["종목만지지"]
    out = out.sort_values("종합점수", ascending=False).reset_index(drop=True)
    out.index += 1
    return out.round(2)


def load(market):
    close = pd.read_csv(f"data/{market}_close.csv", index_col=0, parse_dates=True)
    index = pd.read_csv(f"data/{market}_index.csv", index_col=0, parse_dates=True)
    st = pd.read_csv(f"data/{market}_stocks.csv", dtype={"code": str})
    if market == "kr":
        close.columns = [str(c).zfill(6) for c in close.columns]
    names = dict(zip(st["code"], st["name"]))
    # 코스피 종목은 코스피, 코스닥은 코스닥, 미국은 S&P500과 비교
    bench = dict(zip(st["code"], st["market"]))
    return close, index, names, bench


if __name__ == "__main__":
    market = sys.argv[1] if len(sys.argv) > 1 else "kr"
    res = screen(*load(market))
    res.to_csv(f"data/{market}_ranking.csv", encoding="utf-8-sig")
    print(res.head(20).to_string())
    print(f"\n종목만 지지 {int(res['종목만지지'].sum())}개")
    print(f"종목만 돌파 {int(res['종목만돌파'].sum())}개")
    print(f"강한 종목 {int(res['강한종목'].sum())}개 / 전체 {len(res)}개")
