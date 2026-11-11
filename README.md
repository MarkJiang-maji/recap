# Recap: never retell your medical history again

Every time a patient walks into a new clinic, the first minutes of the visit go to retelling:
which hospitals, which medicines, what dose, any allergies, any recent tests. Patients forget,
and records stay locked in each hospital.

**Recap is a patient-controlled AI agent for the exam room.** With one tap, the patient shares
records from every hospital they have visited. The doctor gets a 30-second brief, cross-hospital
safety alerts, and can ask questions in plain language.

Built at c0mpiled-18 (YC Startup School Hackathon, Taipei) for the YC Request for Startups
**"Plaid for Government Benefits"** (Winter 2027): the same consented, verify-once data layer, applied to
health records, with an AI agent on top.

## Demo scenario (synthetic data)

A 68-year-old man visits a new clinic with easy bruising and a rash. His records live in three places:

| Source | What it knows |
|---|---|
| Sunrise Medical Center (cardiology) | Warfarin for AF, amlodipine, **penicillin allergy** |
| Maple Family Clinic | Metformin, **nifedipine** added for high BP, eGFR 48 |
| Harbor City Hospital (ER, 9 days ago) | **Ibuprofen** and **amoxicillin-clavulanate** |

No single hospital can see the problem. Recap merges them and flags:

1. **Major:** warfarin + ibuprofen → bleeding risk (explains the bruising)
2. **Major:** penicillin allergy, but amoxicillin given (possible cause of the rash)
3. **Moderate:** two calcium channel blockers from two prescribers
4. **Moderate:** kidney function falling (eGFR 62 → 48) while on metformin and an NSAID

## How it works

- `recap/engine.py`: merges consented sources and runs **deterministic** safety rules
  (interactions, allergy classes, duplicate therapy, lab trends). Alerts don't depend on the LLM.
- `recap/llm.py`: Claude writes the 30-second brief and answers the doctor's questions, citing the source
  hospital for every fact.
- `recap/server.py`: Python standard-library HTTP server. The only dependency is `anthropic`.
- `recap/static/index.html`: patient phone (consent) and doctor screen, side by side.

## Run

```bash
pip install anthropic
export ANTHROPIC_API_KEY=...   # optional: without it, Recap runs in offline template mode
cd recap && python3 server.py  # http://127.0.0.1:8765
```

All patient data in this repo is fictional.
