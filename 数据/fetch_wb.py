#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""并发抓取世界银行 WDI 指标（单年快照），保存到 raw/ 目录。"""
import urllib.request, json, time, os
from concurrent.futures import ThreadPoolExecutor, as_completed

OUT = os.path.join(os.path.dirname(__file__), 'raw')
os.makedirs(OUT, exist_ok=True)

# 指标 -> 中文名
INDICATORS = {
    "PA.NUS.PPPC.RF": "价格水平比率",
    "PA.NUS.PPP": "PPP转换因子",
    "PA.NUS.FCRF": "官方汇率",
    "FP.CPI.TOTL.ZG": "通胀率",
    "NY.GDP.PCAP.CD": "人均GDP",
    "NY.GNP.PCAP.CD": "人均GNI",
    "NY.GDP.MKTP.KD.ZG": "GDP增长",
    "SL.UEM.TOTL.ZS": "失业率",
    "SP.POP.TOTL": "人口",
    "PV.EST": "政治稳定",
    "RL.EST": "法治",
    "GE.EST": "政府效能",
    "RQ.EST": "监管质量",
    "CC.EST": "腐败控制",
    "NE.EXP.GNFS.ZS": "出口占GDP",
    "IT.NET.USER.ZS": "互联网普及率",
}
YEARS = ["2023", "2022", "2021"]  # 逐年回退，取每国最新有值年份

def fetch(url, timeout=180):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json'})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.load(r)
        except Exception as e:
            if attempt == 2:
                raise
            time.sleep(2 + attempt * 2)

def fetch_indicator(code):
    log = []
    for yr in YEARS:
        url = f"https://api.worldbank.org/v2/country/all/indicator/{code}?format=json&per_page=400&date={yr}"
        try:
            d = fetch(url)
            if isinstance(d, list) and len(d) > 1 and isinstance(d[1], list):
                rows = d[1]
                valid = [r for r in rows if r.get('value') is not None and r.get('countryiso3code')]
                log.append(f"{yr}:{len(valid)}国")
                if len(valid) > 50:  # 数据量足够，采用该年
                    out = os.path.join(OUT, f"{code}.json")
                    with open(out, 'w', encoding='utf-8') as f:
                        json.dump({'indicator': code, 'name_cn': INDICATORS[code], 'year': yr, 'rows': valid}, f, ensure_ascii=False)
                    return f"OK {code} ({INDICATORS[code]}) {yr} {len(valid)}国 [{' '.join(log)}]"
            else:
                log.append(f"{yr}:异常")
        except Exception as e:
            log.append(f"{yr}:失败({type(e).__name__})")
    return f"FAIL {code} ({INDICATORS[code]}) [{' '.join(log)}]"

if __name__ == '__main__':
    t0 = time.time()
    results = []
    with ThreadPoolExecutor(max_workers=8) as ex:
        futs = {ex.submit(fetch_indicator, c): c for c in INDICATORS}
        for fut in as_completed(futs):
            r = fut.result()
            results.append(r)
            print(r, flush=True)
    print(f"\n=== 全部完成，耗时 {time.time()-t0:.0f}s ===", flush=True)
    ok = sum(1 for r in results if r.startswith('OK'))
    print(f"成功 {ok}/{len(INDICATORS)}", flush=True)
