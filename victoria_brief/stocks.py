from __future__ import annotations
import sys


def fetch_stock_prices(tickers: list[str]) -> dict[str, dict]:
    """
    Fetch current price and daily change % for each ticker via yfinance.
    Returns {ticker: {"price", "change_pct", "currency"}}
    """
    try:
        import yfinance as yf
    except ImportError:
        print("  [warn] yfinance not installed — skipping stocks", file=sys.stderr)
        return {}

    prices: dict[str, dict] = {}
    for ticker in tickers:
        try:
            info = yf.Ticker(ticker).fast_info
            prev = info.previous_close
            last = info.last_price
            if prev and last:
                prices[ticker] = {
                    "price": round(last, 2),
                    "change_pct": round((last - prev) / prev * 100, 2),
                    "currency": info.currency or "CAD",
                }
        except Exception as exc:
            print(f"  [warn] Stock fetch failed for {ticker}: {exc}", file=sys.stderr)

    return prices
