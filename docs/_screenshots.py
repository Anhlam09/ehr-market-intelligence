"""
Dev-only helper: capture dashboard screenshots for the README.

Assumes a Streamlit server is already running on PORT (started by the caller).
Uses the system Chrome via Playwright. Not part of the app runtime.
"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

PORT = sys.argv[1] if len(sys.argv) > 1 else "8601"
OUT = Path(__file__).parent / "images"
OUT.mkdir(parents=True, exist_ok=True)

PAGES = [
    ("EHR Market Overview", "01_market_overview.png"),
    ("Competitive Intelligence", "02_competitive_intelligence.png"),
    ("Data Engineering Monitor", "03_data_engineering_monitor.png"),
]


def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1600},
                                device_scale_factor=2)
        page.goto(f"http://localhost:{PORT}/", wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(4000)

        for label, filename in PAGES:
            # click the sidebar radio option for this page
            try:
                page.get_by_text(label, exact=True).first.click(timeout=10000)
            except Exception as exc:  # noqa: BLE001
                print(f"warn: could not click {label}: {exc}")
            page.wait_for_timeout(5000)  # let plotly/tables render
            path = OUT / filename
            page.screenshot(path=str(path), full_page=True)
            print(f"saved {path.relative_to(Path(__file__).parent.parent)}")

        browser.close()


if __name__ == "__main__":
    run()
