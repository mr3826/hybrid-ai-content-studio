import asyncio
import email.utils
import hashlib
import html
import re
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Set

import httpx

from app.engines.rss.contracts import ParsedFeedItem

TRACKING_PARAMS: Set[str] = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "utm_id",
    "utm_name",
    "fbclid",
    "gclid",
    "mc_eid",
    "mc_cid",
    "ref",
    "ref_src",
    "source",
    "si",
    "spm",
    "_hsenc",
    "_hsmi",
    "feature",
}


def canonicalize_url(url: str) -> str:
    """Strip marketing tracking parameters, anchors, and normalize host and scheme."""
    if not url:
        return ""
    try:
        parsed = urllib.parse.urlsplit(url.strip())
        scheme = parsed.scheme.lower() if parsed.scheme else "https"
        netloc = parsed.netloc.lower()
        # Drop default ports
        if netloc.endswith(":80") and scheme == "http":
            netloc = netloc[:-3]
        elif netloc.endswith(":443") and scheme == "https":
            netloc = netloc[:-4]

        # Filter out tracking query parameters
        query_pairs = urllib.parse.parse_qsl(parsed.query, keep_blank_values=False)
        clean_query = [
            (k, v) for k, v in query_pairs if k.lower() not in TRACKING_PARAMS
        ]
        clean_query.sort(key=lambda x: x[0])
        new_query = urllib.parse.urlencode(clean_query)

        # Normalize path
        path = parsed.path
        if path.endswith("/") and len(path) > 1:
            path = path[:-1]

        # Discard fragments/anchors (#)
        return urllib.parse.urlunsplit((scheme, netloc, path, new_query, ""))
    except Exception:
        return url.strip()


def normalize_title(title: str) -> str:
    """Normalize title for exact and near-duplicate matching."""
    if not title:
        return ""
    # Unescape HTML entities
    unescaped = html.unescape(title)
    # Strip HTML tags
    cleaned = re.sub(r"<[^>]+>", " ", unescaped)
    # Lowercase
    lowered = cleaned.lower()
    # Replace non-alphanumeric chars with spaces
    alphanumeric = re.sub(r"[^a-z0-9\s]", " ", lowered)
    # Normalize whitespaces
    return " ".join(alphanumeric.split())


STOPWORDS: Set[str] = {
    "a", "an", "the", "and", "or", "in", "on", "at", "to", "for", "with",
    "by", "of", "from", "as", "is", "are", "was", "were", "it", "its",
    "has", "have", "had", "this", "that", "these", "those",
}


def calculate_title_similarity(t1: str, t2: str) -> float:
    """Compute hybrid token similarity between two titles using content tokens."""
    norm1 = normalize_title(t1)
    norm2 = normalize_title(t2)
    if not norm1 or not norm2:
        return 1.0 if norm1 == norm2 else 0.0
    if norm1 == norm2:
        return 1.0

    all_tokens1 = norm1.split()
    all_tokens2 = norm2.split()

    # Filter stopwords to focus on core content words
    tokens1 = {w for w in all_tokens1 if w not in STOPWORDS}
    tokens2 = {w for w in all_tokens2 if w not in STOPWORDS}

    if not tokens1 or not tokens2:
        tokens1 = set(all_tokens1)
        tokens2 = set(all_tokens2)

    union = tokens1 | tokens2
    intersection = tokens1 & tokens2
    if not union or not intersection:
        return 0.0

    jaccard = len(intersection) / len(union)
    containment = len(intersection) / min(len(tokens1), len(tokens2))

    return max(jaccard, containment)


def calculate_fingerprint(title: str, summary: str) -> str:
    """Generate SHA-256 content fingerprint for title and summary."""
    norm_t = normalize_title(title)
    norm_s = normalize_title(summary[:500])
    raw = f"{norm_t}::{norm_s}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _get_elem_text(elem: Optional[ET.Element]) -> str:
    """Extract full textual content from an ElementTree element and all its children."""
    if elem is None:
        return ""
    full_text = "".join(elem.itertext())
    unescaped = html.unescape(full_text)
    clean = re.sub(r"<[^>]+>", " ", unescaped)
    return " ".join(clean.split())


def _find_elem(parent: ET.Element, *tags: str) -> Optional[ET.Element]:
    """Find the first matching child element among tag candidates without boolean testing."""
    for tag in tags:
        found = parent.find(tag)
        if found is not None:
            return found
    return None


def _parse_datetime(date_str: Optional[str]) -> datetime:
    """Parse RFC 2822 or ISO 8601 timestamps with fallback to UTC now."""
    if not date_str:
        return datetime.now(timezone.utc)
    date_str = date_str.strip()

    # Try RFC 2822 (standard for RSS <pubDate>)
    try:
        dt = email.utils.parsedate_to_datetime(date_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        pass

    # Try ISO 8601 (standard for Atom <published> / <updated>)
    try:
        iso_str = date_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(iso_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        pass

    return datetime.now(timezone.utc)


def parse_feed_xml(
    xml_content: str,
    feed_source_name: str,
    feed_id: Optional[str] = None,
    default_trust: float = 0.8,
) -> List[ParsedFeedItem]:
    """Parse RSS 2.0 or Atom XML content into a list of ParsedFeedItem objects."""
    items: List[ParsedFeedItem] = []
    if not xml_content or not xml_content.strip():
        return items

    try:
        root = ET.fromstring(xml_content)
    except Exception as exc:
        raise ValueError(f"XML parse error in feed '{feed_source_name}': {exc}") from exc

    tag = root.tag.lower()

    # 1. Atom feed (<feed ...>)
    if "feed" in tag:
        entries = root.findall(".//{*}entry")
        if not entries:
            entries = root.findall("entry")

        for entry in entries:
            title_elem = _find_elem(entry, "{*}title", "title")
            title = _get_elem_text(title_elem)

            # Link in Atom: <link rel="alternate" href="..." /> or <link href="..." />
            link = ""
            link_candidates = entry.findall("{*}link") or entry.findall("link")
            for l_elem in link_candidates:
                rel = l_elem.attrib.get("rel", "alternate")
                if rel in ("alternate", "") and "href" in l_elem.attrib:
                    link = l_elem.attrib["href"]
                    break
                elif "href" in l_elem.attrib and not link:
                    link = l_elem.attrib["href"]

            if not link:
                id_elem = _find_elem(entry, "{*}id", "id")
                if id_elem is not None:
                    id_text = _get_elem_text(id_elem)
                    if id_text.startswith("http"):
                        link = id_text

            # Summary / Content
            summary_elem = _find_elem(entry, "{*}summary", "summary", "{*}content", "content")
            summary = _get_elem_text(summary_elem)

            # Date: <published> or <updated>
            date_elem = _find_elem(entry, "{*}published", "published", "{*}updated", "updated")
            date_str = _get_elem_text(date_elem) if date_elem is not None else None
            pub_date = _parse_datetime(date_str)

            id_elem = _find_elem(entry, "{*}id", "id")
            guid = _get_elem_text(id_elem) if id_elem is not None else link

            if title or link:
                items.append(
                    ParsedFeedItem(
                        title=title or "Untitled Atom Entry",
                        link=link,
                        summary=summary,
                        published_at=pub_date,
                        guid=guid,
                        feed_id=feed_id,
                        feed_name=feed_source_name,
                        trust_weight=default_trust,
                    )
                )

    # 2. RSS 0.9x / 2.0 / RDF (<rss> or <rdf:RDF>)
    else:
        for item in root.findall(".//item"):
            title_elem = _find_elem(item, "title", "{*}title")
            title = _get_elem_text(title_elem)

            link_elem = _find_elem(item, "link", "{*}link")
            link = _get_elem_text(link_elem)

            guid_elem = _find_elem(item, "guid", "{*}guid")
            guid = _get_elem_text(guid_elem) if guid_elem is not None else link
            if not link and guid and guid.startswith("http"):
                link = guid

            desc_elem = _find_elem(item, "description", "{*}description", "{*}encoded")
            summary = _get_elem_text(desc_elem)

            date_elem = _find_elem(item, "pubDate", "{*}pubDate", "{*}date")
            date_str = _get_elem_text(date_elem) if date_elem is not None else None
            pub_date = _parse_datetime(date_str)

            if title or link:
                items.append(
                    ParsedFeedItem(
                        title=title or "Untitled RSS Item",
                        link=link,
                        summary=summary,
                        published_at=pub_date,
                        guid=guid,
                        feed_id=feed_id,
                        feed_name=feed_source_name,
                        trust_weight=default_trust,
                    )
                )

    return items


async def fetch_feed_resilient(
    url: str,
    timeout: float = 10.0,
    max_retries: int = 3,
    backoff_factor: float = 1.5,
) -> Tuple[bool, Optional[str], Optional[str]]:
    """Fetch feed with custom user-agent, timeouts, and bounded retries.
    Returns (success, xml_content, error_message).
    """
    headers = {
        "User-Agent": "FreshLocalStudio/1.0 (+http://localhost:8400; Content Discovery Engine)",
        "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml;q=0.9, */*;q=0.8",
    }
    last_err: Optional[str] = None

    for attempt in range(1, max_retries + 1):
        try:
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
                response = await client.get(url, headers=headers)
                if response.status_code == 200:
                    return True, response.text, None
                else:
                    last_err = f"HTTP {response.status_code}: {response.reason_phrase}"
        except httpx.TimeoutException:
            last_err = f"Connection timed out after {timeout}s"
        except httpx.RequestError as exc:
            last_err = f"Network error: {str(exc)}"
        except Exception as exc:
            last_err = f"Unexpected fetch error: {str(exc)}"

        if attempt < max_retries:
            await asyncio.sleep(0.3 * (backoff_factor ** (attempt - 1)))

    return False, None, last_err
