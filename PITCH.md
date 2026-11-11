# Recap pitch (for the team)

## One line

> "Recap is the AI agent that reconciles a patient's medications across every hospital they've visited —
> with their consent, in seconds — so care teams catch dangerous gaps before they prescribe."

## 90-second video

| Time | Screen | Voice-over |
|---|---|---|
| 0–10s | Clinician screen, "Medication reconciliation needed" | "A 68-year-old man. Bruising and a rash. The cause is spread across three hospitals, and none of them can see the others. So patients retell everything, and still miss things." |
| 10–20s | Request → patient phone → Share | "With Recap, the patient shares records from every hospital with one tap. Read-only, and it expires after the visit." |
| 20–55s | Brief + the two red alerts + the ER note card | "Claude reads even a messy ER note: 'Augmentin' is a penicillin. And Recap catches what no single hospital could: a blood thinner from cardiology plus ibuprofen from the ER, which can explain the bruising. And a penicillin allergy the ER never knew about, a possible cause of the rash. Two more issues flagged below." |
| 55–65s | Click "Why might he be bruising?" | "Ask anything. Every answer cites its source hospital." |
| 65–80s | Stay on screen | "Every new patient in home health needs this review, by law. Today it's phone calls and faxes. Medicare already pays for medication reviews, and most plans score two stars on completing them." |
| 80–90s | Logo line | "Every health AI agent will need a consented, trusted medical history. Recap is that layer. It's YC's 'Plaid for benefits' pattern, applied to health records." |

Press **Reset demo** before each take. Don't say the AI is running live: this build uses cached Claude outputs.

## Judge Q&A

**How do you actually get the data?**
Taiwan: the NHI My Health Bank SDK. Patients authorize third-party apps to download their visits, meds and
labs. In 2022, 31 organizations and 64 apps already used it. US: patient-access FHIR APIs.

**Taiwan already has the NHI cloud medication system.**
That is clinician-side and limited to NHI. The data doesn't travel with the patient. Recap is
patient-carried: self-pay, clinics, care abroad. And it connects records to *today's* complaint.

**Particle Health / Health Gorilla already do interoperability.**
They sell pipes. We are the agent on the patient's side that turns records into a reconciliation in
seconds. Data access is becoming a commodity; the agent is the product.

**What if the AI is wrong? Is this a medical device?**
Safety alerts come from deterministic rules, not the LLM. The AI only reads and summarizes, every fact
cites its source, and the clinician decides.

**Who pays?**
Home health and care facilities: per intake. Then Medicare plans, which already pay for medication
reviews. Backup: families managing aging parents' medications (Taiwan passed 20% aged 65+ at the end of 2025).

**Privacy?**
Per-visit consent, read-only, expires in two hours, revocable.

Sources are in README.md. Don't quote numbers that aren't there.
