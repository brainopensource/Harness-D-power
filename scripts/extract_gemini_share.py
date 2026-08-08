#!/usr/bin/env python3
"""Extract full Gemini share-page conversation text to markdown."""

from __future__ import annotations

import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

URL = (
    sys.argv[1]
    if len(sys.argv) > 1 and sys.argv[1].startswith("http")
    else "https://gemini.google.com/share/a80e0c8ea417?skid=36bb015e-1bb8-44dc-95a8-85fbc12ccb85"
)
out_arg = (
    sys.argv[2]
    if len(sys.argv) > 2
    else (
        sys.argv[1]
        if len(sys.argv) > 1 and not sys.argv[1].startswith("http")
        else "gemini_share_a80e0c8ea417.md"
    )
)
OUT = Path(out_arg)


def clean_body(text: str) -> str:
    # Drop chrome chrome / footer noise when possible
    lines = text.splitlines()
    start = 0
    for i, line in enumerate(lines):
        if line.strip() in {"You said", "Advanced Agent Architecture Design"} or line.startswith("# SAGIHA2"):
            # Prefer title if present earlier
            if "Advanced Agent Architecture Design" in line:
                start = i
                break
            if line.strip() == "You said":
                start = max(0, i - 5)
                break
    for i, line in enumerate(lines):
        if line.strip() == "Advanced Agent Architecture Design":
            start = i
            break
    end = len(lines)
    for i, line in enumerate(lines):
        if line.strip().startswith("Google Privacy Policy"):
            end = i
            break
    body = "\n".join(lines[start:end]).strip()
    # Collapse excessive blank lines from share UI
    body = re.sub(r"\n{4,}", "\n\n\n", body)
    return body


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1400, "height": 900})
        page.goto(URL, wait_until="networkidle", timeout=120_000)
        page.wait_for_timeout(3000)

        # Expand collapsed sections
        for _ in range(3):
            for btn in page.locator("button").all():
                try:
                    label = (
                        (btn.inner_text(timeout=200) or "") + " " + (btn.get_attribute("aria-label") or "")
                    )
                    if re.search(r"expand|mostrar|previous|anteriores", label, re.I):
                        btn.click(timeout=1000)
                except Exception:
                    pass
            page.wait_for_timeout(500)

        # Scroll to load any lazy content
        for _ in range(40):
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(120)

        raw = page.inner_text("body")
        title = page.title()
        browser.close()

    body = clean_body(raw)
    md = "\n".join(
        [
            "---",
            "status: rationale",
            "updated: 2026-08-01",
            "retrieval: excluded",
            f"source: {URL}",
            "---",
            "",
            "# Gemini Share Export — Advanced Agent Architecture Design",
            "",
            f"**Source URL:** {URL}",
            "",
            f"**Page title:** {title}",
            "",
            "**Captured:** 2026-08-01 via Playwright (full `document.body` text after expand/scroll).",
            "",
            "> Note: This is a linear text dump of a shared Gemini chat UI. Formatting may include",
            "> doubled newlines from the share renderer; speaker turns are marked",
            "> `You said` / model replies.",
            "",
            "---",
            "",
            body,
            "",
        ]
    )
    OUT.write_text(md, encoding="utf-8")
    print(f"Wrote {OUT} ({len(md)} chars, {len(body)} body chars)")


if __name__ == "__main__":
    main()
