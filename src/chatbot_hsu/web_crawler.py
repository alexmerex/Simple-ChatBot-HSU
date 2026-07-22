from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup


@dataclass(slots=True)
class CrawledPage:
    url: str
    title: str
    text: str


def _normalize_url(url: str) -> str:
    parsed = urlparse(url)
    path = parsed.path or "/"
    cleaned = parsed._replace(
        scheme=parsed.scheme.lower(),
        netloc=parsed.netloc.lower(),
        path=path,
        fragment="",
    )
    return urlunparse(cleaned)


def _is_allowed_url(url: str, allowed_domains: tuple[str, ...]) -> bool:
    try:
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
    except ValueError:
        return False

    if parsed.scheme not in {"http", "https"} or not host:
        return False

    return any(host == domain or host.endswith(f".{domain}") for domain in allowed_domains)


def _extract_text(soup: BeautifulSoup) -> str:
    parts: list[str] = []
    for tag in soup.select("h1,h2,h3,h4,p,li"):
        text = tag.get_text(" ", strip=True)
        if text:
            parts.append(text)
    return "\n".join(parts)


def crawl_website(
    seed_urls: list[str],
    allowed_domains: tuple[str, ...],
    max_pages: int,
    timeout_seconds: int,
) -> list[CrawledPage]:
    visited: set[str] = set()
    queue: deque[str] = deque(_normalize_url(url) for url in seed_urls)
    pages: list[CrawledPage] = []
    requests_attempted = 0
    max_requests = max_pages * 5

    allowed_domains = tuple(domain.lower().lstrip(".") for domain in allowed_domains)
    with requests.Session() as session:
        session.headers.update({"User-Agent": "HSUChatBot/1.0 (+educational crawler)"})

        while queue and len(pages) < max_pages and requests_attempted < max_requests:
            url = queue.popleft()
            if url in visited:
                continue
            visited.add(url)

            if not _is_allowed_url(url, allowed_domains):
                continue

            requests_attempted += 1
            try:
                response = session.get(url, timeout=timeout_seconds)
                if response.status_code != 200:
                    continue
                content_type = response.headers.get("Content-Type", "").lower()
                if "text/html" not in content_type:
                    continue
            except requests.RequestException:
                continue

            soup = BeautifulSoup(response.text, "html.parser")
            for unwanted in soup.select("script,style,noscript,svg"):
                unwanted.decompose()
            title = soup.title.get_text(" ", strip=True) if soup.title else url
            text = _extract_text(soup)
            if text:
                pages.append(CrawledPage(url=url, title=title, text=text))

            for anchor in soup.select("a[href]"):
                href = anchor.get("href", "").strip()
                if not href:
                    continue
                absolute = _normalize_url(urljoin(url, href))
                if absolute not in visited and _is_allowed_url(absolute, allowed_domains):
                    queue.append(absolute)

    return pages
