"""
Stage 2: Extract
"""

import json
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

BASE_URL = "https://white-cliff-0bca3ed00.1.azurestaticapps.net/"
LOGIN_EMAIL = "admin@gmail.com"
LOGIN_PASSWORD = "password"
LOGIN_URL = "https://white-cliff-0bca3ed00.1.azurestaticapps.net/login"

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
UI_STATES_DIR = DATA_DIR / "ui_states"
SCREENSHOTS_DIR = DATA_DIR / "screenshots"
LOG_PATH = DATA_DIR / "extraction_log.jsonl"
COVERAGE_PATH = DATA_DIR / "coverage_report.json"

MAX_PAGES = 25
NAV_TIMEOUT_MS = 15000
RETRY_COUNT = 2
RETRY_BACKOFF_SEC = 2

COMPONENT_SELECTORS = {
    "heading": "h1, h2, h3, h4, h5, h6",
    "button": "button, [role='button'], input[type='submit'], input[type='button']",
    "link": "a[href]",
    "nav_item": "nav a, [role='navigation'] a",
    "text_block": "p",
    "label": "label",
    "input": "input, textarea, select",
    "image": "img",
}

def log_event(event_type, message, **extra):
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": event_type,
        "message": message,
        **extra,
    }
    print(f"[{event_type.upper()}] {message}")
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")

def safe_filename(url):
    path = urlparse(url).path.strip("/").replace("/", "_")
    return path if path else "root"

def with_retries(fn, description, retries=RETRY_COUNT):
    last_err = None
    for attempt in range(1, retries + 2):
        try:
            return True, fn()
        except Exception as e:
            last_err = e
            log_event("retry", f"Attempt {attempt} failed for: {description} -> {e}")
            time.sleep(RETRY_BACKOFF_SEC * attempt)
    log_event("error", f"All retries exhausted for: {description} -> {last_err}")
    return False, None

def perform_login(page):
    page.goto(LOGIN_URL, wait_until="networkidle", timeout=NAV_TIMEOUT_MS)
    page.wait_for_timeout(1000)

    email_selectors = [
        "input[type='email']", "input[name='email']",
        "input[placeholder*='email' i]", "input[id*='email' i]",
    ]
    password_selectors = [
        "input[type='password']", "input[name='password']", "input[id*='password' i]",
    ]
    email_input = None
    for sel in email_selectors:
        if page.locator(sel).count() > 0:
            email_input = page.locator(sel).first
            break
    password_input = None
    for sel in password_selectors:
        if page.locator(sel).count() > 0:
            password_input = page.locator(sel).first
            break
    if not email_input or not password_input:
        log_event("warning", "Could not locate email/password fields on /login page.")
        return False

    email_input.wait_for(state="visible", timeout=NAV_TIMEOUT_MS)
    email_input.click()
    email_input.fill("")
    email_input.press_sequentially(LOGIN_EMAIL, delay=50)

    password_input.wait_for(state="visible", timeout=NAV_TIMEOUT_MS)
    password_input.click()
    password_input.fill("")
    password_input.press_sequentially(LOGIN_PASSWORD, delay=50)

    email_value = email_input.input_value()
    password_value = password_input.input_value()
    log_event("debug", f"Email field value after typing: '{email_value}' (expected '{LOGIN_EMAIL}')")
    if email_value != LOGIN_EMAIL or password_value != LOGIN_PASSWORD:
        log_event("warning", "Typed values do not match expected credentials.")

    try:
        page.screenshot(path=str(SCREENSHOTS_DIR / "debug_pre_submit.png"))
    except Exception as e:
        log_event("warning", f"Pre-submit debug screenshot failed: {e}")

    submit_selectors = [
        "button[type='submit']", "button:has-text('Login')",
        "button:has-text('Log in')", "button:has-text('Sign in')", "input[type='submit']",
    ]
    clicked = False
    for sel in submit_selectors:
        if page.locator(sel).count() > 0:
            page.locator(sel).first.click()
            clicked = True
            break
    if not clicked:
        password_input.press("Enter")

    try:
        page.wait_for_load_state("networkidle", timeout=NAV_TIMEOUT_MS)
    except PlaywrightTimeoutError:
        log_event("warning", "Network did not go idle after login submit; continuing anyway.")

    try:
        page.wait_for_url(lambda url: "/login" not in url, timeout=20000)
    except PlaywrightTimeoutError:
        log_event("warning", "URL did not change away from /login within 20s.")

    log_event("info", f"Post-login URL: {page.url}")
    if page.url.rstrip("/").endswith("/login"):
        log_event("warning", "Still on /login after submit attempt - login may have failed.")
        try:
            page.screenshot(path=str(SCREENSHOTS_DIR / "debug_post_submit_failed.png"))
        except Exception as e:
            log_event("warning", f"Post-submit debug screenshot failed: {e}")

    return True

def discover_internal_links(page, base_url):
    base_netloc = urlparse(base_url).netloc
    hrefs = page.eval_on_selector_all("a[href]", "elements => elements.map(el => el.getAttribute('href'))")
    internal = set()
    for href in hrefs:
        if not href or href.startswith("#") or href.startswith("mailto:") or href.startswith("tel:"):
            continue
        full_url = urljoin(base_url, href)
        if urlparse(full_url).netloc == base_netloc:
            cleaned = full_url.split("#")[0]
            internal.add(cleaned)
    return internal

def extract_page_components(page, page_url):
    components = []
    retrieved_at = datetime.now(timezone.utc).isoformat()
    for component_type, selector in COMPONENT_SELECTORS.items():
        try:
            elements = page.query_selector_all(selector)
        except Exception as e:
            log_event("warning", f"Selector failed for {component_type} on {page_url}: {e}")
            continue
        for idx, el in enumerate(elements):
            try:
                text_content = (el.inner_text() or "").strip()
            except Exception:
                text_content = None
            try:
                bounding_box = el.bounding_box()
                visible = bounding_box is not None and bounding_box["width"] > 0 and bounding_box["height"] > 0
            except Exception:
                visible = None
            try:
                structural_selector = page.evaluate(
                    """(el) => {
                        function cssPath(el) {
                            if (!(el instanceof Element)) return '';
                            const path = [];
                            while (el.nodeType === Node.ELEMENT_NODE) {
                                let selector = el.nodeName.toLowerCase();
                                if (el.id) {
                                    selector += '#' + el.id;
                                    path.unshift(selector);
                                    break;
                                } else {
                                    let sib = el, nth = 1;
                                    while (sib = sib.previousElementSibling) {
                                        if (sib.nodeName.toLowerCase() === selector) nth++;
                                    }
                                    selector += `:nth-of-type(${nth})`;
                                }
                                path.unshift(selector);
                                el = el.parentElement;
                            }
                            return path.join(' > ');
                        }
                        return cssPath(el);
                    }""",
                    el,
                )
            except Exception:
                structural_selector = f"{selector}[{idx}]"
            component = {
                "page_url": page_url,
                "component_type": component_type,
                "component_selector": structural_selector,
                "actual_text_content": text_content if text_content else None,
                "expected_text_content": None,
                "guideline_reference": None,
                "discrepancy_flag": None,
                "discrepancy_reason": None,
                "screenshot_path": None,
                "is_visible": visible,
                "retrieved_at": retrieved_at,
            }
            components.append(component)
    return components

def run_extraction():
    UI_STATES_DIR.mkdir(parents=True, exist_ok=True)
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    coverage = {
        "discovered_urls": [], "successful_urls": [], "failed_urls": [],
        "started_at": datetime.now(timezone.utc).isoformat(),
    }
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()
        page.set_default_timeout(NAV_TIMEOUT_MS)
        log_event("info", "Starting login flow")
        success, _ = with_retries(lambda: perform_login(page), "login")
        if not success:
            log_event("error", "Login failed after retries. Aborting extraction.")
            browser.close()
            return
        log_event("info", f"Login flow completed. Current URL: {page.url}")
        to_visit = {page.url, BASE_URL}
        visited = set()
        all_components = []
        while to_visit and len(visited) < MAX_PAGES:
            url = to_visit.pop()
            if url in visited:
                continue
            visited.add(url)
            coverage["discovered_urls"].append(url)
            def visit_and_extract(url=url, current_url=page.url):
                if url != current_url:
                    try:
                        page.goto(url, wait_until="networkidle", timeout=NAV_TIMEOUT_MS)
                    except PlaywrightTimeoutError:
                        log_event("warning", f"networkidle timed out for {url}; falling back to domcontentloaded.")
                        page.wait_for_load_state("domcontentloaded", timeout=NAV_TIMEOUT_MS)
                page.wait_for_timeout(1000)
                return True
            ok, _ = with_retries(visit_and_extract, f"visit {url}")
            if not ok:
                coverage["failed_urls"].append(url)
                continue
            try:
                components = extract_page_components(page, url)
            except Exception as e:
                log_event("error", f"Extraction failed for {url}: {e}\n{traceback.format_exc()}")
                coverage["failed_urls"].append(url)
                continue
            screenshot_name = f"{safe_filename(url)}.png"
            screenshot_path = SCREENSHOTS_DIR / screenshot_name
            try:
                page.screenshot(path=str(screenshot_path), full_page=True)
                rel_path = str(screenshot_path.relative_to(PROJECT_ROOT))
            except Exception as e:
                log_event("warning", f"Screenshot failed for {url}: {e}")
                rel_path = None
            for c in components:
                c["screenshot_path"] = rel_path
            all_components.extend(components)
            coverage["successful_urls"].append(url)
            log_event("info", f"Extracted {len(components)} components from {url}")
            try:
                new_links = discover_internal_links(page, url)
                for link in new_links:
                    if link not in visited:
                        to_visit.add(link)
            except Exception as e:
                log_event("warning", f"Link discovery failed for {url}: {e}")
        browser.close()
    output_path = UI_STATES_DIR / "extracted_ui_state.jsonl"
    with open(output_path, "w", encoding="utf-8") as f:
        for component in all_components:
            f.write(json.dumps(component) + "\n")
    coverage["finished_at"] = datetime.now(timezone.utc).isoformat()
    coverage["total_components_extracted"] = len(all_components)
    coverage["pages_visited"] = len(visited)
    with open(COVERAGE_PATH, "w", encoding="utf-8") as f:
        json.dump(coverage, f, indent=2)
    log_event("info", f"Extraction complete. {len(all_components)} components across {len(visited)} pages. Output: {output_path}")

if __name__ == "__main__":
    run_extraction()
