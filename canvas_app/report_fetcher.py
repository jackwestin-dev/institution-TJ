"""
Browser-automated Canvas New Quizzes report downloader.

How it works:
  1. Uses the Canvas API token to get a sessionless-launch URL (no password needed).
  2. Opens that URL in a headless Chromium browser — it lands directly on the
     New Quizzes quiz-builder view (Build | Settings | Moderate | Reports | Exports).
  3. Clicks the Reports tab, then downloads the Student Analysis CSV.
     - If a report already exists: clicks "Export CSV" on the Student Analysis card.
     - If not: clicks "Generate Report", polls until ready, then "Export CSV".
  4. Returns the raw CSV bytes.

Requires:  pip install playwright  &&  playwright install chromium

Reports page layout (3 cards, left to right):
  [Quiz and Item Analysis | Export CSV]  [Outcomes Analysis]  [Student Analysis | Export CSV (grayed) | Generate Report]
"""

import time
import requests


def is_playwright_available() -> bool:
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
        return True
    except ImportError:
        return False


def fetch_quiz_report_csv(
    canvas_url: str,
    api_token: str,
    course_id: int,
    assignment_id: int,
    report_type: str = "student",
    timeout_ms: int = 120_000,
    headless: bool = True,
    status_callback=None,
    generate_if_missing: bool = True,
) -> bytes:
    """
    Download a Canvas New Quiz report CSV via browser automation.

    Parameters
    ----------
    canvas_url     Canvas instance URL, e.g. "https://texasjamp.instructure.com"
    api_token      Canvas API bearer token
    course_id      Canvas course ID (integer)
    assignment_id  Canvas assignment ID (integer)
    report_type    "student" (default) for Student Analysis; "item" for Quiz and Item Analysis
    timeout_ms     Max ms to wait for any single browser action (default 120s)
    headless       Run Chromium headlessly
    status_callback  Optional callable(msg: str) for progress updates
    generate_if_missing  If True (default), click "Generate Report" and poll up
                   to 2 minutes when the report isn't ready. If False, only
                   click "Export CSV" for an already-generated report and fail
                   fast otherwise (use when reports are pre-generated in Canvas).

    Returns
    -------
    bytes  Raw CSV content

    Raises
    ------
    ImportError   if playwright is not installed
    RuntimeError  if the report could not be downloaded
    """
    if not is_playwright_available():
        raise ImportError(
            "Playwright is not installed.\n"
            "Run:  pip install playwright  &&  playwright install chromium"
        )

    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

    def log(msg: str):
        if status_callback:
            status_callback(msg)
        else:
            print(msg)

    # ── Step 1: get sessionless launch URL ────────────────────────────────────
    log("Requesting sessionless launch URL...")
    r = requests.get(
        f"{canvas_url.rstrip('/')}/api/v1/courses/{course_id}/external_tools/sessionless_launch",
        headers={"Authorization": f"Bearer {api_token}"},
        params={"assignment_id": assignment_id, "launch_type": "assessment"},
        timeout=30,
    )
    if r.status_code != 200:
        raise RuntimeError(
            f"Canvas API returned {r.status_code} for sessionless launch: {r.text[:200]}"
        )
    launch_url = r.json().get("url")
    if not launch_url:
        raise RuntimeError("Canvas API returned no launch URL.")

    log("Opening headless browser...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(
            accept_downloads=True,
            viewport={"width": 1280, "height": 900},
        )
        page = context.new_page()

        try:
            # ── Step 2: navigate to quiz tool ─────────────────────────────────
            log("Navigating to quiz via sessionless launch...")
            page.goto(launch_url, wait_until="networkidle", timeout=timeout_ms)
            page.wait_for_load_state("networkidle", timeout=timeout_ms)
            time.sleep(2)

            log(f"Landed on: {page.url[:80]}")

            # ── Step 3: click Reports tab ──────────────────────────────────────
            log("Clicking Reports tab...")
            clicked = False
            for selector in [
                lambda: page.get_by_role("link", name="Reports").click(timeout=8_000),
                lambda: page.locator("a", has_text="Reports").first.click(timeout=8_000),
                lambda: page.locator("text=Reports").first.click(timeout=8_000),
            ]:
                try:
                    selector()
                    clicked = True
                    break
                except (PWTimeout, Exception):
                    continue

            if not clicked:
                raise RuntimeError(
                    "Could not find the Reports tab. "
                    "The quiz may not have reports enabled."
                )

            page.wait_for_load_state("networkidle", timeout=timeout_ms)
            time.sleep(2)
            log(f"Reports page: {page.url[:80]}")

            # ── Step 4: download or generate the target report ─────────────────
            # The Reports page has (left to right):
            #   card 0: "Quiz and Item Analysis"  -> Export CSV button (index 0)
            #   card 1: "Outcomes Analysis"       -> no Export CSV
            #   card 2: "Student Analysis"        -> Export CSV button (index 1, may be disabled)
            #                                        Generate Report link

            if report_type == "student":
                csv_bytes = _download_student_analysis(
                    page, log, timeout_ms, generate_if_missing=generate_if_missing
                )
            else:
                csv_bytes = _download_item_analysis(page, log, timeout_ms)

            return csv_bytes

        finally:
            browser.close()


def _get_export_csv_buttons(page):
    """Return all visible 'Export CSV' buttons on the Reports page."""
    from playwright.sync_api import TimeoutError as PWTimeout
    # Try button role first, then fallback to text locator
    btns = page.get_by_role("button", name="Export CSV")
    if btns.count() == 0:
        btns = page.locator("button:has-text('Export CSV')")
    if btns.count() == 0:
        btns = page.locator("text=Export CSV")
    return btns


def _download_item_analysis(page, log, timeout_ms):
    """Download the Quiz and Item Analysis CSV (already generated, first card)."""
    from playwright.sync_api import TimeoutError as PWTimeout

    log("Targeting Quiz and Item Analysis export...")
    btns = _get_export_csv_buttons(page)
    count = btns.count()
    if count == 0:
        raise RuntimeError("No 'Export CSV' buttons found on the Reports page.")

    # First Export CSV button = Quiz and Item Analysis
    btn = btns.nth(0)
    log("Clicking Export CSV for Quiz and Item Analysis...")
    try:
        with page.expect_download(timeout=30_000) as dl_info:
            btn.click(timeout=8_000)
        download = dl_info.value
        log("Download started, saving...")
        path = download.path()
        with open(path, "rb") as f:
            return f.read()
    except (PWTimeout, Exception) as e:
        raise RuntimeError(f"Failed to download Quiz and Item Analysis CSV: {e}")


def _download_student_analysis(page, log, timeout_ms, generate_if_missing=True):
    """Download the Student Analysis CSV, generating if needed.

    When generate_if_missing is False, only an already-generated report is
    exported; if it isn't ready, raise immediately (no Generate + no polling).
    """
    from playwright.sync_api import TimeoutError as PWTimeout

    log("Checking Student Analysis report status...")

    # ── Try to download an already-generated Student Analysis report ──────────
    btns = _get_export_csv_buttons(page)
    count = btns.count()

    # Student Analysis is the LAST card — its Export CSV is the last button
    if count >= 2:
        student_btn = btns.nth(count - 1)
        is_disabled = student_btn.is_disabled()
        if not is_disabled:
            log("Student Analysis report already exists — downloading...")
            try:
                with page.expect_download(timeout=30_000) as dl_info:
                    student_btn.click(timeout=8_000)
                download = dl_info.value
                log("Download complete.")
                with open(download.path(), "rb") as f:
                    return f.read()
            except (PWTimeout, Exception) as e:
                log(f"Export CSV click failed ({e}), will try generating...")

    # ── Export-only mode: don't generate, fail fast ───────────────────────────
    if not generate_if_missing:
        raise RuntimeError(
            "Student Analysis report is not generated yet (Export CSV unavailable). "
            "Generate it in Canvas first — export-only mode does not generate."
        )

    # ── Generate the Student Analysis report ──────────────────────────────────
    log("Student Analysis not yet generated — clicking Generate Report...")

    # "Generate Report" links: the last one belongs to Student Analysis
    generated = False
    for selector in [
        lambda: page.get_by_role("link", name="Generate Report"),
        lambda: page.locator("a:has-text('Generate Report')"),
        lambda: page.locator("text=Generate Report"),
    ]:
        try:
            links = selector()
            link_count = links.count()
            if link_count == 0:
                continue
            # Click the LAST "Generate Report" link = Student Analysis card
            links.nth(link_count - 1).click(timeout=8_000)
            generated = True
            break
        except (PWTimeout, Exception):
            continue

    if not generated:
        # Maybe "Generate Report" is displayed as a button in this quiz
        for selector in [
            lambda: page.get_by_role("button", name="Generate Report"),
            lambda: page.locator("button:has-text('Generate Report')"),
        ]:
            try:
                btn = selector().last
                btn.click(timeout=8_000)
                generated = True
                break
            except (PWTimeout, Exception):
                continue

    if not generated:
        raise RuntimeError(
            "Could not find 'Generate Report' for Student Analysis. "
            "The report may already exist — try a manual download from Canvas."
        )

    log("Report generation triggered. Polling for completion (up to 2 minutes)...")

    # ── Poll: reload page and check if Export CSV button is now enabled ────────
    for attempt in range(24):  # 24 x 5s = 120 seconds
        time.sleep(5)
        log(f"Waiting for report... ({attempt + 1}/24)")

        try:
            page.reload(wait_until="networkidle", timeout=20_000)
            time.sleep(2)

            btns = _get_export_csv_buttons(page)
            count = btns.count()

            if count >= 2:
                student_btn = btns.nth(count - 1)
                if not student_btn.is_disabled():
                    log("Report is ready — downloading Student Analysis CSV...")
                    with page.expect_download(timeout=30_000) as dl_info:
                        student_btn.click(timeout=8_000)
                    download = dl_info.value
                    log("Download complete.")
                    with open(download.path(), "rb") as f:
                        return f.read()
            elif count == 1:
                # Only one Export CSV — might be Student Analysis if item analysis was never generated
                btn = btns.nth(0)
                if not btn.is_disabled():
                    log("Export CSV available — downloading...")
                    with page.expect_download(timeout=30_000) as dl_info:
                        btn.click(timeout=8_000)
                    download = dl_info.value
                    log("Download complete.")
                    with open(download.path(), "rb") as f:
                        return f.read()

        except (PWTimeout, Exception) as e:
            log(f"Poll {attempt + 1} error: {e}")
            continue

    raise RuntimeError(
        "Student Analysis report did not become available within 2 minutes. "
        "Try manually generating it in Canvas first, then click Fetch again."
    )
