"""미국 지수/종목 일봉 (yfinance, 무료)."""
import io
import pandas as pd
import requests
import yfinance as yf

US_INDEX = {"SP500": "^GSPC", "NASDAQ": "^IXIC"}
FIELDS = ["Open", "High", "Low", "Close", "Volume"]


def sp500_tickers():
    """S&P500 구성종목 (위키백과 표)."""
    html = requests.get("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies",
                        headers={"User-Agent": "Mozilla/5.0"}, timeout=15).text
    t = pd.read_html(io.StringIO(html))[0]
    return t["Symbol"].str.replace(".", "-", regex=False).tolist(), dict(zip(
        t["Symbol"].str.replace(".", "-", regex=False), t["Security"]))


def ohlc_long(tickers, period="1y", rename=None):
    """반환: date, code, open, high, low, close, volume 의 긴 표."""
    tickers = [tickers] if isinstance(tickers, str) else list(tickers)
    df = yf.download(tickers, period=period, auto_adjust=True, progress=False,
                     threads=True, group_by="column")
    parts = []
    for t in tickers:
        try:
            one = pd.DataFrame({f.lower(): df[f][t] for f in FIELDS}).dropna(subset=["close"])
        except KeyError:
            continue
        one["code"] = (rename or {}).get(t, t)
        parts.append(one)
    out = pd.concat(parts)
    out.index.name = "date"
    return out.reset_index()[["date", "code", "open", "high", "low", "close", "volume"]]
