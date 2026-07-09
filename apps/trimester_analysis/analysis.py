
"""
Enhanced trimester analysis engine for Meri Aama.

Drop-in replacement scaffold. Extend rule blocks as needed.
"""
from collections import defaultdict

TRIMESTER_RANGES={1:(1,13),2:(14,27),3:(28,45)}
FHR_NORMAL_RANGE=(110,160)
HEMOGLOBIN_LOW_THRESHOLD=11.0
BP_HIGH_THRESHOLD=(140,90)
BP_ELEVATED_THRESHOLD=(130,80)

def get_trimester(week):
    if week is None: return None
    if week<=13: return 1
    if week<=27: return 2
    return 3

def parse_bp(bp):
    try:
        s,d=bp.split("/")
        return int(s),int(d)
    except Exception:
        return None

def change(cur,prev):
    if cur is None or prev is None:
        return None
    diff=round(float(cur)-float(prev),1)
    return {
        "value":diff,
        "direction":"up" if diff>0 else "down" if diff<0 else "same"
    }

def build_timeline(visits):
    out=[]
    prev=None
    for v in visits:
        item={
            "visit":v,
            "week":v.gestational_week,
            "date":v.visit_date,
            "changes":{}
        }
        if prev:
            item["changes"]["weight"]=change(v.maternal_weight_kg,prev.maternal_weight_kg)
            item["changes"]["fundal_height"]=change(v.fundal_height_cm,prev.fundal_height_cm)
            item["changes"]["hemoglobin"]=change(v.hemoglobin_g_dl,prev.hemoglobin_g_dl)
            if v.fetal_heart_rate_bpm and prev.fetal_heart_rate_bpm:
                item["changes"]["fhr"]=change(v.fetal_heart_rate_bpm,prev.fetal_heart_rate_bpm)
        out.append(item)
        prev=v
    return out

def build_chart_data(visits):
    charts={"weeks":[],"weight":[],"hb":[],"fundal":[],"fhr":[],"sys":[],"dia":[]}
    for v in visits:
        if v.gestational_week is None: continue
        charts["weeks"].append(v.gestational_week)
        charts["weight"].append(float(v.maternal_weight_kg) if v.maternal_weight_kg is not None else None)
        charts["hb"].append(float(v.hemoglobin_g_dl) if v.hemoglobin_g_dl is not None else None)
        charts["fundal"].append(float(v.fundal_height_cm) if v.fundal_height_cm is not None else None)
        charts["fhr"].append(v.fetal_heart_rate_bpm)
        bp=parse_bp(v.blood_pressure)
        if bp:
            charts["sys"].append(bp[0]); charts["dia"].append(bp[1])
        else:
            charts["sys"].append(None); charts["dia"].append(None)
    return charts

def analyze_trimester(trimester, visits):
    visits=sorted(visits,key=lambda x:(x.gestational_week or 0,x.visit_date))
    flags=[]
    weights=[float(v.maternal_weight_kg) for v in visits if v.maternal_weight_kg is not None]
    ws=weights[0] if weights else None
    we=weights[-1] if weights else None
    wc=round(we-ws,1) if len(weights)>=2 else None

    for v in visits:
        bp=parse_bp(v.blood_pressure)
        if bp:
            if bp[0]>=BP_HIGH_THRESHOLD[0] or bp[1]>=BP_HIGH_THRESHOLD[1]:
                flags.append({"severity":"concern","message":f"Week {v.gestational_week}: BP {bp[0]}/{bp[1]} recorded."})
            elif bp[0]>=BP_ELEVATED_THRESHOLD[0] or bp[1]>=BP_ELEVATED_THRESHOLD[1]:
                flags.append({"severity":"caution","message":f"Week {v.gestational_week}: Mild BP elevation."})
        if v.hemoglobin_g_dl is not None and float(v.hemoglobin_g_dl)<HEMOGLOBIN_LOW_THRESHOLD:
            flags.append({"severity":"caution","message":f"Week {v.gestational_week}: Hemoglobin {v.hemoglobin_g_dl} g/dL."})
        if v.fetal_heart_rate_bpm and not(FHR_NORMAL_RANGE[0]<=v.fetal_heart_rate_bpm<=FHR_NORMAL_RANGE[1]):
            flags.append({"severity":"concern","message":f"Week {v.gestational_week}: FHR outside expected range."})
        if v.urine_protein in ("plus1","plus2","plus3"):
            flags.append({"severity":"concern","message":"Protein detected in urine."})

    return {
        "trimester_num":trimester,
        "visit_count":len(visits),
        "weight_start":ws,
        "weight_end":we,
        "weight_change":wc,
        "timeline":build_timeline(visits),
        "charts":build_chart_data(visits),
        "flags":flags
    }

def build_full_analysis(all_visits):
    buckets=defaultdict(list)
    for v in all_visits:
        t=get_trimester(v.gestational_week)
        if t: buckets[t].append(v)
    return [analyze_trimester(t,buckets[t]) for t in (1,2,3)]

def generate_narrative_prompt(trimester_results):
    lines=[]
    for t in trimester_results:
        lines.append(f"Trimester {t['trimester_num']}: {t['visit_count']} visits.")
        if t["weight_change"] is not None:
            lines.append(f"Weight change: {t['weight_change']} kg.")
        for f in t["flags"]:
            lines.append(f"- {f['severity']}: {f['message']}")
    system=(
        "You are a compassionate maternal health assistant. "
        "Summarize ONLY supplied facts. Organize output with headings "
        "Overall Progress, Trimester 1, Trimester 2, Trimester 3, Positive Signs, "
        "Things to Discuss with Doctor, Next Visit Advice. Never diagnose or invent facts."
    )
    return system,"\n".join(lines)
