#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""低速稳健抓取世界银行指标：逐个请求、超长超时、不带 date 取最新。"""
import urllib.request, json, time, os
BASE=os.path.dirname(__file__)
OUT=os.path.join(BASE,'raw'); os.makedirs(OUT,exist_ok=True)
IND={
 "PA.NUS.PPPC.RF":"价格水平比率","PA.NUS.PPP":"PPP转换因子","PA.NUS.FCRF":"官方汇率",
 "FP.CPI.TOTL.ZG":"通胀率","NY.GDP.PCAP.CD":"人均GDP","NY.GNP.PCAP.CD":"人均GNI",
 "NY.GDP.MKTP.KD.ZG":"GDP增长","SL.UEM.TOTL.ZS":"失业率","SP.POP.TOTL":"人口",
 "PV.EST":"政治稳定","RL.EST":"法治","GE.EST":"政府效能","RQ.EST":"监管质量",
 "CC.EST":"腐败控制","NE.EXP.GNFS.ZS":"出口占GDP","IT.NET.USER.ZS":"互联网普及率",
}
def fetch(code, timeout=200):
    url=f"https://api.worldbank.org/v2/country/all/indicator/{code}?format=json&per_page=300"
    req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0','Accept':'application/json'})
    with urllib.request.urlopen(req,timeout=timeout) as r:
        return json.load(r)

def pick_latest(rows):
    """按 ISO3 取每个国家最新有值的年份"""
    best={}
    for r in rows:
        iso=r.get('countryiso3code'); v=r.get('value'); yr=r.get('date')
        if not iso or len(iso)!=3 or not iso.isalpha() or v is None: continue
        if iso not in best or yr>best[iso]['date']:
            best[iso]=r
    return [best[k] for k in best]

if __name__=='__main__':
    for code,name in IND.items():
        outp=os.path.join(OUT,f'{code}.json')
        if os.path.exists(outp) and os.path.getsize(outp)>1000:
            print(f"SKIP {code} ({name}) 已存在",flush=True); continue
        ok=False
        for attempt in range(2):
            try:
                t=time.time(); d=fetch(code)
                if isinstance(d,list) and len(d)>1 and isinstance(d[1],list):
                    rows=pick_latest(d[1])
                    json.dump({'indicator':code,'name_cn':name,'year':'latest','rows':rows},
                              open(outp,'w',encoding='utf-8'),ensure_ascii=False)
                    print(f"OK {code} ({name}) {len(rows)}国 {time.time()-t:.0f}s",flush=True)
                    ok=True; break
                else:
                    print(f"WARN {code} 返回结构异常: {str(d)[:120]}",flush=True)
            except Exception as e:
                print(f"RETRY {code} 第{attempt+1}次: {type(e).__name__} {str(e)[:80]}",flush=True)
                time.sleep(3)
        if not ok: print(f"FAIL {code} ({name})",flush=True)
    print("=== 完成 ===",flush=True)
