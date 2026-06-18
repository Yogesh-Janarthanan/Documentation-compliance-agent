"""
Stage 4: Report
"""

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DISCREPANCIES_PATH = DATA_DIR / "discrepancies.json"
COVERAGE_PATH = DATA_DIR / "coverage_report.json"
REPORTS_DIR = PROJECT_ROOT / "reports"
OUTPUT_PATH = REPORTS_DIR / "compliance_report.md"

def load_json(path):
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def generate_report():
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    discrepancy_data = load_json(DISCREPANCIES_PATH)
    if discrepancy_data is None:
        print(f"[ERROR] {DISCREPANCIES_PATH} not found. Run Stage 3 first.")
        return
    coverage_data = load_json(COVERAGE_PATH) or {}
    discrepancies = discrepancy_data.get("discrepancies", [])
    by_page = defaultdict(list)
    for d in discrepancies:
        by_page[d["page_url"]].append(d)
    lines = []
    lines.append("# WaiverPro Documentation Compliance Report")
    lines.append("")
    lines.append(f"_Generated: {datetime.now(timezone.utc).isoformat()}_")
    lines.append("")
    lines.append(f"> **Disclaimer:** {discrepancy_data.get('disclaimer', '')}")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- **Guideline rules checked:** {discrepancy_data.get('total_rules_checked', 'N/A')}")
    lines.append(f"- **Pages checked:** {discrepancy_data.get('total_pages_checked', 'N/A')}")
    lines.append(f"- **Discrepancies found:** {discrepancy_data.get('total_discrepancies_found', len(discrepancies))}")
    if coverage_data:
        lines.append(f"- **Pages successfully crawled:** {len(coverage_data.get('successful_urls', []))}")
        lines.append(f"- **Pages failed to crawl:** {len(coverage_data.get('failed_urls', []))}")
    lines.append("")
    if not discrepancies:
        lines.append("No discrepancies were found.")
        lines.append("")
    else:
        lines.append("## Discrepancies by Page")
        lines.append("")
        for page_url, page_discrepancies in sorted(by_page.items()):
            lines.append(f"### {page_url}")
            lines.append("")
            for i, d in enumerate(page_discrepancies, start=1):
                lines.append(f"**{i}. {d.get('discrepancy_reason', 'Discrepancy detected')}**")
                lines.append("")
                lines.append(f"- **Guideline reference:** {d.get('guideline_reference', 'N/A')}")
                if d.get("expected_text_content"):
                    lines.append(f"- **Expected:** {d['expected_text_content']}")
                if d.get("actual_text_content"):
                    lines.append(f"- **Actual:** {d['actual_text_content']}")
                if d.get("component_selector"):
                    lines.append(f"- **Selector:** `{d['component_selector']}`")
                if d.get("screenshot_path"):
                    lines.append(f"- **Screenshot evidence:** `{d['screenshot_path']}`")
                    lines.append("")
                    lines.append(f"  ![Screenshot]({d['screenshot_path']})")
                lines.append("")
    if coverage_data:
        lines.append("## Coverage & Completeness")
        lines.append("")
        lines.append(f"- Started: {coverage_data.get('started_at', 'N/A')}")
        lines.append(f"- Finished: {coverage_data.get('finished_at', 'N/A')}")
        lines.append(f"- Total UI components extracted: {coverage_data.get('total_components_extracted', 'N/A')}")
        lines.append(f"- Pages visited: {coverage_data.get('pages_visited', 'N/A')}")
        failed = coverage_data.get("failed_urls", [])
        if failed:
            lines.append(f"- **Failed URLs ({len(failed)}):**")
            for url in failed:
                lines.append(f"  - {url}")
        else:
            lines.append("- No failed URLs.")
        lines.append("")
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"[INFO] Report generated: {OUTPUT_PATH}")

if __name__ == "__main__":
    generate_report()
