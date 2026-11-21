"""
Step 5 — Competitor overlap model (transparent, weighted, evidence-based).

Computes a 0..100 overlap score between a focus vendor (default: August Health)
and every other vendor, using only VERIFIED data from PostgreSQL.

Dimensions and initial weights (testable assumptions, see README):
    customer segment similarity ...... 40%
    product feature similarity ....... 35%
    workflow similarity .............. 15%
    integration / use-case similarity  10%

Method:
  * Each dimension is a Jaccard similarity between the two vendors' relevant sets.
  * Feature-based dimensions count only features with availability_status =
    'confirmed'. 'unknown' is treated as missing evidence, NOT as absence.
  * If evidence coverage for either vendor is too thin, the pair is classified
    'Insufficient evidence' rather than scored low.

Classification: High >=70, Moderate 40..69, Low <40, else Insufficient evidence.
"""
from __future__ import annotations

import pandas as pd

from common import PROCESSED, connect, get_logger

log = get_logger("analyze")

WEIGHTS = {"segment": 0.40, "feature": 0.35, "workflow": 0.15, "integration": 0.10}

# Feature groupings by feature_name (must match product_features seed).
WORKFLOW_FEATURES = {"Clinical charting", "Medication management", "Scheduling"}
INTEGRATION_FEATURES = {"Pharmacy integrations", "API access", "Data export", "FHIR support"}

# Minimum share of features with positive evidence to score a vendor at all.
EVIDENCE_THRESHOLD = 0.30


def _jaccard(a: set, b: set) -> float:
    if not a and not b:
        return 0.0
    return len(a & b) / len(a | b)


def _load_frames():
    # Use plain cursors (psycopg + DataFrame) to stay dependency-light.
    with connect() as conn, conn.cursor() as cur:
        cur.execute("SELECT vendor_id, vendor_name FROM vendors")
        vendors = pd.DataFrame(cur.fetchall(), columns=["vendor_id", "vendor_name"])
        cur.execute("SELECT vendor_id, segment_id FROM vendor_segments")
        vseg = pd.DataFrame(cur.fetchall(), columns=["vendor_id", "segment_id"])
        cur.execute(
            "SELECT vf.vendor_id, pf.feature_name, pf.feature_category, vf.availability_status "
            "FROM vendor_features vf JOIN product_features pf USING (feature_id)"
        )
        vfeat = pd.DataFrame(cur.fetchall(),
                             columns=["vendor_id", "feature_name", "feature_category", "status"])
    return vendors, vseg, vfeat


def _sets_for(vendor_id, vseg, vfeat):
    segs = set(vseg[vseg.vendor_id == vendor_id]["segment_id"])
    confirmed = set(vfeat[(vfeat.vendor_id == vendor_id) & (vfeat.status == "confirmed")]["feature_name"])
    total_feats = vfeat[vfeat.vendor_id == vendor_id]["feature_name"].nunique()
    evidence = vfeat[(vfeat.vendor_id == vendor_id) & (vfeat.status != "unknown")]["feature_name"].nunique()
    coverage = evidence / total_feats if total_feats else 0.0
    return segs, confirmed, coverage


def score_against(focus_name: str = "August Health") -> pd.DataFrame:
    vendors, vseg, vfeat = _load_frames()
    name_to_id = dict(zip(vendors.vendor_name, vendors.vendor_id))
    if focus_name not in name_to_id:
        raise ValueError(f"focus vendor not found: {focus_name}")
    fid = name_to_id[focus_name]
    f_segs, f_feats, f_cov = _sets_for(fid, vseg, vfeat)

    rows = []
    for _, vr in vendors.iterrows():
        if vr.vendor_id == fid:
            continue
        c_segs, c_feats, c_cov = _sets_for(vr.vendor_id, vseg, vfeat)

        seg_sim = _jaccard(f_segs, c_segs)
        feat_sim = _jaccard(f_feats, c_feats)
        wf_sim = _jaccard(f_feats & WORKFLOW_FEATURES, c_feats & WORKFLOW_FEATURES)
        int_sim = _jaccard(f_feats & INTEGRATION_FEATURES, c_feats & INTEGRATION_FEATURES)

        score = 100 * (
            WEIGHTS["segment"] * seg_sim
            + WEIGHTS["feature"] * feat_sim
            + WEIGHTS["workflow"] * wf_sim
            + WEIGHTS["integration"] * int_sim
        )

        if min(f_cov, c_cov) < EVIDENCE_THRESHOLD:
            label = "Insufficient evidence"
        elif score >= 70:
            label = "High overlap"
        elif score >= 40:
            label = "Moderate overlap"
        else:
            label = "Low overlap"

        rows.append({
            "focus_vendor": focus_name,
            "competitor": vr.vendor_name,
            "segment_sim": round(seg_sim, 3),
            "feature_sim": round(feat_sim, 3),
            "workflow_sim": round(wf_sim, 3),
            "integration_sim": round(int_sim, 3),
            "overlap_score": round(score, 1),
            "evidence_coverage": round(min(f_cov, c_cov), 3),
            "classification": label,
        })

    df = pd.DataFrame(rows).sort_values("overlap_score", ascending=False).reset_index(drop=True)
    out = PROCESSED / "competitor_overlap.csv"
    df.to_csv(out, index=False)
    log.info("scored %d competitors vs %s -> %s", len(df), focus_name, out.name)
    return df


if __name__ == "__main__":
    result = score_against()
    print(result.to_string(index=False))
