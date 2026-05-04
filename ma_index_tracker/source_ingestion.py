from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import quote, urlparse
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from ma_index_tracker.db.database import upsert_event_source

GDELT_DOC_URL = "https://api.gdeltproject.org/api/v2/doc/doc"
DEAL_TERMS = ("merger", "acquisition", "acquire", "deal")


@dataclass(frozen=True)
class SourceCandidate:
    title: str
    url: str
    publisher: str | None
    published_at: str | None
    source_type: str
    score: int
    date_distance_days: int


# Format company name for queries
def _clean_company_name(name: str | None) -> str | None:

    if not name:
        return None
    
    text = re.sub(r"\s+", " ", name).strip()
    return text or None


# Split name into individual words, clean unnecessary words
def _name_tokens(name: str | None) -> list[str]:

    if not name:
        return []
    
    ignore = {
        "the",
        "inc",
        "corp",
        "corporation",
        "company",
        "co",
        "ltd",
        "plc",
        "class",
        "group",
        "holdings",
    }

    return [
        token
        for token in re.findall(r"[a-z0-9]+", name.lower())
        if len(token) > 2 and token not in ignore
    ]


# Convert date from string to datetime
def _parse_iso_date(value: str | None) -> datetime | None:

    if not value:
        return None
    
    try:
        return datetime.fromisoformat(value[:10])
    except ValueError:
        return None


# Convert datetime to GDELT-compatible format
def _format_gdelt_datetime(dt: datetime) -> str:
    return dt.strftime("%Y%m%d%H%M%S")


# Convert GDELT-compatible format to iso
def _normalise_gdelt_date(value: str | None) -> str | None:

    if not value:
        return None

    text = str(value)
    for fmt in ("%Y%m%dT%H%M%SZ", "%Y%m%d%H%M%S", "%Y%m%d"):
        try:
            return datetime.strptime(text, fmt).isoformat()
        except ValueError:
            continue

    return text


# Build basic query for GDELT - contains tgt name, acq name, one of the deal terms
def build_source_query(target_name: str, acquirer_name: str | None = None) -> str:

    target = _clean_company_name(target_name)
    acquirer = _clean_company_name(acquirer_name)

    name_parts = [f'"{target}"'] if target else []

    if acquirer:
        name_parts.append(f'"{acquirer}"')

    deal_terms = "(" + " OR ".join(DEAL_TERMS) + ")"
    return " ".join([*name_parts, deal_terms]).strip()


# Fetch headline, link from GDELT
def fetch_gdelt_articles(
    query: str,
    *,
    announcement_date: str | None,
    max_records: int = 20,
    window_days: int = 14,
) -> list[dict[str, Any]]:
    
    params = [
        f"query={quote(query)}",
        "mode=ArtList",
        "format=json",
        f"maxrecords={max_records}",
        "sort=HybridRel", # rough relevance
    ]

    announcement_dt = _parse_iso_date(announcement_date)
    if announcement_dt is not None:
        start_dt = announcement_dt - timedelta(days=window_days)
        end_dt = announcement_dt + timedelta(days=window_days)
        params.append(f"startdatetime={_format_gdelt_datetime(start_dt)}")
        params.append(f"enddatetime={_format_gdelt_datetime(end_dt)}")

    url = f"{GDELT_DOC_URL}?{'&'.join(params)}"
    request = Request(url, headers={"User-Agent": "ma-index-tracker/0.1"})

    for attempt in range(3):
        try:
            with urlopen(request, timeout=30) as response:
                payload = json.loads(response.read().decode("utf-8"))
            break
        except HTTPError as exc:
            if exc.code != 429 or attempt == 2:
                raise
            retry_after = exc.headers.get("Retry-After")
            delay = int(retry_after) if retry_after and retry_after.isdigit() else 15 * (attempt + 1)
            time.sleep(delay)

    return payload.get("articles", [])


# Strip url to get domain
def _domain_from_url(url: str) -> str:

    parsed = urlparse(url)
    return parsed.netloc.lower().removeprefix("www.")


def _source_type(domain: str) -> str:
    if "sec.gov" in domain:
        return "filing"
    if any(d in domain for d in ("businesswire.com", "prnewswire.com", "globenewswire.com")):
        return "press_release"
    return "news"

# Calculate score for article based on key words and date distance
def _score_article(
    article: dict[str, Any],
    *,
    target_name: str,
    acquirer_name: str | None,
    announcement_date: str | None,
) -> tuple[int, int]:
    title = str(article.get("title") or "")
    title_lower = title.lower()
    domain = str(article.get("domain") or _domain_from_url(str(article.get("url") or ""))).lower()

    score = 0
    target_tokens = _name_tokens(target_name)
    acquirer_tokens = _name_tokens(acquirer_name)

    if target_tokens and any(token in title_lower for token in target_tokens):
        score += 3
    if acquirer_tokens and any(token in title_lower for token in acquirer_tokens):
        score += 3
    if any(term in title_lower for term in DEAL_TERMS):
        score += 2

    published_dt = _parse_iso_date(_normalise_gdelt_date(article.get("seendate")))
    announcement_dt = _parse_iso_date(announcement_date)
    date_distance = 9999
    if published_dt is not None and announcement_dt is not None:
        date_distance = abs((published_dt.date() - announcement_dt.date()).days)
        if date_distance <= 3:
            score += 2
        elif date_distance <= 14:
            score += 1

    return score, date_distance

# Remove duplicate articles, calculate scores, rank
def rank_articles(
    articles: list[dict[str, Any]],
    *,
    target_name: str,
    acquirer_name: str | None,
    announcement_date: str | None,
    top_n: int = 3,
) -> list[SourceCandidate]:
    
    seen_urls: set[str] = set()
    seen_titles: set[str] = set()
    candidates: list[SourceCandidate] = []

    for article in articles:
        url = str(article.get("url") or "").strip()
        title = str(article.get("title") or "").strip()
        title_key = re.sub(r"\s+", " ", title.lower()).strip()
        if not url or not title or url in seen_urls or title_key in seen_titles:
            continue

        seen_urls.add(url)
        seen_titles.add(title_key)
        domain = str(article.get("domain") or _domain_from_url(url)).lower()
        score, date_distance = _score_article(
            article,
            target_name=target_name,
            acquirer_name=acquirer_name,
            announcement_date=announcement_date,
        )

        candidates.append(
            SourceCandidate(
                title=title,
                url=url,
                publisher=domain or None,
                published_at=_normalise_gdelt_date(article.get("seendate")),
                source_type=_source_type(domain),
                score=score,
                date_distance_days=date_distance,
            )
        )

    candidates.sort(key=lambda c: (-c.score, c.date_distance_days, c.published_at or ""))
    return candidates[:top_n]


# Insert sources into DB
def insert_sources(
    conn,
    event_id: int,
    *,
    max_records: int = 20,
    top_n: int = 3,
) -> list[SourceCandidate]:
    
    row = conn.execute(
        """
        SELECT
            e.announcement_date,
            target.name AS target_name,
            acquirer.name AS acquirer_name
        FROM mna_events e
        JOIN companies target
            ON e.target_company_id = target.id
        LEFT JOIN companies acquirer
            ON e.acquirer_company_id = acquirer.id
        WHERE e.id = ?
        """,
        (event_id,),
    ).fetchone()
    if row is None:
        raise ValueError(f"No event found for event_id={event_id}")

    query = build_source_query(row["target_name"], row["acquirer_name"])
    articles = fetch_gdelt_articles(
        query,
        announcement_date=row["announcement_date"],
        max_records=max_records,
    )
    sources = rank_articles(
        articles,
        target_name=row["target_name"],
        acquirer_name=row["acquirer_name"],
        announcement_date=row["announcement_date"],
        top_n=top_n,
    )

    conn.execute("DELETE FROM event_sources WHERE event_id = ?", (event_id,))
    for rank, source in enumerate(sources, start=1):
        upsert_event_source(
            conn,
            event_id=event_id,
            rank=rank,
            title=source.title,
            url=source.url,
            publisher=source.publisher,
            published_at=source.published_at,
            source_type=source.source_type,
        )

    return sources


def get_pending_event_ids(conn) -> list[int]:

    rows = conn.execute(
        """
        SELECT id
        FROM mna_events
        WHERE status = 'Pending'
        ORDER BY id
        """
    ).fetchall()
    
    return [int(row["id"]) for row in rows]
