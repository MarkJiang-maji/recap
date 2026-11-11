# Recap

**Recap is the AI agent that reconciles a patient's medications across every hospital they've visited,
with their consent, in seconds, so care teams catch dangerous gaps before they prescribe.**

Built at c0mpiled-18 (YC Startup School Hackathon, Taipei). RFS: **Plaid for Government Benefits**
(Winter 2027). It applies the same pattern, a consented verify-once data layer pulled from the source, to
health records, with an AI agent on top.

## The problem

Every time a patient enters a new care setting, someone has to reconcile their medications. Today that
means phone calls, faxes, and asking a patient who may not remember. Each hospital sees only its own
records, so the dangerous combinations sit in the gaps between them.

- US home health agencies must review every medication a new patient takes, checking for interactions,
  duplicate therapy and adverse effects ([42 CFR 484.55(c)](https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-G/part-484/subpart-B/section-484.55)).
- Medicare Part D plans already pay for Comprehensive Medication Reviews, and completion rates feed plan
  Star Ratings, yet most plans score 2 stars or less on this measure
  ([CMS technical notes](https://www.cms.gov/files/document/2023-star-ratings-technical-notes.pdf),
  [commentary](https://www.hmpgloballearningnetwork.com/site/pln/commentary/rethinking-medicare-part-d-medication-therapy-management-comprehensive)).
- Taiwan became a super-aged society at the end of 2025: 20.06% of people are 65 or older
  ([udn](https://udn.com/news/story/7266/9254576)).

## Why now

- **Patients can now pull their own data.** In Taiwan, the NHI "My Health Bank" SDK lets a patient authorize
  a third-party app to download their visits, prescriptions and lab results from every NHI hospital
  ([iThome](https://www.ithome.com.tw/news/132069)). In the US, patient-access FHIR APIs do the same.
- **AI can finally read messy records.** Free-text discharge notes, brand names and abbreviations are no
  longer a blocker.
- **AI agents need trusted patient context.** Every health agent (intake, scheduling, insurance) needs a
  consented, verifiable medical history. Recap is that layer.

## Demo scenario (synthetic data)

A 68-year-old man arrives with easy bruising and a rash. His records live in three places:

| Source | What it knows |
|---|---|
| Sunrise Medical Center (cardiology) | Warfarin for AF, amlodipine, **penicillin allergy** |
| Maple Family Clinic | Metformin, **nifedipine** added for high BP, eGFR 48 |
| Harbor City Hospital (ER) | A free-text discharge note: "Motrin 400mg… **Augmentin** 875/125…" |

Claude reads the ER note and maps the brand names to ibuprofen and amoxicillin-clavulanate. Then Recap's
rules flag what no single hospital could see:

1. **Major:** warfarin + ibuprofen: bleeding risk, which may explain the bruising
2. **Major:** penicillin allergy, yet Augmentin was given: possible cause of the rash
3. **Moderate:** two calcium channel blockers from two prescribers
4. **Moderate:** kidney function falling (eGFR 62 → 48) on metformin and an NSAID

## How it works

- `recap/engine.py`: merges consented sources and runs **deterministic** safety rules (interactions,
  allergy classes, duplicate therapy, lab trends). Alerts never depend on the LLM.
- `recap/llm.py`: Claude writes the reconciliation brief and answers questions, citing the source hospital
  for every fact.
- `recap/server.py`: Python standard-library HTTP server.
- `recap/static/index.html`: patient phone (consent) and clinician screen, side by side.

**No API key at the event:** this build ships Claude outputs written ahead of time
(`recap/data/cached_llm.json`), and the UI labels them "cached". With a key, the brief and Q&A run live.

## How Recap is different

Care-navigation companies are growing, which shows the market is real. Recap sits at a different layer:

- **The record, not the logistics.** Recap holds the cross-hospital medication record and checks it.
- **Follows the patient, not the institution.** Per-visit consent that expires; works across any provider.
- **Deterministic safety.** Alerts come from fixed rules. The AI only reads records and cites sources,
  and Recap only ever escalates: it never tells anyone they're fine.

**Taiwan already proved the value.** Taiwan's NHI cloud system gives clinicians cross-hospital records,
including medications and allergies, with proactive alerts for drug interactions, allergies and duplicate
prescriptions ([MOHW](https://www.mohw.gov.tw/cp-4250-50429-1.html), [MOHW](https://www.mohw.gov.tw/fp-16-57049-1.html),
[iThome](https://www.ithome.com.tw/news/154486)). That system is built for clinicians inside NHI providers.
Recap starts where it stops: with the patient, the family and care at home, through the NHI My Health Bank
SDK that lets patients export their own record. Single payer covers 99.9% of the population
([MOHW 2024](https://service.mohw.gov.tw/ebook/dopl/113/02/files/basic-html/page109.html)), so one
integration reaches 23 million people. Next: the US, which has no single national equivalent and where two in three hospitals still exchange records by fax ([ONC 2023](https://www.healthit.gov/sites/default/files/2024-05/Interoperable-Exchange-of-Patient-Health-Information-Among-U.S.-Hospitals-2023.pdf)), over patient-access FHIR APIs.

## Roadmap

Every step reuses the same patient-consented record.

1. **Today: cross-hospital medication reconciliation** for care teams (this demo).
2. **Patient app:** "Your record goes with you — every medication explained in plain language, with the
   questions worth asking your doctor." It is also how patients connect their records.
3. **Missed-claim alerts (Taiwan first):** "Recap matches your visits against your policies and flags claims
   you never filed — visible only to you." Claim documents travel over the industry's existing claims
   network; we don't rebuild it.
4. **Follow-up check-ins:** rule-based check-ins after a visit that alert the care team when something looks off.
5. **Vision:** the consented patient-history layer every healthcare AI agent plugs into.

**Why Taiwan first:** one integration with the NHI My Health Bank SDK covers every NHI hospital.

## Run

```bash
pip install anthropic          # only needed for live mode
export ANTHROPIC_API_KEY=...   # optional
cd recap && python3 server.py  # http://127.0.0.1:8765
```

All patient data in this repo is fictional.
