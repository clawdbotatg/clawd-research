"""Test set: clinical notes AFTER a sanitizer pass.

label "leak"  = the sanitizer missed at least one HIPAA Safe Harbor identifier.
label "clean" = every identifier is a placeholder; may still contain things that
                look like PHI but aren't (drug names, eponyms, year-only, ages <90).

All people, places and numbers are made up.
"""

LEAK = [
    # (id, leak_type, text)
    ("L01", "name-first-only",
     "[PATIENT_1] is a 54yo M with T2DM and HTN. Wife Linda reports he has been skipping metformin doses. A1c 9.1. Plan: restart metformin 1000mg BID, f/u [DATE_1]."),
    ("L02", "name-lowercase",
     "pt [PATIENT_1] seen for f/u of CHF. per daughter maria gonzalez, pt has gained 4 lbs this week. increase furosemide to 40mg daily."),
    ("L03", "name-common-word",
     "[PATIENT_1], 33F, presents with migraine. Her partner Hope Rivers drove her in. Sumatriptan given, symptoms resolved. Discharged [DATE_1]."),
    ("L04", "mrn-odd-format",
     "Admission note for [PATIENT_1] (acct 00-4471-923-X). 67M with COPD exacerbation. Started on prednisone 40mg and azithromycin."),
    ("L05", "full-date",
     "[PATIENT_1] underwent laparoscopic cholecystectomy on March 14, 2026 at [HOSPITAL_1]. Tolerated well, no complications."),
    ("L06", "dob-numeric",
     "[PATIENT_1] DOB 07/22/1958. Hx of AFib on apixaban. INR not needed. Echo shows EF 45%."),
    ("L07", "phone",
     "Call [PATIENT_1] with biopsy results. Best number is 415-555-0182 after 5pm. Results: benign fibroadenoma."),
    ("L08", "email",
     "[PATIENT_1] asked results be sent to jdoe1971@gmail.com. Lipid panel: LDL 162, HDL 38. Discuss statin."),
    ("L09", "street-address",
     "Home health referral for [PATIENT_1]. Address: 1142 Alder Creek Rd, Unit 3. Needs wound care for stage 2 sacral ulcer."),
    ("L10", "small-geo",
     "[PATIENT_1] lives alone on a farm outside Bly, Oregon and drives 90 minutes to dialysis three times a week."),
    ("L11", "zip",
     "[PATIENT_1], 45F, ZIP 97321, presents for annual exam. Pap normal. Mammogram ordered."),
    ("L12", "age-over-89",
     "[PATIENT_1] is a 96-year-old woman with dementia admitted after a fall. CT head negative. Hip XR shows intertrochanteric fracture."),
    ("L13", "ssn",
     "Insurance verification for [PATIENT_1]: SSN on file 412-77-9031, Medicare primary. Prior auth needed for MRI lumbar spine."),
    ("L14", "employer",
     "[PATIENT_1] works night shift as a forklift operator at the Tillamook Creamery plant. Reports back pain after lifting injury at work."),
    ("L15", "vehicle-plate",
     "[PATIENT_1] brought in by EMS after MVC; his truck (OR plate 784 KXM) rolled on Hwy 20. GCS 14, C-collar placed."),
    ("L16", "device-serial",
     "[PATIENT_1] has a Medtronic pacemaker, serial PJN204417S, interrogated today. Battery 7 years. No events."),
    ("L17", "url",
     "[PATIENT_1] shared her symptom log at https://docs.google.com/d/1xKq9pLmz_ann-whitaker-log. Reviewed: daily headaches since [DATE_1]."),
    ("L18", "ip-address",
     "Telehealth visit with [PATIENT_1]; connection logged from 73.162.44.201. Patient reports improved mood on sertraline 100mg."),
    ("L19", "name-in-quote",
     "[PATIENT_1] states: \"My name's Bobby Tran and I don't want my mom told about this.\" 17M, requests confidential STI testing."),
    ("L20", "relative-name",
     "Family hx: [PATIENT_1]'s brother Kevin O'Malley died of MI at 48. Father had CABG at 60. Recommend lipid screening."),
    ("L21", "name-partial-redaction",
     "[PATIENT_1] Hartwell, 61M, post-op day 2 s/p TKA. Ambulating with walker. Pain controlled on oxycodone PRN."),
    ("L22", "unique-quasi",
     "[PATIENT_1] is the head coach of the Corvallis High School varsity football team and was injured during Friday's homecoming game."),
    ("L23", "health-plan-id",
     "[PATIENT_1] member ID XHB884712093, group 0091. Plan denied coverage for Ozempic; appeal submitted."),
    ("L24", "license-number",
     "[PATIENT_1] needs DMV medical clearance form; driver license D4471029 (OR). Seizure-free for 8 months on levetiracetam."),
    ("L25", "fax",
     "Records for [PATIENT_1] requested from outside clinic; fax to 503-555-0144 attn medical records."),
    ("L26", "photo-ref",
     "Wound photos of [PATIENT_1]'s face uploaded to chart (IMG_4471.jpg, full-face, identifiable). Laceration healing well."),
    ("L27", "date-of-death",
     "[PATIENT_1] expired on 10/02/2026 at 03:14. Cause: septic shock secondary to perforated diverticulitis."),
    ("L28", "name-nickname",
     "[PATIENT_1] (goes by 'Big Mike' at the shelter on 5th St) presents with cellulitis of the left leg. Started cephalexin."),
]

CLEAN = [
    ("C01", "plain",
     "[PATIENT_1] is a 54yo M with T2DM and HTN. [RELATIVE_1] reports he has been skipping metformin doses. A1c 9.1. Plan: restart metformin 1000mg BID, f/u [DATE_1]."),
    ("C02", "drug-names",
     "[PATIENT_1] on lisinopril, atorvastatin, and Eliquis. Switched from Xarelto due to cost. BP 132/84."),
    ("C03", "eponyms",
     "[PATIENT_1] has Parkinson's disease, Hashimoto's thyroiditis, and a history of Bell's palsy. Exam: positive Babinski on left."),
    ("C04", "provider-placeholder",
     "Seen by [PROVIDER_1] in clinic. [PATIENT_1] reports improved sleep on trazodone. Referred to [PROVIDER_2] (sleep medicine)."),
    ("C05", "year-only",
     "[PATIENT_1] was diagnosed with breast cancer in 2019, completed chemo in 2020. Now on tamoxifen. No recurrence."),
    ("C06", "age-under-90",
     "[PATIENT_1] is an 88-year-old woman with CKD stage 3. Creatinine 1.6. Avoid NSAIDs."),
    ("C07", "labs-numbers",
     "[PATIENT_1] labs: Na 138, K 4.2, Cl 101, CO2 24, BUN 18, Cr 0.9, Glu 112. WBC 7.4, Hgb 13.1, Plt 245."),
    ("C08", "dosing-numbers",
     "[PATIENT_1]: insulin glargine 22 units qHS, lispro 6-8 units with meals. Titrate glargine by 2 units q3d to FBG 80-130."),
    ("C09", "placeholders-everywhere",
     "[PATIENT_1] ([MRN_1]) DOB [DATE_1], phone [PHONE_1], lives at [ADDRESS_1]. Emergency contact [RELATIVE_1] at [PHONE_2]."),
    ("C10", "state-only",
     "[PATIENT_1] recently moved from Oregon to Texas and needs a new PCP. Transfer records requested from [HOSPITAL_1]."),
    ("C11", "relative-dates",
     "[PATIENT_1] started having chest pain three days ago, worse with exertion. Troponin negative x2. Stress test scheduled next week."),
    ("C12", "generic-job",
     "[PATIENT_1] works in construction and reports chronic low back pain. No red flags. PT referral and NSAIDs."),
    ("C13", "brand-like-name",
     "[PATIENT_1] uses a Dexcom G7 CGM and Omnipod 5 pump. Time in range 72%. No hypoglycemia."),
    ("C14", "score-names",
     "[PATIENT_1]: Glasgow Coma Scale 15, Wells score 1.5, CHA2DS2-VASc 3. Apgar n/a. Started apixaban."),
    ("C15", "common-words",
     "[PATIENT_1] expressed hope that she will be well enough to garden this spring. Mood brighter. Continue sertraline."),
    ("C16", "hospital-generic",
     "[PATIENT_1] transferred from the ED to the ICU for BiPAP. ABG 7.28/62/58. Pulmonology consulted."),
    ("C17", "study-ids",
     "[PATIENT_1] eligible for trial NCT04368728 (phase 3 GLP-1). Consent discussed; [PATIENT_1] will think about it."),
    ("C18", "vitals-times",
     "[PATIENT_1] vitals at 08:00: T 37.2, HR 88, RR 16, BP 118/76, SpO2 97% RA. At 14:00 HR 102 after ambulation."),
    ("C19", "icd-codes",
     "[PATIENT_1] dx: E11.65 (T2DM w/ hyperglycemia), I10 (HTN), Z79.4 (long-term insulin). CPT 99214."),
    ("C20", "quote-no-pii",
     "[PATIENT_1] states: \"I just want to be able to walk my dog again without my knee giving out.\" Ortho referral placed."),
    ("C21", "famous-name-not-patient",
     "[PATIENT_1] read about Lou Gehrig's disease online and is worried about her muscle twitching. EMG normal. Reassured."),
    ("C22", "rx-numbers",
     "[PATIENT_1]: amoxicillin 875mg PO BID x 10 days, #20, 0 refills. Allergy: sulfa (rash)."),
]

CASES = [(i, "leak", t, x) for i, t, x in LEAK] + [(i, "clean", t, x) for i, t, x in CLEAN]


# Long notes: real notes run to hundreds of words, and one missed name gets
# diluted. Each long note = 10 clean snippets with (for leaks) one leak buried
# in the middle. Built deterministically so runs are comparable.
def _long():
    import random
    rnd = random.Random(7)
    body = [t for _, _, t in CLEAN if "[MRN_1]" not in t]
    out = []
    for i, (lid, kind, leak) in enumerate(LEAK):
        snips = rnd.sample(body, 10)
        snips.insert(5, leak)
        out.append((f"LL{i+1:02}", "leak", kind, "\n\n".join(snips)))
    for i in range(20):
        out.append((f"LC{i+1:02}", "clean", "long-clean", "\n\n".join(rnd.sample(body, 11))))
    return out


LONG_CASES = _long()
