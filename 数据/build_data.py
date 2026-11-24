#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
整合 OWID（镜像世界银行等权威源）数据 + 城市数据 → world_data.json
核心：以中国=1 计算各国「相对物价指数」，并归一化各维度打分。
数据源全部为权威公开数据，可在页面标注来源。
"""
import csv, json, os
from collections import defaultdict
from cities_source import build as build_cities

BASE = os.path.dirname(__file__)
OWID = os.path.join(BASE, 'owid')

# 文件 -> 值列索引（第4列，index 3）
CSV_VALUE_COL = {
    'priceLevel': 3,   # GDP price levels relative to the US
    'ppp': 3,          # PPP conversion factor
    'gdpPc': 3,        # GDP per capita
    'population': 3,   # Population
    'unemployment': 3, # Unemployment rate
    'hdi': 3,          # Human Development Index
    'lifeExpectancy': 3,
    'exports': 3,
    'corruption': 3,   # Corruption Perceptions Index
}
FIELD = {
    'priceLevel':'priceLevel','ppp':'ppp','gdpPc':'gdpPc','population':'population',
    'unemployment':'unemployment','hdi':'hdi','lifeExpectancy':'lifeExpectancy',
    'exports':'exports','corruption':'corruption',
}
IND_META = {
    'priceLevel':('相对物价水平(对美国)','World Bank / ICP via OWID'),
    'ppp':('PPP转换因子','ICP / World Bank via OWID'),
    'gdpPc':('人均GDP(现价$)','World Bank via OWID'),
    'population':('人口','UN / World Bank via OWID'),
    'unemployment':('失业率(%)','ILO / World Bank via OWID'),
    'hdi':('人类发展指数','UNDP via OWID'),
    'lifeExpectancy':('预期寿命(岁)','UN / OWID'),
    'exports':('货物服务出口(2015$)','World Bank via OWID'),
    'corruption':('腐败感知指数','Transparency International via OWID'),
}

# ISO3 -> ECharts 世界地图 name（世界银行/OWID 与地图命名不一致的真实国家）
ALIAS = {
    "ATG":"Antigua and Barb.","BHS":"Bahamas","BIH":"Bosnia and Herz.","BRN":"Brunei",
    "CPV":"Cabo Verde","CAF":"Central African Rep.","COD":"Dem. Rep. Congo","COG":"Congo",
    "CIV":"Cote d'Ivoire","CZE":"Czech Rep.","DOM":"Dominican Rep.","EGY":"Egypt",
    "GNQ":"Equatorial Guinea","SWZ":"Eswatini","GMB":"Gambia","HKG":"China",
    "IRN":"Iran","KOR":"Korea","XKX":"Kosovo","KGZ":"Kyrgyzstan","MDV":"Maldives",
    "MHL":"Marshall Is.","FSM":"Micronesia","MCO":"Monaco","MKD":"Macedonia",
    "SMR":"San Marino","STP":"Sao Tome and Principe","SLB":"Solomon Is.","SOM":"Somalia",
    "KNA":"St. Kitts and Nevis","LCA":"St. Lucia","VCT":"St. Vin. and Gren.",
    "TUR":"Turkey","TUV":"Tuvalu","VEN":"Venezuela","VNM":"Vietnam","PSE":"Palestine",
    "RUS":"Russia","SVK":"Slovak Rep.","MAC":"China","PRI":"Puerto Rico","CUW":"Curacao",
    "ABW":"Aruba","CYM":"Cayman Is.","FRO":"Faroe Is.","PYF":"Fr. Polynesia",
    "GRL":"Greenland","TCA":"Turks and Caicos Is.","SXM":"Sint Maarten","NRU":"Nauru",
    "LSO":"Lesotho","SSD":"S. Sudan","TWN":"China",
}
# OWID 聚合体（非国家）
AGG = set("OWID_WRL OWID_AFR OWID_ASI OWID_EUR OWID_NAM OWID_SAM OWID_OCE OWID_EU27 OWID_LOWINC OWID_LMC OWID_UMC OWID_HIC OWID_LIC".split())

def is_iso3(code):
    return len(code)==3 and code.isalpha() and code.upper()==code

def load_latest(fname):
    """返回 {iso3: {'value':v,'year':yr,'entity':name}}，每国取最新有值年"""
    p=os.path.join(OWID,fname+'.csv')
    col=CSV_VALUE_COL[fname]
    best={}
    with open(p,encoding='utf-8') as f:
        r=csv.reader(f); next(r)
        for row in r:
            if len(row)<=col: continue
            code=row[1]; yr=row[2]; val=row[col]
            if code in AGG or not is_iso3(code) or not val: continue
            try: y=int(yr)
            except: 
                try: y=int(float(yr))
                except: continue
            if y<1990 or y>2025: continue  # 排除异常年份
            try: v=float(val)
            except: continue
            if code not in best or y>best[code]['year']:
                best[code]={'value':v,'year':y,'entity':row[0]}
    return best

def main():
    data={k:load_latest(k) for k in CSV_VALUE_COL}
    # 地图名集合
    map_names=set(f['properties']['name'] for f in json.load(open(os.path.join(BASE,'geo','world.json'),encoding='utf-8'))['features'])
    # 中国基准价格水平
    cn_pl=data['priceLevel'].get('CHN',{}).get('value')
    if not cn_pl:
        # 回退：用中国 gdpPc/ppp 估算，或直接 1
        cn_pl=1.0
    # 国家清单：以 priceLevel 为主（覆盖广），并集其他
    isos=set(data['priceLevel']) | set(data['gdpPc']) | set(data['hdi'])
    countries={}
    for iso in isos:
        enname=ALIAS.get(iso)
        if not enname:
            # 从任一数据源取实体英文名
            for k in ['priceLevel','gdpPc','hdi','population']:
                if iso in data[k]: enname=data[k][iso]['entity']; break
        if not enname: continue
        if enname not in map_names and iso in ALIAS: continue
        if enname not in map_names:
            # 尝试精确匹配失败则跳过
            continue
        rec={'iso3':iso,'nameEn':enname}
        years={}
        for k,fld in FIELD.items():
            if iso in data[k]:
                rec[fld]=round(data[k][iso]['value'],4)
                years[fld]=data[k][iso]['year']
            else:
                rec[fld]=None
        rec['years']=years
        pl=rec.get('priceLevel')
        rec['priceRatioCn']=round(pl/cn_pl,3) if (pl and cn_pl) else None
        countries[iso]=rec

    # 挂接城市
    cities=build_cities()
    by_iso=defaultdict(list)
    for c in cities: by_iso[c['iso3']].append(c)
    for iso,cl in by_iso.items():
        if iso in countries: countries[iso]['cities']=cl

    meta={
        'generated':'2026-11-17',
        'sources':'Our World in Data (镜像 World Bank WDI / ICP / UNDP / ILO / TI)，2026 快照',
        'indicators':{FIELD[k]:{'name':IND_META[k][0],'source':IND_META[k][1]} for k in FIELD},
        'cnPriceLevel':round(cn_pl,4),
        'countryCount':len(countries),
        'cityCount':sum(len(v) for v in by_iso.values()),
        'cityNote':'城市层为教学示例打分，非官方统计；国家级指标来自权威公开数据',
    }
    out={'meta':meta,'countries':list(countries.values())}
    p=os.path.join(BASE,'world_data.json')
    json.dump(out,open(p,'w',encoding='utf-8'),ensure_ascii=False,separators=(',',':'))
    print("生成:",p)
    print(f"国家数:{len(countries)} | 城市数:{meta['cityCount']} | 中国基准价:{round(cn_pl,4)}")
    for iso in ['CHN','THA','JPN','CHE','IND','USA','VNM','SGP']:
        c=countries.get(iso)
        if c: print(f"  {iso} {c['nameEn']:18s} 相对中国物价={c.get('priceRatioCn')} 人均GDP={c.get('gdpPc')} HDI={c.get('hdi')}")
    ranked=sorted([x for x in countries.values() if x.get('priceRatioCn')],key=lambda x:x['priceRatioCn'])
    print("\n最便宜8国:",[(x['nameEn'],x['priceRatioCn']) for x in ranked[:8]])
    print("最贵8国:",[(x['nameEn'],x['priceRatioCn']) for x in ranked[-8:]])
    missing=[iso for iso in by_iso if iso not in countries]
    print("\n城市所属国未匹配地图(需检查):",missing)

if __name__=='__main__':
    main()
