#!/usr/bin/env python
# coding: utf-8
# 读取两个文件中的ticker，去重、调整ticker格式，都在一个脚本内完成。
# 查找依据：彭博ticker；数据源：yfinance；查找指标：行业，市值，3个月日均交易量

import yfinance as yf
from curl_cffi import requests
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import os
import random
import math


_YF_SESSION = requests.Session(impersonate="chrome")
yf.config.network.proxy = "http://127.0.0.1:7890"

def retry(func, *args, retries=3, backoff=1.0, **kwargs):
    for i in range(retries):
        try:
            return func(*args, **kwargs)
        except Exception:
            if i == retries - 1:
                raise
            time.sleep(backoff * (2 ** i) + random.uniform(0, 0.5))


# ============ 本地映射：group 和 y_ticker ============

def bbg_to_cn(ticker: str) -> str:
    return ticker.split()[0].strip().zfill(6)

def _infer_yf_suffix(code: str) -> str | None:
    """根据 6 位 A 股代码推断 Yahoo 后缀"""
    if code.startswith(("600", "601", "603", "605", "688", "689")):
        return ".SS"
    if code.startswith(("000", "001", "002", "003", "300", "301")):
        return ".SZ"
    if code.startswith(("8", "4")):
        return ".BJ"
    return None
    
def yf_ticker_map(tickers: list[str]):
    """
    国内市场 ticker（如 '001391'）→ Yahoo ticker（如 '001391.SZ'）。
    直接按代码前缀推断交易所后缀，不再读本地 CSV。
    """
    yf_map = {}
    unmatched = []
    for t in tickers:
        code = bbg_to_cn(str(t))    # 兼容 '001391' / '001391 CH Equity'
        suffix = _infer_yf_suffix(code)
        if suffix:
            yf_map[code] = code + suffix
        else:
            unmatched.append(code)
    if unmatched:
        print(f"[警告] 无法推断交易所后缀的代码 {len(unmatched)} 个: {unmatched[:10]}...")
    print(f"已生成 y_ticker 映射 {len(yf_map)} 条")
    return yf_map

# ============ 逐只获取其余指标 ============

def fetch_one(ticker: str, yf_map: dict):
    key = bbg_to_cn(ticker)
    yf_ticker = yf_map.get(key)
    if not yf_ticker:
        return {
            "ticker": ticker, "symbol": key,
            "error": "y_ticker not found in mapping",
        }

    row = {"ticker": ticker, "symbol": key, "y_ticker": yf_ticker}

    # 一次 info：market_cap + sector + industry
    try:
        t = yf.Ticker(yf_ticker, session=_YF_SESSION)
        info = retry(lambda: t.info, retries=3)
        row["market_cap"] = info.get("marketCap")
        row["yf_sector"] = info.get("sector")
        row["yf_industry"] = info.get("industry")
    except Exception as e:
        row["market_cap"] = None
        row["yf_sector"] = None
        row["yf_industry"] = None
        row["error_info"] = str(e)
        t = None

    # 三个月日均成交量（fast_info，轻量）
    try:
        if t is None:
            t = yf.Ticker(yf_ticker, session=_YF_SESSION)
        row["three_month_avg_volume"] = retry(
            lambda: t.fast_info.three_month_average_volume, retries=3
        )
    except Exception as e:
        row["three_month_avg_volume"] = None
        row["error_volume"] = str(e)

    time.sleep(random.uniform(2, 4))
    return row

# ============ 主流程：并发 + 断点续跑 ============

def build_dataset(
    tickers: list,
    max_workers: int = 2,
    cache_path: str = "security_info.csv",
):
    yf_map = yf_ticker_map(tickers)   # ← 传 ticker 列表，不再传 CSV 路径

    done = {}
    if os.path.exists(cache_path):
        cached = pd.read_csv(cache_path)
        done = {row["ticker"]: row.to_dict() for _, row in cached.iterrows()}
        print(f"已加载缓存 {len(done)} 条")

    todo = [t for t in tickers if t not in done]
    print(f"待处理 {len(todo)} 个 ticker")
    if not todo:
        return pd.DataFrame(done.values())

    rows = []
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(fetch_one, t, yf_map): t for t in todo}
        for i, fut in enumerate(as_completed(futures), 1):
            t = futures[fut]
            try:
                rows.append(fut.result())
            except Exception as e:
                print(f"[失败] {t}: {e}")
                rows.append({"ticker": t})
            if i % 50 == 0:
                _flush(rows, cache_path)
                print(f"进度 {i}/{len(todo)}")

    _flush(rows, cache_path)
    all_rows = list(done.values()) + rows
    return pd.DataFrame(all_rows)

def _flush(rows, cache_path):
    if not rows:
        return
    new_df = pd.DataFrame(rows)
    if os.path.exists(cache_path):
        old_df = pd.read_csv(cache_path)
        new_df = pd.concat([old_df, new_df], ignore_index=True)
    new_df.drop_duplicates(subset="ticker", keep="last").to_csv(cache_path, index=False, encoding='utf-8-sig',)


if __name__ == "__main__":

    portfolio_df = pd.read_csv("portfolio_sample.csv", encoding='gbk')
    # 第一步：只留下stock，去除持仓中的股指期货（ticker 以 IFB、IFD、FFD 开头）
    prefixes = ("IFB", "IFD", "FFD")
    mask = ~portfolio_df["ticker"].astype(str).str.startswith(prefixes)
    portfolio_df_filtered = portfolio_df[mask]
    stock_tickers = portfolio_df_filtered["ticker"].dropna().drop_duplicates()
    stock_tickers = stock_tickers.astype(str).str.strip().str[:6]

    # 股指成分list中ticker的格式为中国市场标准六位数字格式
    constituent_df = pd.read_csv("constituent.csv")
    constituent_tickers = constituent_df["ticker"].dropna().drop_duplicates().astype(str)

    # 把 constituent_tickers 和 stock_tickers 粘在一起成 tickers
    tickers = pd.concat([constituent_tickers, stock_tickers], ignore_index=True)
    tickers = tickers.drop_duplicates().to_list()

    batch_size = 100
    i = 16
    batch = tickers[i * batch_size: (i + 1) * batch_size]
    print(f"第 {i+1} 组，共 {len(batch)} 个 ticker")

    df = build_dataset(
        batch,
        max_workers=2,
        cache_path="securityinfo_yf.csv",
    )
    print(df.head())
    print(f"总行数: {len(df)}")
