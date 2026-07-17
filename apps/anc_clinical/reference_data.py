"""
anc_clinical/reference_data.py

All the numeric thresholds from your clinical spec, in one place.
LAB_REFERENCE_SEED is loaded into the LabTestReference table by the data
migration (0001_initial's RunPython) or by `manage.py seed_lab_references`.
If a clinician wants a threshold changed later, update the DB row via
/admin -- you don't need to touch this file or redeploy for that. This file
only matters the *first* time the table is populated (or if you reset it).

TEXT_TEST_RULES covers tests that come back as text/categorical rather than
numeric (urine dipstick, serology, blood group) -- these aren't stored in
LabTestReference since "reactive"/"positive" isn't a min/max comparison.
"""

AGE_RISK_MIN = 18   # < this = teenage pregnancy, high risk
AGE_RISK_MAX = 35   # >= this = advanced maternal age, high risk

# (test_code, test_name, unit, trimester, normal_min, normal_max,
#  severe_min, severe_max, flag_message_low, flag_message_high)
# trimester: 0 = Any, 1/2/3 = trimester-specific row
LAB_REFERENCE_SEED = [
    ("HB", "Hemoglobin", "g/dL", 0,
     11, None, 7, None,
     "Anemia — Hb below 11 g/dL (WHO)", None),

    ("BP_SYS", "Blood Pressure (Systolic)", "mmHg", 0,
     None, 140, None, 160,
     None, "Gestational hypertension — systolic >=140 mmHg"),

    ("BP_DIA", "Blood Pressure (Diastolic)", "mmHg", 0,
     None, 90, None, 110,
     None, "Gestational hypertension — diastolic >=90 mmHg"),

    ("SPO2", "Oxygen Saturation", "%", 0,
     95, None, 90, None,
     "Low SpO2 — below 95%", None),

    ("PULSE", "Pulse Rate", "bpm", 0,
     60, 100, 40, 130,
     "Bradycardia — pulse below 60 bpm", "Tachycardia — pulse above 100 bpm"),

    ("RFT_CREATININE", "Serum Creatinine", "mg/dL", 0,
     0.4, 0.8, None, 1.5,
     "Unusually low creatinine — verify sample", "Elevated for pregnancy (>0.8 mg/dL) — reduced renal clearance"),

    ("GCT", "Glucose Challenge Test (1hr, 50g)", "mg/dL", 0,
     None, 140, None, 200,
     None, "GCT >=140 mg/dL — needs full OGTT"),

    ("HBA1C", "HbA1c", "%", 0,
     None, 5.7, None, 6.5,
     None, "HbA1c >=5.7% borderline, >=6.5% suggests pre-existing diabetes"),

    # TSH — trimester-specific ACOG ranges
    ("TSH", "Thyroid Stimulating Hormone", "mIU/L", 1,
     0.1, 2.5, None, None,
     "Low TSH (T1) — possible hyperthyroidism", "High TSH (T1) — possible hypothyroidism"),

    ("TSH", "Thyroid Stimulating Hormone", "mIU/L", 2,
     0.2, 3.0, None, None,
     "Low TSH (T2) — possible hyperthyroidism", "High TSH (T2) — possible hypothyroidism"),

    ("TSH", "Thyroid Stimulating Hormone", "mIU/L", 3,
     0.3, 3.0, None, None,
     "Low TSH (T3) — possible hyperthyroidism", "High TSH (T3) — possible hypothyroidism"),
]

# Categorical / text-result tests. "flag_values" are the value_text entries
# (lowercased) that should be treated as flagged.
TEXT_TEST_RULES = {
    "URINE_PROTEIN": {
        "flag_values": {"plus1", "plus2", "plus3", "+1", "+2", "+3"},
        "severity": "moderate",
        "reason": "Proteinuria (>=1+) — correlate with BP, possible pre-eclampsia",
    },
    "URINE_GLUCOSE": {
        "flag_values": {"plus1", "plus2", "plus3", "+1", "+2", "+3"},
        "severity": "moderate",
        "reason": "Glycosuria — needs GCT/OGTT workup for gestational diabetes",
    },
    "HIV": {
        "flag_values": {"reactive"},
        "severity": "severe",
        "reason": "HIV reactive — refer for specialist management",
    },
    "HBSAG": {
        "flag_values": {"reactive"},
        "severity": "severe",
        "reason": "HBsAg reactive — refer for specialist management",
    },
    "VDRL": {
        "flag_values": {"reactive"},
        "severity": "severe",
        "reason": "VDRL reactive — refer for specialist management",
    },
}
