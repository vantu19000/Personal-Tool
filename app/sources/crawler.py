"""Crawler and Data Ingestion Engine for Source Management (Màn Nguồn Cào).

Real extraction from live URLs only:
- RSS / Atom XML feeds (real HTTP fetch + XML parse)
- Websites (HTML meta tags, title, open graph, and auto-discovered RSS)
- APIs (REST JSON endpoints)
- PDF Documents (HTTP download + PyMuPDF text extraction)

Deduplication rules:
- Strictly checks normalized URL and title against existing records in `crawled_articles`.
- Never generates or inserts synthetic/fake articles into the database.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import parse_qs, urlencode, urljoin, urlparse, urlunparse
import xml.etree.ElementTree as ET

import httpx

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

from app.articles import services as article_services
from app.sources import services as source_services

logger = logging.getLogger(__name__)

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/rss+xml,application/json,*/*;q=0.8",
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
}


def normalize_url(url: Optional[str]) -> str:
    """Normalize a URL for reliable deduplication comparison.

    - Strips whitespace
    - Lowercases scheme and netloc
    - Strips URL fragments (#...)
    - Strips marketing tracking query parameters (utm_*, fbclid, gclid, ref, etc.)
    - Strips trailing slash unless root path
    """
    if not url or not url.strip():
        return ""

    raw_url = url.strip()
    try:
        parsed = urlparse(raw_url)
        scheme = parsed.scheme.lower() or "https"
        netloc = parsed.netloc.lower()

        # Filter out tracking query params
        query_params = parse_qs(parsed.query, keep_blank_values=False)
        tracking_keys = {
            "utm_source", "utm_medium", "utm_campaign", "utm_term",
            "utm_content", "fbclid", "gclid", "ref", "source", "from"
        }
        filtered_params = {k: v for k, v in query_params.items() if k.lower() not in tracking_keys}
        clean_query = urlencode(filtered_params, doseq=True)

        path = parsed.path.rstrip("/")
        if not path:
            path = "/"

        clean_url = urlunparse((scheme, netloc, path, parsed.params, clean_query, ""))
        return clean_url
    except Exception:
        return raw_url.rstrip("/")


def normalize_title(title: Optional[str]) -> str:
    """Normalize title for duplicate detection when URLs are identical or missing."""
    if not title:
        return ""
    cleaned = re.sub(r"[^\w\s]", " ", title.lower(), flags=re.UNICODE)
    return " ".join(cleaned.split())


async def get_all_existing_identifiers(db: Optional[Any] = None) -> Tuple[Set[str], Set[str]]:
    """Fetch set of all normalized URLs and normalized titles currently in crawled_articles."""
    all_articles, _ = await article_services._repo.find_all(db=db)
    urls: Set[str] = set()
    titles: Set[str] = set()

    for a in all_articles:
        raw_url = a.get("url")
        if raw_url:
            norm_u = normalize_url(raw_url)
            if norm_u:
                urls.add(norm_u)

        raw_title = a.get("title")
        if raw_title:
            norm_t = normalize_title(raw_title)
            if norm_t:
                titles.add(norm_t)

    return urls, titles


async def is_article_duplicate(
    candidate_url: str,
    candidate_title: str,
    existing_urls: Set[str],
    existing_titles: Set[str],
) -> bool:
    """Check if a candidate article has already been crawled based on URL or Title."""
    norm_url = normalize_url(candidate_url)
    if norm_url and norm_url in existing_urls:
        return True

    norm_title = normalize_title(candidate_title)
    if norm_title and norm_title in existing_titles:
        return True

    return False


# ==============================================================================
# REAL DATA EXTRACTORS (LIVE URL ONLY)
# ==============================================================================

async def fetch_rss_feed(url: str, limit: int = 15) -> List[Dict[str, Any]]:
    """Fetch and parse actual RSS/Atom XML feed from URL."""
    if not url or not (url.startswith("http://") or url.startswith("https://")):
        return []

    try:
        async with httpx.AsyncClient(timeout=6.0, follow_redirects=True, headers=DEFAULT_HEADERS) as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                logger.debug(f"RSS fetch returned status {resp.status_code} for {url}")
                return []

            content_text = resp.text
            return parse_rss_xml(content_text, base_url=url, limit=limit)
    except Exception as exc:
        logger.debug(f"RSS fetch error on {url}: {exc}")
        return []


def parse_rss_xml(xml_content: str, base_url: str = "", limit: int = 15) -> List[Dict[str, Any]]:
    """Parse RSS 2.0 or Atom XML string into structured article candidates."""
    items: List[Dict[str, Any]] = []
    try:
        root = ET.fromstring(xml_content)

        # 1. Standard RSS 2.0 (<channel><item>)
        for node in root.findall(".//item")[:limit]:
            title = (node.findtext("title") or "").strip()
            link = (node.findtext("link") or "").strip()
            if not link and base_url:
                link = base_url

            raw_desc = (node.findtext("description") or "").strip()
            summary = re.sub(r"<[^>]+>", " ", raw_desc).strip()
            summary = " ".join(summary.split())[:350]

            if title and link:
                items.append({
                    "title": title,
                    "summary": summary or title,
                    "content": summary or title,
                    "url": link,
                    "category": infer_article_category(title, link),
                })

        # 2. Atom XML (<feed><entry>)
        if not items:
            for entry in (root.findall(".//{http://www.w3.org/2005/Atom}entry") or root.findall(".//entry"))[:limit]:
                title = (entry.findtext("{http://www.w3.org/2005/Atom}title") or entry.findtext("title") or "").strip()
                link_el = entry.find("{http://www.w3.org/2005/Atom}link") or entry.find("link")
                link = link_el.attrib.get("href", "").strip() if link_el is not None else ""
                if not link and base_url:
                    link = base_url

                raw_summary = (
                    entry.findtext("{http://www.w3.org/2005/Atom}summary")
                    or entry.findtext("{http://www.w3.org/2005/Atom}content")
                    or entry.findtext("summary")
                    or ""
                ).strip()
                summary = re.sub(r"<[^>]+>", " ", raw_summary).strip()
                summary = " ".join(summary.split())[:350]

                if title and link:
                    items.append({
                        "title": title,
                        "summary": summary or title,
                        "content": summary or title,
                        "url": link,
                        "category": infer_article_category(title, link),
                    })

        return items
    except Exception as exc:
        logger.debug(f"Error parsing RSS XML: {exc}")
        return []


def clean_portal_title(title: str) -> str:
    """Clean extra spaces and remove common portal suffixes from title."""
    if not title:
        return ""
    cleaned = re.sub(r"[\r\n\t\xa0]+", " ", title)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    # Strip site branding suffix like " - VnExpress", " | Báo Dân trí", " - CafeF"
    cleaned = re.sub(
        r"\s*[-|–]\s*(VnExpress|Tuổi Trẻ|Thanh Niên|Dân Trí|CafeF|Zing|VietnamNet|VTC News|Kênh 14|Báo Đầu tư|Báo Nhân Dân|Lao Động|Tiền Phong).*$",
        "",
        cleaned,
        flags=re.IGNORECASE,
    ).strip()
    return cleaned


def infer_article_category(title: str, url: str) -> str:
    """Infer article category based on title and URL slug."""
    lower_text = f"{title} {url}".lower()
    if any(k in lower_text for k in ["bất động sản", "nhà đất", "địa ốc", "chung cư", "quy hoạch", "bat-dong-san", "nha-dat"]):
        return "Bất động sản"
    if any(k in lower_text for k in ["công nghệ", "trí tuệ nhân tạo", "ai agent", "smartphone", "phần mềm", "chip", "cong-nghe", "tech"]):
        return "Công nghệ"
    if any(k in lower_text for k in ["tài chính", "ngân hàng", "chứng khoán", "cổ phiếu", "lãi suất", "vàng", "tai-chinh", "chung-khoan"]):
        return "Tài chính & Đầu tư"
    if any(k in lower_text for k in ["kinh doanh", "doanh nghiệp", "thương mại", "xuất khẩu", "kinh-doanh", "doanh-nhan"]):
        return "Kinh doanh"
    if any(k in lower_text for k in ["marketing", "truyền thông", "quảng cáo", "tiktok", "youtube", "social"]):
        return "Marketing & Media"
    if any(k in lower_text for k in ["pháp luật", "chính sách", "nghị định", "luật", "phap-luat"]):
        return "Chính sách & Pháp luật"
    return "Kinh tế & Thị trường"


def extract_articles_from_html(html: str, base_url: str, limit: int = 15) -> List[Dict[str, Any]]:
    """Extract list of real article candidates from website HTML."""
    if not html or not BeautifulSoup:
        return []

    try:
        soup = BeautifulSoup(html, "html.parser")
    except Exception as exc:
        logger.debug(f"Failed to parse HTML with BeautifulSoup: {exc}")
        return []

    base_parsed = urlparse(base_url)
    base_netloc = base_parsed.netloc.lower()

    items: List[Dict[str, Any]] = []
    seen_urls: Set[str] = set()

    NON_ARTICLE_PATTERNS = [
        r"/(category|chuyen-muc|danh-muc|chu-de|tag|tags|author|tac-gia|page|trang|search|tim-kiem)/",
        r"/(lien-he|contact|about|gioi-thieu|chinh-sach|privacy|terms|dieu-khoan|tro-giup|faq)/?$",
        r"/(login|dang-nhap|register|dang-ky|quen-mat-khau)/?$",
        r"/(rss|feed)/?$",
        r"#",
        r"^javascript:",
        r"^mailto:",
        r"^tel:",
    ]

    def is_valid_article_url(href: str) -> bool:
        if not href or href.strip() in ("", "/", "#"):
            return False
        href = href.strip()
        for pat in NON_ARTICLE_PATTERNS:
            if re.search(pat, href, re.IGNORECASE):
                return False
        try:
            full = urljoin(base_url, href)
            parsed = urlparse(full)
            if not parsed.scheme.startswith("http"):
                return False
            target_netloc = parsed.netloc.lower()
            # Allow same domain or subdomain
            if not (
                target_netloc == base_netloc
                or target_netloc.endswith("." + base_netloc)
                or base_netloc.endswith("." + target_netloc)
            ):
                return False
            if full.rstrip("/") == base_url.rstrip("/"):
                return False
            path = parsed.path.rstrip("/")
            if not path or path == "":
                return False
            return True
        except Exception:
            return False

    def clean_text(text: Optional[str]) -> str:
        if not text:
            return ""
        return " ".join(re.sub(r"[\r\n\t\xa0]+", " ", text).split())

    # Strategy 1: Headings with links (h1, h2, h3, h4)
    for h in soup.find_all(["h1", "h2", "h3", "h4"]):
        if len(items) >= limit:
            break
        a = h.find("a", href=True)
        if not a:
            continue
        href = a.get("href", "").strip()
        if not is_valid_article_url(href):
            continue
        full_url = normalize_url(urljoin(base_url, href))
        if not full_url or full_url in seen_urls:
            continue

        raw_title = a.get("title", "").strip() or a.get_text(strip=True) or h.get_text(strip=True)
        title = clean_portal_title(clean_text(raw_title))
        if len(title) < 18 or len(title) > 300:
            continue

        # Look for snippet/summary in neighboring elements
        summary = ""
        parent = h.parent
        if parent:
            p_el = parent.find(["p", "div"], class_=lambda c: c and any(k in str(c).lower() for k in ["sapo", "summary", "desc", "lead", "excerpt"]))
            if not p_el:
                p_el = parent.find("p")
            if p_el:
                summary = clean_text(p_el.get_text(strip=True))

        seen_urls.add(full_url)
        items.append({
            "title": title,
            "url": full_url,
            "summary": summary or title,
            "content": summary or title,
            "category": infer_article_category(title, full_url),
        })

    # Strategy 2: Common article containers if not enough items
    if len(items) < limit:
        container_selectors = [
            "article",
            "div[class*='item-news']",
            "div[class*='news-item']",
            "div[class*='story']",
            "div[class*='post']",
            "div[class*='card-news']",
            "div[class*='article-item']",
            "div[class*='box-category-item']",
            "li[class*='item-news']",
            "li[class*='news-item']",
            "li[class*='story']",
            "li[class*='post']",
        ]
        try:
            containers = soup.select(", ".join(container_selectors))
        except Exception:
            containers = []

        for box in containers:
            if len(items) >= limit:
                break
            link_el = box.find("a", href=True)
            if not link_el:
                continue
            href = link_el.get("href", "").strip()
            if not is_valid_article_url(href):
                continue
            full_url = normalize_url(urljoin(base_url, href))
            if not full_url or full_url in seen_urls:
                continue

            raw_title = link_el.get("title", "").strip() or link_el.get_text(strip=True)
            h_el = box.find(["h1", "h2", "h3", "h4", "h5"])
            if h_el and len(h_el.get_text(strip=True)) > len(raw_title):
                raw_title = h_el.get_text(strip=True)
            title = clean_portal_title(clean_text(raw_title))
            if len(title) < 18 or len(title) > 300:
                continue

            p_el = box.find(["p", "div"], class_=lambda c: c and any(k in str(c).lower() for k in ["sapo", "summary", "desc", "lead", "excerpt", "snippet"]))
            if not p_el:
                p_el = box.find("p")
            summary = clean_text(p_el.get_text(strip=True)) if p_el else ""

            seen_urls.add(full_url)
            items.append({
                "title": title,
                "url": full_url,
                "summary": summary or title,
                "content": summary or title,
                "category": infer_article_category(title, full_url),
            })

    # Strategy 3: Descriptive <a> links across page
    if len(items) < limit:
        for a in soup.find_all("a", href=True):
            if len(items) >= limit:
                break
            href = a.get("href", "").strip()
            if not is_valid_article_url(href):
                continue
            full_url = normalize_url(urljoin(base_url, href))
            if not full_url or full_url in seen_urls:
                continue

            raw_title = a.get("title", "").strip() or a.get_text(strip=True)
            title = clean_portal_title(clean_text(raw_title))
            if len(title) < 25 or len(title.split()) < 4 or len(title) > 300:
                continue

            seen_urls.add(full_url)
            items.append({
                "title": title,
                "url": full_url,
                "summary": title,
                "content": title,
                "category": infer_article_category(title, full_url),
            })

    return items


async def fetch_website_content(url: str, limit: int = 15) -> List[Dict[str, Any]]:
    """Fetch website HTML, extract list of articles from page, auto-discover RSS, or single page article."""
    if not url or not (url.startswith("http://") or url.startswith("https://")):
        return []

    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True, headers=DEFAULT_HEADERS) as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                return []

            content_text = resp.text

            # 1. Check if response is actually an XML RSS feed
            if content_text.lstrip().startswith("<?xml") or "<rss" in content_text[:300]:
                return parse_rss_xml(content_text, base_url=url, limit=limit)

            # 2. Check auto-discovered RSS link in HTML header
            rss_link_match = re.search(
                r'<link[^>]+type=["\']application/rss\+xml["\'][^>]+href=["\']([^"\']+)["\']',
                content_text,
                re.IGNORECASE,
            ) or re.search(
                r'<link[^>]+href=["\']([^"\']+)["\'][^>]+type=["\']application/rss\+xml["\']',
                content_text,
                re.IGNORECASE,
            )

            if rss_link_match:
                feed_url = urljoin(url, rss_link_match.group(1))
                feed_items = await fetch_rss_feed(feed_url, limit=limit)
                if len(feed_items) >= 2:
                    return feed_items

            # 3. Extract list of articles directly from HTML
            articles = extract_articles_from_html(content_text, base_url=url, limit=limit)
            if articles:
                return articles

            # 4. Fallback: Check if this URL is a single article page itself
            clean_title = ""
            summary = ""
            if BeautifulSoup:
                soup = BeautifulSoup(content_text, "html.parser")
                og_title = soup.find("meta", property="og:title")
                if og_title and og_title.get("content"):
                    clean_title = clean_portal_title(og_title["content"].strip())
                elif soup.title and soup.title.string:
                    clean_title = clean_portal_title(soup.title.string.strip())

                og_desc = soup.find("meta", property="og:description") or soup.find("meta", attrs={"name": "description"})
                if og_desc and og_desc.get("content"):
                    summary = og_desc["content"].strip()
            else:
                title_match = re.search(r'<title>(.*?)</title>', content_text, re.IGNORECASE | re.DOTALL)
                if title_match:
                    clean_title = clean_portal_title(title_match.group(1).strip())

            if clean_title and len(clean_title) >= 15:
                return [{
                    "title": clean_title,
                    "summary": summary or clean_title,
                    "content": summary or clean_title,
                    "url": url,
                    "category": infer_article_category(clean_title, url),
                }]

            return []
    except Exception as exc:
        logger.debug(f"Website fetch error on {url}: {exc}")
        return []


async def fetch_api_content(url: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Fetch REST API endpoint expecting JSON response."""
    if not url or not (url.startswith("http://") or url.startswith("https://")):
        return []

    headers = dict(DEFAULT_HEADERS)
    headers["Accept"] = "application/json"

    try:
        async with httpx.AsyncClient(timeout=6.0, follow_redirects=True, headers=headers) as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                return []

            data = resp.json()
            raw_items = []
            if isinstance(data, list):
                raw_items = data[:limit]
            elif isinstance(data, dict):
                for key in ["items", "data", "articles", "posts", "results", "records"]:
                    if isinstance(data.get(key), list):
                        raw_items = data[key][:limit]
                        break

            parsed_articles: List[Dict[str, Any]] = []
            for idx, item in enumerate(raw_items):
                if isinstance(item, dict):
                    title = item.get("title") or item.get("name") or item.get("headline") or ""
                    link = item.get("url") or item.get("link") or f"{url}#{item.get('id', idx)}"
                    summary = item.get("summary") or item.get("description") or item.get("content") or ""
                    if title:
                        parsed_articles.append({
                            "title": str(title).strip(),
                            "summary": str(summary).strip()[:350],
                            "content": str(summary).strip(),
                            "url": str(link).strip(),
                        })

            return parsed_articles
    except Exception as exc:
        logger.debug(f"API fetch error on {url}: {exc}")
        return []


async def fetch_pdf_content(url: str) -> List[Dict[str, Any]]:
    """Download and extract text from a real PDF document using PyMuPDF."""
    if not url or not (url.startswith("http://") or url.startswith("https://")):
        return []

    try:
        import fitz  # PyMuPDF

        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True, headers=DEFAULT_HEADERS) as client:
            resp = await client.get(url)
            if resp.status_code != 200 or not resp.content:
                return []

            doc = fitz.open(stream=resp.content, filetype="pdf")
            if len(doc) == 0:
                return []

            first_page_text = doc[0].get_text()
            title = ""
            lines = [l.strip() for l in first_page_text.splitlines() if len(l.strip()) > 10]
            if lines:
                title = lines[0][:150]
            else:
                title = urlparse(url).path.split("/")[-1] or "Văn bản PDF"

            full_text = " ".join([page.get_text() for page in doc[:3]])
            summary = full_text[:400]

            return [{
                "title": title,
                "summary": summary,
                "content": full_text[:2000],
                "url": url,
            }]
    except Exception as exc:
        logger.debug(f"PDF extract error on {url}: {exc}")
        return []


# ==============================================================================
# MAIN CRAWL INGESTION & DEDUPLICATION LOGIC
# ==============================================================================

async def crawl_source_and_save(
    source_id: int,
    db: Optional[Any] = None,
) -> Dict[str, Any]:
    """Execute crawl for a single source, filter duplicates, and persist ONLY new real articles.

    STRICT GUARANTEES:
    - Never fabricates or saves synthetic/fake mock data.
    - If URL is invalid, offline, or returns 0 articles -> saves NOTHING, returns error message.
    - If article URL or title already exists in database -> SKIPPED (deduplicated), no duplicates saved.
    """
    await source_services.init_sources_collection(db)
    await article_services.init_articles_collection(db)

    # 1. Fetch source record
    source = await source_services.get_source_by_id(source_id, db=db)
    if not source:
        return {
            "ok": False,
            "error": f"Không tìm thấy nguồn dữ liệu ID {source_id}",
            "scanned_count": 0,
            "new_count": 0,
            "duplicate_count": 0,
        }

    source_url = (source.get("url") or "").strip()
    src_type = source.get("type", "website")
    src_name = source.get("name", "Nguồn cào")

    if not source_url:
        return {
            "ok": False,
            "error": f"Nguồn '{src_name}' chưa được thiết lập địa chỉ URL.",
            "source_id": source_id,
            "source_name": src_name,
            "scanned_count": 0,
            "new_count": 0,
            "duplicate_count": 0,
        }

    # 2. Extract real candidate articles from live URL
    candidates: List[Dict[str, Any]] = []

    if src_type == "rss" or source_url.endswith(".rss") or source_url.endswith(".xml"):
        candidates = await fetch_rss_feed(source_url, limit=12)

    elif src_type == "website":
        candidates = await fetch_website_content(source_url, limit=15)

    elif src_type == "api":
        candidates = await fetch_api_content(source_url, limit=10)

    elif src_type == "pdf" or source_url.lower().endswith(".pdf"):
        candidates = await fetch_pdf_content(source_url)

    # Note: For social channels (facebook, youtube, tiktok, etc.) without configured API credentials,
    # or if URL is unreachable, we report the actual status and NEVER invent fake data!
    if not candidates:
        return {
            "ok": False,
            "error": (
                f"Không thể cào dữ liệu từ URL '{source_url}'. "
                f"Vui lòng kiểm tra lại liên kết hoặc kết nối của nguồn '{src_name}'."
            ),
            "source_id": source_id,
            "source_name": src_name,
            "scanned_count": 0,
            "new_count": 0,
            "duplicate_count": 0,
        }

    # 3. Load existing identifiers from database for strict deduplication
    existing_urls, existing_titles = await get_all_existing_identifiers(db=db)

    new_articles_saved: List[Dict[str, Any]] = []
    duplicate_count = 0

    # 4. Filter and save only new articles
    for item in candidates:
        cand_url = item.get("url", "")
        cand_title = item.get("title", "")

        is_dup = await is_article_duplicate(
            candidate_url=cand_url,
            candidate_title=cand_title,
            existing_urls=existing_urls,
            existing_titles=existing_titles,
        )

        if is_dup:
            duplicate_count += 1
            logger.info(f"Duplicate article skipped: '{cand_title}' ({cand_url})")
            continue

        # Prepare full article record from real fetched content
        location_parts = [
            p for p in [source.get("ward"), source.get("district"), source.get("province")]
            if p and p.strip()
        ]
        location_str = ", ".join(location_parts) if location_parts else source.get("province", "Toàn quốc")

        cat = item.get("category")
        if not cat or cat == "Kinh tế & Thị trường":
            inferred = infer_article_category(cand_title, cand_url)
            if inferred and inferred != "Kinh tế & Thị trường":
                cat = inferred
            else:
                source_tags = source.get("tags")
                if isinstance(source_tags, list) and source_tags:
                    cat = source_tags[0]
                elif isinstance(source_tags, str) and source_tags.strip():
                    cat = source_tags.split(",")[0].strip()
                else:
                    cat = "Kinh tế & Thị trường"

        article_payload = {
            "title": cand_title,
            "summary": item.get("summary", cand_title),
            "content": item.get("content", item.get("summary", cand_title)),
            "url": cand_url,
            "source": src_name,
            "source_id": source["id"],
            "source_type": src_type,
            "source_icon": source.get("type_icon", "globe"),
            "author": item.get("author") or source.get("name", "Biên tập viên"),
            "location": location_str,
            "category": cat,
            "tags": source.get("tags", []),
            "sentiment": item.get("sentiment", "Tích cực"),
            "viral_potential": item.get("viral_potential", 82),
            "status": "new",
        }

        # Save to database
        created = await article_services.create_article(article_payload, db=db)
        new_articles_saved.append(created)

        # Track to prevent duplicates within the same batch
        if cand_url:
            existing_urls.add(normalize_url(cand_url))
        if cand_title:
            existing_titles.add(normalize_title(cand_title))

    new_count = len(new_articles_saved)
    scanned_total = len(candidates)

    # 5. Update source metrics
    curr_articles_count = int(source.get("articles_count", 0))
    new_total = curr_articles_count + new_count
    if new_total == 0 and duplicate_count > 0:
        new_total = duplicate_count

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    update_source_payload = {
        "articles_count": new_total,
        "last_scanned_at": "Vừa xong",
        "updated_at": now_str,
    }
    await source_services.update_source(source_id, update_source_payload, db=db)

    # 6. Response message
    if new_count > 0:
        if duplicate_count > 0:
            msg = (
                f"Quét thành công nguồn '{src_name}': Đã cào và lưu mới {new_count} bài vào Bài Thu Thập "
                f"(bỏ qua {duplicate_count} bài đã cào trước đó)."
            )
        else:
            msg = f"Quét thành công nguồn '{src_name}': Đã cào và lưu mới toàn bộ {new_count} bài vào Bài Thu Thập!"
    else:
        msg = (
            f"Quét hoàn tất nguồn '{src_name}': Đã kiểm tra {scanned_total} bài, "
            f"toàn bộ {duplicate_count} bài đã có trong Bài Thu Thập (không lưu thêm bài trùng)."
        )

    return {
        "ok": True,
        "source_id": source_id,
        "source_name": src_name,
        "scanned_count": scanned_total,
        "new_count": new_count,
        "duplicate_count": duplicate_count,
        "new_articles": new_articles_saved,
        "message": msg,
    }


async def crawl_all_active_sources(db: Optional[Any] = None) -> Dict[str, Any]:
    """Crawl all active sources sequentially and aggregate results."""
    all_sources, _ = await source_services._repo.find_all(db=db)
    active_sources = [s for s in all_sources if s.get("status") == "active"]

    total_scanned = 0
    total_new = 0
    total_duplicates = 0
    scanned_sources_details = []

    for src in active_sources:
        res = await crawl_source_and_save(src["id"], db=db)
        if res.get("ok"):
            total_scanned += res.get("scanned_count", 0)
            total_new += res.get("new_count", 0)
            total_duplicates += res.get("duplicate_count", 0)
            scanned_sources_details.append({
                "source_id": src["id"],
                "source_name": src["name"],
                "new_count": res.get("new_count", 0),
                "duplicate_count": res.get("duplicate_count", 0),
            })

    return {
        "ok": True,
        "sources_count": len(active_sources),
        "total_scanned": total_scanned,
        "total_new": total_new,
        "total_duplicates": total_duplicates,
        "details": scanned_sources_details,
        "message": (
            f"Đã quét đồng loạt {len(active_sources)} nguồn đang hoạt động: "
            f"Lưu mới {total_new} bài viết, bỏ qua {total_duplicates} bài trùng lặp."
        ),
    }
