"""
EHR Market Intelligence — Streamlit dashboard (3 pages).

  1. EHR Market Overview
  2. Competitive Intelligence
  3. Data Engineering Monitor

Run:  streamlit run dashboard/app.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

# allow importing src/ helpers
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from common import connect  # noqa: E402
import analyze_competitors  # noqa: E402

st.set_page_config(page_title="EHR Market Intelligence", layout="wide")


@st.cache_data(ttl=300)
def q(sql: str, params: tuple | None = None) -> pd.DataFrame:
    with connect() as conn, conn.cursor() as cur:
        cur.execute(sql, params or ())
        cols = [d[0] for d in cur.description]
        return pd.DataFrame(cur.fetchall(), columns=cols)


# ---------------------------------------------------------------------------
def page_overview() -> None:
    st.title("EHR Market Overview")

    vendors = q("SELECT vendor_id, vendor_name FROM vendors ORDER BY vendor_name")
    segments = q("SELECT segment_name FROM market_segments ORDER BY segment_name")

    c1, c2, c3 = st.columns(3)
    c1.metric("Vendors tracked", len(vendors))
    c2.metric("Market segments", len(segments))
    c3.metric("Sources cited", q("SELECT COUNT(*) n FROM sources")["n"][0])

    chosen = st.multiselect("Filter by healthcare segment",
                            segments["segment_name"].tolist())

    st.subheader("Vendor market coverage")
    cov = q("""
        SELECT v.vendor_name,
               STRING_AGG(ms.segment_name, ', ' ORDER BY ms.segment_name) AS segments,
               COUNT(vs.segment_id) AS segments_served
        FROM vendors v
        LEFT JOIN vendor_segments vs USING (vendor_id)
        LEFT JOIN market_segments ms USING (segment_id)
        GROUP BY v.vendor_name
        ORDER BY segments_served DESC, v.vendor_name
    """)
    if chosen:
        mask = cov["segments"].fillna("").apply(lambda s: any(c in s for c in chosen))
        cov = cov[mask]
    st.dataframe(cov, use_container_width=True, hide_index=True)

    st.subheader("Acute-care hospital EHR market share (as reported by KLAS)")
    st.caption("Hospital share only. Not comparable to senior-living footprint counts.")
    share = q("""
        SELECT v.vendor_name, m.metric_value AS market_share_pct, m.measurement_year
        FROM market_metrics m JOIN vendors v USING (vendor_id)
        WHERE m.metric_name = 'acute_care_ehr_market_share'
        ORDER BY m.metric_value DESC
    """)
    if not share.empty:
        fig = px.bar(share, x="vendor_name", y="market_share_pct",
                     text="market_share_pct", labels={"vendor_name": "", "market_share_pct": "% share"})
        fig.update_traces(textposition="outside")
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Senior living / LTPAC reported footprint (self-reported)")
    st.caption("Self-reported facility/community counts. A different measure than hospital share.")
    foot = q("""
        SELECT v.vendor_name, m.metric_value, m.metric_unit, m.measurement_year
        FROM market_metrics m JOIN vendors v USING (vendor_id)
        WHERE m.metric_name IN ('reported_customer_facilities','reported_customer_communities')
        ORDER BY m.metric_value DESC NULLS LAST
    """)
    st.dataframe(foot, use_container_width=True, hide_index=True)


# ---------------------------------------------------------------------------
def page_competitive() -> None:
    st.title("Competitive Intelligence")

    vendors = q("SELECT vendor_name FROM vendors ORDER BY vendor_name")["vendor_name"].tolist()
    c1, c2 = st.columns(2)
    v1 = c1.selectbox("Vendor A", vendors, index=vendors.index("August Health"))
    v2 = c2.selectbox("Vendor B", vendors, index=vendors.index("Epic Systems"))

    st.subheader(f"Feature comparison — {v1} vs {v2}")
    feat = q("""
        SELECT pf.feature_category, pf.feature_name,
               MAX(CASE WHEN v.vendor_name = %s THEN vf.availability_status END) AS vendor_a,
               MAX(CASE WHEN v.vendor_name = %s THEN vf.availability_status END) AS vendor_b
        FROM product_features pf
        LEFT JOIN vendor_features vf USING (feature_id)
        LEFT JOIN vendors v USING (vendor_id)
        WHERE v.vendor_name IN (%s, %s)
        GROUP BY pf.feature_category, pf.feature_name
        ORDER BY pf.feature_category, pf.feature_name
    """, (v1, v2, v1, v2))
    feat = feat.rename(columns={"vendor_a": v1, "vendor_b": v2})
    st.dataframe(feat, use_container_width=True, hide_index=True)

    st.subheader("Customer segment overlap")
    seg = q("""
        SELECT ms.segment_name,
               BOOL_OR(v.vendor_name = %s) AS vendor_a,
               BOOL_OR(v.vendor_name = %s) AS vendor_b
        FROM market_segments ms
        LEFT JOIN vendor_segments vs USING (segment_id)
        LEFT JOIN vendors v USING (vendor_id)
        GROUP BY ms.segment_name
        ORDER BY ms.segment_name
    """, (v1, v2))
    seg = seg.rename(columns={"vendor_a": v1, "vendor_b": v2})
    st.dataframe(seg, use_container_width=True, hide_index=True)

    st.subheader("Competitive similarity score")
    st.caption("Transparent weighted model: 40% segment + 35% features + 15% workflow + 10% integration. "
               "Only verified data; 'unknown' is treated as missing, not absent.")
    scores = analyze_competitors.score_against(v1)
    row = scores[scores["competitor"] == v2]
    if not row.empty:
        r = row.iloc[0]
        m1, m2, m3 = st.columns(3)
        m1.metric("Overlap score (0-100)", r["overlap_score"])
        m2.metric("Classification", r["classification"])
        m3.metric("Evidence coverage", f"{r['evidence_coverage']*100:.0f}%")
        st.dataframe(row[["segment_sim", "feature_sim", "workflow_sim", "integration_sim"]],
                     use_container_width=True, hide_index=True)
    st.markdown(f"**Full ranking vs {v1}:**")
    st.dataframe(scores, use_container_width=True, hide_index=True)

    st.subheader("Evidence & sources")
    ev = q("""
        SELECT v.vendor_name, pf.feature_name, vf.availability_status,
               vf.verified_date, src.source_name, src.source_url
        FROM vendor_features vf
        JOIN vendors v USING (vendor_id)
        JOIN product_features pf USING (feature_id)
        LEFT JOIN sources src USING (source_id)
        WHERE v.vendor_name IN (%s, %s) AND vf.availability_status <> 'unknown'
        ORDER BY v.vendor_name, pf.feature_name
    """, (v1, v2))
    st.dataframe(ev, use_container_width=True, hide_index=True,
                 column_config={"source_url": st.column_config.LinkColumn("source_url")})


# ---------------------------------------------------------------------------
def page_monitor() -> None:
    st.title("Data Engineering Monitor")

    runs = q("""
        SELECT run_id, pipeline_name, start_time, end_time, status,
               records_processed, records_rejected, error_message
        FROM pipeline_runs ORDER BY start_time DESC LIMIT 10
    """)
    if not runs.empty:
        last = runs.iloc[0]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Latest run", f"#{last['run_id']}")
        c2.metric("Status", last["status"])
        c3.metric("Records processed", int(last["records_processed"] or 0))
        c4.metric("Validation warnings", int(last["records_rejected"] or 0))

    st.subheader("Recent pipeline runs")
    st.dataframe(runs, use_container_width=True, hide_index=True)

    st.subheader("Source freshness")
    fresh = q("""
        SELECT source_name, source_type, retrieval_date, publication_date,
               (CURRENT_DATE - retrieval_date) AS days_since_retrieval
        FROM sources ORDER BY retrieval_date ASC NULLS FIRST
    """)
    st.dataframe(fresh, use_container_width=True, hide_index=True)

    st.subheader("Evidence coverage per vendor")
    cov = q("""
        SELECT v.vendor_name,
               COUNT(*) AS total_features,
               COUNT(*) FILTER (WHERE vf.availability_status <> 'unknown') AS with_evidence,
               ROUND(100.0 * COUNT(*) FILTER (WHERE vf.availability_status <> 'unknown')
                     / NULLIF(COUNT(*),0), 1) AS evidence_coverage_pct
        FROM vendors v JOIN vendor_features vf USING (vendor_id)
        GROUP BY v.vendor_name ORDER BY evidence_coverage_pct ASC
    """)
    fig = px.bar(cov, x="vendor_name", y="evidence_coverage_pct",
                 labels={"vendor_name": "", "evidence_coverage_pct": "% features with evidence"})
    st.plotly_chart(fig, use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Traceability gaps (missing sources)")
        gaps = q("""
            SELECT 'vendor_segments' AS tbl, COUNT(*) n FROM vendor_segments WHERE source_id IS NULL
            UNION ALL SELECT 'vendor_features', COUNT(*) FROM vendor_features WHERE source_id IS NULL
            UNION ALL SELECT 'market_metrics', COUNT(*) FROM market_metrics WHERE source_id IS NULL
        """)
        st.dataframe(gaps, use_container_width=True, hide_index=True)
    with c2:
        st.subheader("Metrics with no reported value")
        novalue = q("""
            SELECT v.vendor_name, m.metric_name, m.measurement_year
            FROM market_metrics m JOIN vendors v USING (vendor_id)
            WHERE m.metric_value IS NULL
        """)
        st.dataframe(novalue, use_container_width=True, hide_index=True)


PAGES = {
    "EHR Market Overview": page_overview,
    "Competitive Intelligence": page_competitive,
    "Data Engineering Monitor": page_monitor,
}

choice = st.sidebar.radio("Navigate", list(PAGES.keys()))
st.sidebar.caption("EHR Market Intelligence & Competitive Analysis")
PAGES[choice]()
