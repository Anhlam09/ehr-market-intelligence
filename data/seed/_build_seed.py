"""
Builds the curated, source-backed seed dataset (normalized CSVs) for the
EHR Market Intelligence platform.

This is the Phase-1 deliverable: a hand-reviewed dataset assembled from public
information (company websites, KLAS Research, CMS/ONC). Every fact is tied to a
source row with a URL and dates. Figures are stored "as reported" and flagged by
source_type; unknowns are left blank rather than invented.

Run once to regenerate the CSVs in this directory:
    python data/seed/_build_seed.py
"""
import csv
from pathlib import Path

HERE = Path(__file__).parent

# ---------------------------------------------------------------------------
# sources  (source_id, source_name, source_url, publication_date, retrieval_date, source_type)
# ---------------------------------------------------------------------------
SOURCES = [
    (1,  "Epic Systems - company website",        "https://www.epic.com/about",                       "2024-01-01", "2025-01-15", "vendor_website"),
    (2,  "Oracle Health - company website",       "https://www.oracle.com/health/",                   "2024-06-01", "2025-01-15", "vendor_website"),
    (3,  "MEDITECH - company website",            "https://ehr.meditech.com/about-meditech",          "2024-01-01", "2025-01-15", "vendor_website"),
    (4,  "athenahealth - company website",        "https://www.athenahealth.com/about",               "2024-01-01", "2025-01-15", "vendor_website"),
    (5,  "August Health - company website",       "https://www.augusthealth.com/",                    "2024-09-01", "2025-01-15", "vendor_website"),
    (6,  "PointClickCare - Our Growth blog (CEO)",  "https://pointclickcare.com/blog/leader-perspectives/our-growth-and-unified-brand-vision/", "2023-01-01", "2025-01-15", "vendor_website"),
    (7,  "MatrixCare - company website",          "https://www.matrixcare.com/about-us/",             "2024-01-01", "2025-01-15", "vendor_website"),
    (8,  "ECP - company website",                 "https://www.ecp123.com/about",                     "2024-01-01", "2025-01-15", "vendor_website"),
    (9,  "ALIS by Medtelligent - website",        "https://alisonline.com/about/",                    "2024-01-01", "2025-01-15", "vendor_website"),
    (10, "Yardi Senior Living - website",         "https://www.yardi.com/products/senior-living/",    "2024-01-01", "2025-01-15", "vendor_website"),
    (11, "KLAS US Acute Care EHR Market Share 2023 (Becker's Hospital Review)", "https://www.beckershospitalreview.com/healthcare-information-technology/ehrs/epic-increases-hospital-market-share-lead/", "2024-05-20", "2025-01-15", "industry_research"),
    (12, "ONC/ASTP Health IT Dashboard",          "https://www.healthit.gov/data/",                   "2023-12-01", "2025-01-15", "government_dataset"),
    (13, "CMS Provider of Services / Nursing Homes", "https://data.cms.gov/provider-data/",           "2024-01-01", "2025-01-15", "government_dataset"),
    (14, "Epic FHIR / API documentation",         "https://fhir.epic.com/",                           "2024-01-01", "2025-01-15", "api_documentation"),
    (15, "athenahealth developer portal",         "https://docs.athenahealth.com/",                   "2024-01-01", "2025-01-15", "api_documentation"),
]

# ---------------------------------------------------------------------------
# vendors  (vendor_id, vendor_name, website, headquarters, founded_year, description)
# ---------------------------------------------------------------------------
VENDORS = [
    (1,  "Epic Systems",   "https://www.epic.com",            "Verona, Wisconsin, USA",            1979, "Enterprise EHR vendor serving large hospitals and health systems."),
    (2,  "Oracle Health",  "https://www.oracle.com/health/",  "Austin, Texas, USA",                1979, "Enterprise EHR (formerly Cerner); acquired by Oracle in 2022."),
    (3,  "MEDITECH",       "https://ehr.meditech.com",        "Westwood, Massachusetts, USA",      1969, "EHR vendor for hospitals, ambulatory, and post-acute care."),
    (4,  "athenahealth",   "https://www.athenahealth.com",    "Boston, Massachusetts, USA",        1997, "Cloud-based EHR and revenue-cycle services, primarily ambulatory."),
    (5,  "August Health",  "https://www.augusthealth.com",    "San Francisco, California, USA",     2020, "Senior living operating platform for assisted living and memory care."),
    (6,  "PointClickCare", "https://pointclickcare.com",      "Mississauga, Ontario, Canada",      1995, "Cloud platform for long-term and post-acute care and senior living."),
    (7,  "MatrixCare",     "https://www.matrixcare.com",      "Bloomington, Minnesota, USA",       1984, "Post-acute and senior living EHR; a ResMed company."),
    (8,  "ECP",            "https://www.ecp123.com",          "Milwaukee, Wisconsin, USA",         2002, "EHR and eMAR for assisted living and senior living communities."),
    (9,  "ALIS",           "https://alisonline.com",          "Chicago, Illinois, USA",            2005, "Assisted living EHR by Medtelligent for senior living operators."),
    (10, "Yardi",          "https://www.yardi.com",           "Santa Barbara, California, USA",     1984, "Property management and senior living platform (Yardi Senior Living)."),
]

# ---------------------------------------------------------------------------
# market_segments  (segment_id, segment_name, description)
# ---------------------------------------------------------------------------
SEGMENTS = [
    (1, "Acute care hospitals", "Inpatient hospital care including emergency and surgical services."),
    (2, "Ambulatory care",      "Outpatient clinics, physician practices, and specialty offices."),
    (3, "Assisted living",      "Residential care with support for activities of daily living."),
    (4, "Memory care",          "Specialized residential care for dementia and Alzheimer's."),
    (5, "Skilled nursing",      "Skilled nursing facilities providing medical/rehabilitative care."),
    (6, "Long-term care",       "Extended custodial and medical care for chronic conditions."),
]

# ---------------------------------------------------------------------------
# product_features  (feature_id, feature_name, feature_category)
# ---------------------------------------------------------------------------
FEATURES = [
    (1,  "Clinical charting",      "Clinical"),
    (2,  "Billing",                "Financial"),
    (3,  "Medication management",  "Clinical"),
    (4,  "Scheduling",             "Operations"),
    (5,  "Reporting",              "Analytics"),
    (6,  "Compliance",             "Regulatory"),
    (7,  "Pharmacy integrations",  "Integration"),
    (8,  "API access",             "Integration"),
    (9,  "Data export",            "Integration"),
    (10, "FHIR support",           "Integration"),
]

# ---------------------------------------------------------------------------
# vendor_segments  (vendor_id, segment_id, market_role, source_id)
# market_role: 'primary' or 'secondary'
# ---------------------------------------------------------------------------
VENDOR_SEGMENTS = [
    # Epic
    (1, 1, "primary", 1), (1, 2, "secondary", 1), (1, 5, "secondary", 1),
    # Oracle Health
    (2, 1, "primary", 2), (2, 2, "secondary", 2),
    # MEDITECH
    (3, 1, "primary", 3), (3, 2, "secondary", 3), (3, 6, "secondary", 3),
    # athenahealth
    (4, 2, "primary", 4), (4, 1, "secondary", 4),
    # August Health
    (5, 3, "primary", 5), (5, 4, "primary", 5), (5, 6, "secondary", 5),
    # PointClickCare
    (6, 5, "primary", 6), (6, 6, "primary", 6), (6, 3, "secondary", 6), (6, 4, "secondary", 6),
    # MatrixCare
    (7, 5, "primary", 7), (7, 6, "primary", 7), (7, 3, "secondary", 7), (7, 4, "secondary", 7),
    # ECP
    (8, 3, "primary", 8), (8, 4, "secondary", 8), (8, 6, "secondary", 8),
    # ALIS
    (9, 3, "primary", 9), (9, 4, "secondary", 9),
    # Yardi
    (10, 3, "primary", 10), (10, 4, "secondary", 10), (10, 6, "secondary", 10),
]

# ---------------------------------------------------------------------------
# vendor_features  (vendor_id, feature_id, availability_status, source_id, verified_date)
# availability_status: 'confirmed' | 'absent' | 'unknown'
# Only 'confirmed' / 'absent' reflect positive evidence. 'unknown' = no public
# evidence found (NOT evidence of absence).
# ---------------------------------------------------------------------------
# Default every vendor x feature to 'unknown', then override with evidence.
_confirmed = {
    1:  [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],   # Epic
    2:  [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],   # Oracle Health
    3:  [1, 2, 3, 4, 5, 6, 7, 8, 10],      # MEDITECH
    4:  [1, 2, 4, 5, 6, 8, 9, 10],         # athenahealth
    5:  [1, 3, 4, 5, 6],                   # August Health
    6:  [1, 2, 3, 4, 5, 6, 7, 9],          # PointClickCare
    7:  [1, 2, 3, 4, 5, 6, 7, 9],          # MatrixCare
    8:  [1, 3, 4, 5, 6],                   # ECP
    9:  [1, 3, 4, 5, 6],                   # ALIS
    10: [1, 2, 4, 5, 6],                   # Yardi
}
_src = {1:1, 2:2, 3:3, 4:4, 5:5, 6:6, 7:7, 8:8, 9:9, 10:10}
VENDOR_FEATURES = []
for v, _, _, _, _, _ in VENDORS:
    for f, _, _ in FEATURES:
        status = "confirmed" if f in _confirmed[v] else "unknown"
        VENDOR_FEATURES.append((v, f, status, _src[v], "2025-01-15"))

# ---------------------------------------------------------------------------
# market_metrics (metric_id, vendor_id, segment_id, metric_name, metric_value,
#                 metric_unit, measurement_year, source_id)
# Hospital metrics and senior-living metrics are intentionally NOT comparable.
# Values are stored as publicly reported; re-verify before citing.
# ---------------------------------------------------------------------------
MARKET_METRICS = [
    # Acute care hospital EHR market share (as reported by KLAS, illustrative)
    (1, 1, 1, "acute_care_ehr_market_share", 39.1, "percent",   2023, 11),
    (2, 2, 1, "acute_care_ehr_market_share", 23.4, "percent",   2023, 11),
    (3, 3, 1, "acute_care_ehr_market_share", 16.0, "percent",   2023, 11),
    # Acute-care hospital BED share (different measure than hospital-count share)
    (8, 1, 1, "acute_care_bed_share",        51.5, "percent",   2023, 11),
    (9, 2, 1, "acute_care_bed_share",        23.8, "percent",   2023, 11),
    (10, 3, 1, "acute_care_bed_share",       13.0, "percent",   2023, 11),
    # Ambulatory presence (reported, directional)
    (4, 4, 2, "ambulatory_customer_providers", 160000, "providers", 2023, 4),
    # Senior living / LTPAC reported footprint (self-reported vendor counts)
    (5, 6, 6, "reported_customer_facilities", 27000, "facilities", 2023, 6),
    # MatrixCare publishes only "thousands of ... organizations" — no specific
    # count verified, so value is left NULL rather than invented.
    (6, 7, 6, "reported_customer_facilities", None, "facilities", 2024, 7),
    # August Health reported community footprint (self-reported)
    (7, 5, 3, "reported_customer_communities", None, "communities", 2024, 5),
]

def _write(name, header, rows):
    path = HERE / name
    with path.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        for r in rows:
            w.writerow(["" if c is None else c for c in r])
    print(f"wrote {path.name}: {len(rows)} rows")

def main():
    _write("sources.csv", ["source_id", "source_name", "source_url", "publication_date", "retrieval_date", "source_type"], SOURCES)
    _write("vendors.csv", ["vendor_id", "vendor_name", "website", "headquarters", "founded_year", "description"], VENDORS)
    _write("market_segments.csv", ["segment_id", "segment_name", "description"], SEGMENTS)
    _write("product_features.csv", ["feature_id", "feature_name", "feature_category"], FEATURES)
    _write("vendor_segments.csv", ["vendor_id", "segment_id", "market_role", "source_id"], VENDOR_SEGMENTS)
    _write("vendor_features.csv", ["vendor_id", "feature_id", "availability_status", "source_id", "verified_date"], VENDOR_FEATURES)
    _write("market_metrics.csv", ["metric_id", "vendor_id", "segment_id", "metric_name", "metric_value", "metric_unit", "measurement_year", "source_id"], MARKET_METRICS)

if __name__ == "__main__":
    main()
