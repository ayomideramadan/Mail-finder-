"""
╔══════════════════════════════════════════════════════════════════════╗
║         RAMADAN AYOMIDE - AUTHOR EMAIL FINDER                       ║
║         Complete Single-File Application (app.py)                   ║
║         Private Book Marketing Intelligence Tool                    ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import os
import re
import io
import time
import random
import requests
import pandas as pd
import streamlit as st
from datetime import datetime
from urllib.parse import urlparse, urljoin, unquote, quote
from bs4 import BeautifulSoup


# ══════════════════════════════════════════════════════════════════════
#  SECTION 1 ── CONFIGURATION & CONSTANTS
# ══════════════════════════════════════════════════════════════════════

ACCESS_PASSWORD = os.environ.get("APP_PASSWORD", "RamadanAyomide2024!")

REQUEST_DELAY   = 2.5          # seconds between requests (rate-limit safety)
REQUEST_TIMEOUT = 15           # seconds before a request times out
MAX_BULK_ROWS   = 500          # maximum authors allowed in a single bulk upload
MAX_EMAILS_OUT  = 5            # maximum emails returned per author

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36",

    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36",

    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) "
    "Gecko/20100101 Firefox/121.0",

    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) "
    "Version/17.2 Safari/605.1.15",

    "Mozilla/5.0 (X11; Linux x86_64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36",
]

# Domains that are never the author's personal site
BLOCKED_DOMAINS = {
    "google.com", "google.co", "googleapis.com", "gstatic.com",
    "youtube.com", "facebook.com", "twitter.com", "x.com",
    "instagram.com", "linkedin.com", "pinterest.com", "tiktok.com",
    "reddit.com", "wikipedia.org", "amazon.com", "amazon.co",
    "goodreads.com", "barnesandnoble.com", "bookdepository.com",
    "webcache.googleusercontent.com", "translate.google.com",
    "maps.google.com", "play.google.com", "accounts.google.com",
    "bing.com", "yahoo.com", "duckduckgo.com", "yelp.com",
    "tripadvisor.com", "imdb.com", "spotify.com", "apple.com",
    "microsoft.com", "github.com", "stackoverflow.com",
    "worldcat.org", "openlibrary.org", "archive.org",
}

# URL path keywords that suggest the author's official site
TRUSTED_URL_SIGNALS = [
    "author", "official", "writer", "books", "contact",
    "about", "portfolio", "blog", "novelist", "poet",
]

# File-like extensions that appear in obfuscated code — not real emails
EXCLUDED_EMAIL_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".bmp",
    ".ico", ".tiff", ".css", ".js", ".woff", ".woff2", ".ttf",
    ".eot", ".map", ".json", ".xml", ".html", ".htm", ".php",
    ".py", ".rb", ".java", ".c", ".cpp", ".ts", ".tsx", ".jsx",
}

# Generic mailbox prefixes — kept but deprioritised
GENERIC_EMAIL_PREFIXES = {
    "info", "admin", "webmaster", "noreply", "no-reply",
    "support", "help", "sales", "marketing", "contact",
    "hello", "mail", "office", "team", "enquiries", "enquiry",
}

# Domains that are almost certainly not the author's personal email
EXCLUDED_EMAIL_DOMAINS = {
    "example.com", "test.com", "domain.com", "email.com",
    "yoursite.com", "sentry.io", "sentry-next.com",
    "w3schools.com", "w3.org", "schema.org",
}


# ══════════════════════════════════════════════════════════════════════
#  SECTION 2 ── HTTP HELPERS
# ══════════════════════════════════════════════════════════════════════

def _random_headers() -> dict:
    """Return browser-like request headers with a random User-Agent."""
    return {
        "User-Agent":                random.choice(USER_AGENTS),
        "Accept":                    "text/html,application/xhtml+xml,"
                                     "application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language":           "en-US,en;q=0.9",
        "Accept-Encoding":           "gzip, deflate",
        "DNT":                       "1",
        "Connection":                "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Cache-Control":             "max-age=0",
    }


def _safe_get(url: str, timeout: int = REQUEST_TIMEOUT) -> requests.Response | None:
    """
    Perform a GET request and return the Response object.
    Returns None on any network or HTTP error.
    """
    try:
        resp = requests.get(
            url,
            headers=_random_headers(),
            timeout=timeout,
            allow_redirects=True,
            verify=True,
        )
        if resp.status_code == 200:
            return resp
    except Exception:
        pass
    return None


# ══════════════════════════════════════════════════════════════════════
#  SECTION 3 ── SEARCH ENGINE  (Google → DuckDuckGo fallback)
# ══════════════════════════════════════════════════════════════════════

def _is_blocked(url: str) -> bool:
    """Return True if the URL belongs to a blocked / generic domain."""
    try:
        host = urlparse(url).netloc.lower().lstrip("www.")
        return any(host == b or host.endswith("." + b) for b in BLOCKED_DOMAINS)
    except Exception:
        return True


def _score_url(url: str, author_name: str) -> int:
    """
    Heuristic score — higher means more likely to be the author's
    personal / official website.
    """
    score = 0
    url_lower = url.lower()
    parts = [p for p in author_name.lower().split() if len(p) > 2]

    # Author name fragments in URL
    for part in parts:
        if part in url_lower:
            score += 15

    # Trusted keyword signals in URL path
    for signal in TRUSTED_URL_SIGNALS:
        if signal in url_lower:
            score += 5

    # Prefer root / near-root pages
    path = urlparse(url).path.rstrip("/")
    if path in ("", "/", "/contact", "/about", "/home"):
        score += 10

    # Prefer .com TLD
    if url_lower.endswith(".com") or ".com/" in url_lower:
        score += 3

    # Penalise very long URLs (deep archive / parameter pages)
    if len(url) > 120:
        score -= 8

    return score


def _extract_urls_from_html(html: str) -> list[str]:
    """Pull every usable URL out of a Google-results HTML page."""
    urls = []
    soup = BeautifulSoup(html, "html.parser")

    for a in soup.find_all("a", href=True):
        href = a["href"]

        # Google wraps real URLs inside /url?q=...
        if "/url?q=" in href:
            m = re.search(r"/url\?q=(https?://[^&]+)", href)
            if m:
                clean = unquote(m.group(1))
                if not _is_blocked(clean):
                    urls.append(clean)
        elif href.startswith("http") and not _is_blocked(href):
            urls.append(href)

    # Also sweep raw text for bare URLs
    raw = re.findall(
        r"https?://(?:www\.)?[-a-zA-Z0-9@:%._+~#=]{1,256}"
        r"\.[a-zA-Z0-9()]{1,6}"
        r"\b[-a-zA-Z0-9()@:%_+.~#?&/=]*",
        html,
    )
    for u in raw:
        if not _is_blocked(u) and u not in urls:
            urls.append(u)

    return urls


def _google_search(author_name: str) -> list[str]:
    """Query Google with three tailored searches; return all found URLs."""
    queries = [
        f"{author_name} official website contact",
        f"{author_name} author website",
        f"{author_name} author contact email",
    ]
    all_urls: list[str] = []

    for q in queries:
        url = f"https://www.google.com/search?q={quote(q)}&num=10&hl=en"
        resp = _safe_get(url)
        if resp:
            all_urls.extend(_extract_urls_from_html(resp.text))
        time.sleep(1)

    return all_urls


def _duckduckgo_search(author_name: str) -> list[str]:
    """Fallback: DuckDuckGo HTML search."""
    q = f"{author_name} author official website contact"
    url = f"https://html.duckduckgo.com/html/?q={quote(q)}"
    resp = _safe_get(url)
    if not resp:
        return []

    urls = []
    soup = BeautifulSoup(resp.text, "html.parser")
    for link in soup.find_all("a", {"class": "result__a"}, href=True):
        href = link["href"]
        if "uddg=" in href:
            m = re.search(r"uddg=(https?://[^&]+)", href)
            if m:
                clean = unquote(m.group(1))
                if not _is_blocked(clean):
                    urls.append(clean)
        elif href.startswith("http") and not _is_blocked(href):
            urls.append(href)

    return urls


def find_author_website(author_name: str) -> str | None:
    """
    Public function: return the single best-scoring URL for an author,
    or None if nothing credible is found.
    """
    raw_urls = _google_search(author_name)

    if not raw_urls:
        raw_urls = _duckduckgo_search(author_name)

    if not raw_urls:
        return None

    # Deduplicate (strip trailing slashes / anchors for comparison)
    seen: set[str] = set()
    unique: list[str] = []
    for u in raw_urls:
        key = u.split("#")[0].split("?")[0].rstrip("/")
        if key not in seen:
            seen.add(key)
            unique.append(u)

    # Score and return the winner
    ranked = sorted(unique, key=lambda u: _score_url(u, author_name), reverse=True)
    return ranked[0] if ranked else None


# ══════════════════════════════════════════════════════════════════════
#  SECTION 4 ── EMAIL EXTRACTION ENGINE
# ══════════════════════════════════════════════════════════════════════

# Master email regex (verbose for readability)
_EMAIL_RE = re.compile(
    r"""
    (?:mailto:)?                        # optional mailto: prefix
    (
        [a-zA-Z0-9]                     # local part must start alphanumeric
        [a-zA-Z0-9._%+\-]{0,63}        # rest of local part
        @                               # separator
        [a-zA-Z0-9]                     # domain start
        [a-zA-Z0-9.\-]{0,252}          # domain body
        \.                              # dot before TLD
        [a-zA-Z]{2,20}                 # TLD
    )
    """,
    re.VERBOSE | re.IGNORECASE,
)

# Patterns that identify fake / system-generated email-like strings
_FALSE_POSITIVE_RE = re.compile(
    r"(\d{10,}|[0-9a-f]{32}|sentry|webpack|node_modules|"
    r"placeholder|example\.com|domain\.com|email\.com|"
    r"yourname|username|youremail|test@|foo@|bar@)",
    re.IGNORECASE,
)


def _is_valid_email(email: str) -> bool:
    """Validate a candidate email string with heuristic filters."""
    if not re.match(
        r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$", email
    ):
        return False

    local, domain = email.split("@", 1)

    # Length sanity
    if len(local) < 1 or len(domain) < 4:
        return False

    # Bad TLDs / internal domains
    for bad in (".example", ".test", ".invalid", ".localhost", ".internal"):
        if email.endswith(bad):
            return False

    # Excluded email domains
    if domain.lower() in EXCLUDED_EMAIL_DOMAINS:
        return False

    # False-positive pattern match
    if _FALSE_POSITIVE_RE.search(email):
        return False

    # Must not end with an excluded file extension
    for ext in EXCLUDED_EMAIL_EXTENSIONS:
        if email.lower().endswith(ext):
            return False

    return True


def _prioritise(emails: list[str]) -> list[str]:
    """
    Place personal / named emails before generic mailbox prefixes,
    and remove complete duplicates.
    """
    seen: set[str] = set()
    personal: list[str] = []
    generic: list[str]  = []

    for e in emails:
        e_low = e.lower()
        if e_low in seen:
            continue
        seen.add(e_low)

        local = e_low.split("@")[0]
        if local in GENERIC_EMAIL_PREFIXES:
            generic.append(e)
        else:
            personal.append(e)

    return personal + generic


def _raw_emails_from_text(text: str) -> list[str]:
    """Find all raw email candidates in a block of text."""
    candidates = _EMAIL_RE.findall(text)
    return [e.strip().rstrip(".").lower() for e in candidates]


def _decode_cloudflare_email(encoded: str) -> str | None:
    """Reverse Cloudflare's __cf_email__ XOR encoding."""
    try:
        key = int(encoded[:2], 16)
        decoded = "".join(
            chr(int(encoded[i: i + 2], 16) ^ key)
            for i in range(2, len(encoded), 2)
        )
        return decoded if _is_valid_email(decoded) else None
    except Exception:
        return None


def _decode_obfuscated(soup: BeautifulSoup) -> list[str]:
    """
    Attempt to recover emails hidden behind common obfuscation tricks:
      1. Cloudflare data-cfemail attributes
      2. JavaScript reversed-string patterns
      3. 'name [at] domain [dot] tld' human-readable substitutions
    """
    found: list[str] = []

    # ── 1. Cloudflare protection
    for tag in soup.find_all(attrs={"data-cfemail": True}):
        result = _decode_cloudflare_email(tag["data-cfemail"])
        if result:
            found.append(result)

    # ── 2. Reversed strings inside <script> tags
    for script in soup.find_all("script"):
        if not script.string:
            continue
        rev_pat = r"['\"]([a-zA-Z0-9._%+\-]+\.[a-zA-Z]{2,}@[a-zA-Z0-9._%+\-]+)['\"]"
        for m in re.findall(rev_pat, script.string):
            candidate = m[::-1]
            if _is_valid_email(candidate):
                found.append(candidate)

    # ── 3.  'user [at] domain [dot] com' pattern in visible text
    at_dot_re = re.compile(
        r"([a-zA-Z0-9._%+\-]+)"
        r"\s*[\[\(]?\s*(?:at|AT)\s*[\]\)]?\s*"
        r"([a-zA-Z0-9.\-]+)"
        r"\s*[\[\(]?\s*(?:dot|DOT)\s*[\]\)]?\s*"
        r"([a-zA-Z]{2,})",
        re.IGNORECASE,
    )
    for m in at_dot_re.finditer(soup.get_text()):
        candidate = f"{m.group(1)}@{m.group(2)}.{m.group(3)}".lower()
        if _is_valid_email(candidate):
            found.append(candidate)

    return found


def _contact_page_urls(base_url: str, soup: BeautifulSoup) -> list[str]:
    """
    Return up to 5 internal links whose text / href suggests a
    contact or about page.
    """
    keywords = {
        "contact", "about", "reach", "connect",
        "email", "get-in-touch", "reach-out", "hire",
    }
    pages: list[str] = []

    for a in soup.find_all("a", href=True):
        href_low = a["href"].lower()
        text_low = a.get_text().lower()
        if any(kw in href_low or kw in text_low for kw in keywords):
            full = urljoin(base_url, a["href"])
            if full not in pages:
                pages.append(full)

    return pages[:5]


def scrape_emails_from_url(url: str) -> list[str]:
    """
    Public function: scrape a URL (and its contact sub-pages) for
    email addresses. Returns a deduplicated, prioritised list.
    """
    all_emails: list[str] = []

    # ── Fetch the main page
    resp = _safe_get(url)
    if not resp:
        return []

    html   = resp.text
    soup   = BeautifulSoup(html, "html.parser")
    text   = soup.get_text(separator=" ")

    # Pass 1 – visible text
    all_emails.extend(_raw_emails_from_text(text))

    # Pass 2 – raw HTML source (catches encoded / commented-out addresses)
    for e in _raw_emails_from_text(html):
        if e not in all_emails:
            all_emails.append(e)

    # Pass 3 – explicit mailto: href values (highest confidence)
    for a in soup.find_all("a", href=True):
        if "mailto:" in a["href"].lower():
            m = re.search(
                r"mailto:([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})",
                a["href"],
                re.IGNORECASE,
            )
            if m:
                e = m.group(1).lower()
                if _is_valid_email(e):
                    # Insert at front – these are most trustworthy
                    if e in all_emails:
                        all_emails.remove(e)
                    all_emails.insert(0, e)

    # Pass 4 – obfuscation decoding
    for e in _decode_obfuscated(soup):
        if e not in all_emails:
            all_emails.append(e)

    # Pass 5 – scan contact/about sub-pages if nothing found yet
    if not all_emails:
        for sub_url in _contact_page_urls(url, soup):
            if sub_url.rstrip("/") == url.rstrip("/"):
                continue
            sub_resp = _safe_get(sub_url)
            if not sub_resp:
                continue

            sub_soup = BeautifulSoup(sub_resp.text, "html.parser")
            sub_text = sub_soup.get_text(separator=" ")

            sub_emails = _raw_emails_from_text(sub_text)
            sub_emails += _raw_emails_from_text(sub_resp.text)

            for a in sub_soup.find_all("a", href=True):
                if "mailto:" in a["href"].lower():
                    m = re.search(
                        r"mailto:([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})",
                        a["href"],
                        re.IGNORECASE,
                    )
                    if m:
                        e = m.group(1).lower()
                        if _is_valid_email(e):
                            sub_emails.insert(0, e)

            sub_emails += _decode_obfuscated(sub_soup)

            for e in sub_emails:
                if e not in all_emails:
                    all_emails.append(e)

            if all_emails:
                break   # Found something — stop scanning more sub-pages

    # Final filter + prioritise
    valid = [e for e in all_emails if _is_valid_email(e)]
    return _prioritise(valid)[:MAX_EMAILS_OUT]


# ══════════════════════════════════════════════════════════════════════
#  SECTION 5 ── CORE SEARCH ORCHESTRATOR
# ══════════════════════════════════════════════════════════════════════

def find_author_email(author_name: str) -> dict:
    """
    Master function that ties the search engine and scraper together.
    Always returns a fully-populated result dictionary — never a blank.
    """
    result = {
        "Author Name":          author_name.strip(),
        "Official Website URL": "No website found",
        "Found Email Address":  "No direct email found. Check page manually.",
    }

    try:
        website = find_author_website(author_name.strip())

        if website:
            result["Official Website URL"] = website
            emails = scrape_emails_from_url(website)

            if emails:
                result["Found Email Address"] = ", ".join(emails)
            # else: fallback message already set above

        # If no website, both fallback messages remain in place

    except Exception as exc:
        result["Found Email Address"] = (
            f"Search error — {str(exc)[:100]}"
        )

    return result


# ══════════════════════════════════════════════════════════════════════
#  SECTION 6 ── STREAMLIT UI
# ══════════════════════════════════════════════════════════════════════

# ── 6-A  Page config (must be first Streamlit call) ──────────────────

st.set_page_config(
    page_title="Ramadan Ayomide – Author Email Finder",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ── 6-B  CSS injection ────────────────────────────────────────────────

def _inject_css() -> None:
    st.markdown(
        """
        <style>
        /* ── App background ── */
        .stApp { background: linear-gradient(135deg,#f4f6f8 0%,#e8ecf0 100%); }

        /* ── Top header banner ── */
        .app-header {
            background: linear-gradient(135deg,#1B4332 0%,#2D6A4F 60%,#40916C 100%);
            padding: 2rem 2.5rem;
            border-radius: 16px;
            margin-bottom: 1.8rem;
            box-shadow: 0 8px 32px rgba(27,67,50,.35);
            text-align: center;
        }
        .app-header h1 {
            color:#fff; font-family:'Georgia',serif;
            font-size:2.3rem; margin:0; letter-spacing:.8px;
       
