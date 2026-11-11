"""Deterministic record merging and safety checks.

The safety alerts come from fixed rules, not from the LLM, so they are
reproducible and work without an API key. The LLM only writes the brief and
answers questions on top of these results.
"""
import datetime as dt

# Small demo rule tables. A real product would use a licensed drug database.
INTERACTIONS = [
    {
        "a": {"warfarin"},
        "b": {"ibuprofen", "naproxen", "diclofenac", "aspirin"},
        "severity": "major",
        "title": "Bleeding risk: warfarin + NSAID",
        "detail": "NSAIDs raise bleeding risk in patients on warfarin and can push INR up.",
        "action": "Stop the NSAID; check INR today; use acetaminophen for pain.",
    },
]

ALLERGY_CLASSES = {
    "penicillin": {"penicillin", "amoxicillin", "amoxicillin-clavulanate", "ampicillin"},
}

DUPLICATE_CLASSES = {"dihydropyridine calcium channel blocker", "anticoagulant", "NSAID", "statin"}


def _d(s):
    return dt.date.fromisoformat(s)


def _key(drug):
    return drug.lower().replace(" xl", "").strip()


def _end(rx):
    if rx.get("days") is None:
        return None
    return _d(rx["start"]) + dt.timedelta(days=rx["days"] - 1)


def merge(record, source_ids):
    """Merge the consented sources into one timeline."""
    today = _d(record["today"]["date"])
    meds, recent, allergies, diagnoses, encounters, labs = [], [], [], [], [], []
    for src in record["sources"]:
        if src["id"] not in source_ids:
            continue
        tag = {"source_id": src["id"], "source": src["name"]}
        for rx in src["prescriptions"]:
            item = dict(rx, **tag)
            end = _end(rx)
            item["end"] = end.isoformat() if end else None
            if _d(rx["start"]) <= today and (end is None or end >= today):
                item["status"] = "active"
                meds.append(item)
            elif end is not None and (today - end).days <= 30:
                item["status"] = "recently finished"
                recent.append(item)
        allergies += [dict(a, **tag) for a in src["allergies"]]
        diagnoses += [dict(x, **tag) for x in src["diagnoses"]]
        encounters += [dict(x, **tag) for x in src["encounters"]]
        labs += [dict(x, **tag) for x in src["labs"]]
    encounters.sort(key=lambda e: e["date"], reverse=True)
    labs.sort(key=lambda x: x["date"])
    return {
        "patient": record["patient"],
        "today": record["today"],
        "active_meds": meds,
        "recent_meds": recent,
        "allergies": allergies,
        "diagnoses": diagnoses,
        "encounters": encounters,
        "labs": labs,
    }


def alerts(merged):
    out = []
    meds = merged["active_meds"]
    exposures = meds + merged["recent_meds"]

    for rule in INTERACTIONS:
        hits_a = [m for m in meds if _key(m["drug"]) in rule["a"]]
        hits_b = [m for m in meds if _key(m["drug"]) in rule["b"]]
        for a in hits_a:
            for b in hits_b:
                out.append({
                    "severity": rule["severity"],
                    "kind": "Drug interaction",
                    "title": rule["title"],
                    "detail": "%s (%s) + %s (%s). %s" % (a["drug"], a["source"], b["drug"], b["source"], rule["detail"]),
                    "action": rule["action"],
                    "sources": sorted({a["source"], b["source"]}),
                })

    for al in merged["allergies"]:
        cls = ALLERGY_CLASSES.get(al["substance"].lower(), {al["substance"].lower()})
        for m in exposures:
            if _key(m["drug"]) in cls:
                out.append({
                    "severity": "major",
                    "kind": "Allergy conflict",
                    "title": "%s allergy, but given %s" % (al["substance"], m["drug"]),
                    "detail": "%s allergy (%s, recorded %s, at %s). %s was prescribed on %s at %s, which did not have this allergy on file." % (
                        al["substance"], al["reaction"], al["recorded"], al["source"], m["drug"], m["start"], m["source"]),
                    "action": "Consider drug reaction as cause of current rash; update allergy list everywhere.",
                    "sources": sorted({al["source"], m["source"]}),
                })

    by_class = {}
    for m in meds:
        if m["class"] in DUPLICATE_CLASSES:
            by_class.setdefault(m["class"], []).append(m)
    for cls, ms in by_class.items():
        if len(ms) > 1 and len({m["source"] for m in ms}) > 1:
            out.append({
                "severity": "moderate",
                "kind": "Duplicate therapy",
                "title": "Two %ss from two prescribers" % cls,
                "detail": "; ".join("%s %s (%s, since %s)" % (m["drug"], m["dose"], m["source"], m["start"]) for m in ms) + ".",
                "action": "Keep one; the second was likely added without knowing about the first.",
                "sources": sorted({m["source"] for m in ms}),
            })

    egfr = [x for x in merged["labs"] if x["name"] == "eGFR"]
    if len(egfr) >= 2 and egfr[-1]["value"] < egfr[0]["value"] * 0.85:
        risky = [m["drug"] for m in meds if m["class"] in ("NSAID", "biguanide")]
        out.append({
            "severity": "moderate",
            "kind": "Lab trend",
            "title": "Kidney function falling: eGFR %s → %s" % (egfr[0]["value"], egfr[-1]["value"]),
            "detail": "eGFR %s on %s (%s) → %s on %s (%s). Kidney-relevant active meds: %s." % (
                egfr[0]["value"], egfr[0]["date"], egfr[0]["source"],
                egfr[-1]["value"], egfr[-1]["date"], egfr[-1]["source"], ", ".join(risky) or "none"),
            "action": "Recheck renal function; review metformin dose; avoid NSAIDs.",
            "sources": sorted({egfr[0]["source"], egfr[-1]["source"]}),
        })

    rank = {"major": 0, "moderate": 1, "minor": 2}
    out.sort(key=lambda a: rank.get(a["severity"], 9))
    return out


def fallback_brief(merged, found):
    """Template brief used when no LLM key is configured."""
    p, t = merged["patient"], merged["today"]
    lines = [
        "%s, %d%s. Today: %s" % (p["name"], p["age"], p["sex"], t["reason"]),
        "Problems: " + ", ".join(sorted({d["name"] for d in merged["diagnoses"]})) + ".",
        "Active meds (%d, from %d places): " % (len(merged["active_meds"]), len({m["source"] for m in merged["active_meds"]}))
        + ", ".join("%s %s" % (m["drug"], m["dose"]) for m in merged["active_meds"]) + ".",
        "Allergies: " + (", ".join("%s (%s)" % (a["substance"], a["reaction"]) for a in merged["allergies"]) or "none on file") + ".",
    ]
    if found:
        lines.append("Most important: " + found[0]["title"] + ". " + found[0]["action"])
    return "\n".join(lines)
