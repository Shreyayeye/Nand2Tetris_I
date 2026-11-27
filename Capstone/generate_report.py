#!/usr/bin/env python3
"""Render Capstone_Report.html to Capstone_Report.pdf using headless Chrome.

ReportLab is not installed in this environment and cannot be downloaded, so
the report is authored as print-ready A4 HTML/CSS and printed to PDF by the
locally installed Chrome browser.  The HTML keeps the text as real, selectable
text and embeds the genuine screenshots from the screenshots/ folder.
"""

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HTML = ROOT / "Capstone_Report.html"
PDF = ROOT / "Capstone_Report.pdf"

CHROME_CANDIDATES = [
    Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
    Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
    Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
    Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
]


def find_browser() -> Path:
    for candidate in CHROME_CANDIDATES:
        if candidate.is_file():
            return candidate
    raise SystemExit("No Chrome or Edge installation found to render the PDF.")


def main() -> int:
    if not HTML.is_file():
        raise SystemExit("Missing {}".format(HTML))

    browser = find_browser()
    command = [
        str(browser),
        "--headless=new",
        "--disable-gpu",
        "--hide-scrollbars",
        "--no-pdf-header-footer",
        "--virtual-time-budget=8000",
        "--print-to-pdf={}".format(PDF),
        HTML.as_uri(),
    ]
    subprocess.run(command, check=True, cwd=str(ROOT), timeout=180)

    if not PDF.is_file():
        raise SystemExit("PDF was not created.")

    data = PDF.read_bytes()
    if not data.startswith(b"%PDF-"):
        raise SystemExit("Output is not a valid PDF file.")

    pages = len(re.findall(rb"/Type\s*/Page(?!s)", data))
    size_mb = len(data) / (1024 * 1024)
    print("Created: {}".format(PDF))
    print("Pages: {} | Size: {:.2f} MB".format(pages, size_mb))

    if pages != 4:
        print("WARNING: expected 4 pages, found {}".format(pages), file=sys.stderr)
    if size_mb >= 25:
        print("WARNING: PDF exceeds the 25 MB upload limit.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
