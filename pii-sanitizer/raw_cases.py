"""Raw (un-sanitized) notes for the end-to-end loop, with ground truth.

Built from cases.py by filling the placeholders back in with fake values.
`must_go` = every string that has to be gone after sanitizing.
"""
import re
from cases import LEAK, CLEAN

FILL = {
    "PATIENT_1": "Gerald Huang", "PATIENT_2": "Gerald Huang", "RELATIVE_1": "his wife Linda Huang",
    "DATE_1": "11/03/2026", "HOSPITAL_1": "St. Vincent Medical Center",
    "PROVIDER_1": "Dr. Amy Feld", "PROVIDER_2": "Dr. Raj Patel",
    "MRN_1": "MRN 88214477", "PHONE_1": "541-555-0119", "PHONE_2": "541-555-0177",
    "ADDRESS_1": "88 Ridgeview Ln, Albany OR 97321",
}
FILL_GONE = {  # what of each fill must disappear (provider names aren't patient PHI, keep them optional)
    "PATIENT_1": ["Gerald", "Huang"], "RELATIVE_1": ["Linda"], "DATE_1": ["11/03/2026"],
    "HOSPITAL_1": ["St. Vincent"], "MRN_1": ["88214477"], "PHONE_1": ["541-555-0119"],
    "PHONE_2": ["541-555-0177"], "ADDRESS_1": ["88 Ridgeview", "97321"],
}
LEAK_GONE = {
    "L01": ["Linda"], "L02": ["maria", "gonzalez"], "L03": ["Hope Rivers"], "L04": ["00-4471-923-X"],
    "L05": ["March 14"], "L06": ["07/22/1958"], "L07": ["415-555-0182"], "L08": ["jdoe1971@gmail.com"],
    "L09": ["1142 Alder Creek"], "L10": ["Bly"], "L11": ["97321"], "L12": ["96-year-old"],
    "L13": ["412-77-9031"], "L14": ["Tillamook Creamery"], "L15": ["784 KXM"], "L16": ["PJN204417S"],
    "L17": ["ann-whitaker"], "L18": ["73.162.44.201"], "L19": ["Bobby", "Tran"], "L20": ["Kevin", "O'Malley"],
    "L21": ["Hartwell"], "L22": ["Corvallis High"], "L23": ["XHB884712093"], "L24": ["D4471029"],
    "L25": ["503-555-0144"], "L26": [], "L27": ["10/02/2026"], "L28": ["Big Mike"],
}


def _fill(text):
    gone = []
    def sub(m):
        k = m.group(1)
        gone.extend(FILL_GONE.get(k, []))
        return FILL.get(k, m.group(0))
    return re.sub(r"\[([A-Z]+_\d)\]", sub, text), gone


RAW = []
for cid, kind, text in LEAK + CLEAN:
    raw, gone = _fill(text)
    RAW.append((cid, kind, raw, sorted(set(gone + LEAK_GONE.get(cid, [])))))
