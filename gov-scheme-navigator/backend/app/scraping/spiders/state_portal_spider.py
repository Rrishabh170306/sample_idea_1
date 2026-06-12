"""Spider for India.gov.in state-level government scheme portals.

Scrapes:
 - https://www.india.gov.in/my-government/schemes  (central schemes index)
 - State-specific scheme portals (Tamil Nadu, Maharashtra, UP, etc.)

Falls back to httpx when Playwright is unavailable.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx

from app.scraping.change_detector import ChangeDetector
from app.scraping.extractors.scheme_extractor import SchemeExtractor

logger = logging.getLogger(__name__)

# Target portals — government scheme listing pages
STATE_PORTAL_URLS: list[dict[str, str]] = [
    {
        "url": "https://www.india.gov.in/my-government/schemes",
        "name": "India.gov.in Central Schemes",
        "state": "Central",
    },
    {
        "url": "https://www.myscheme.gov.in/search?category=Agriculture",
        "name": "MyScheme Agriculture",
        "state": "Central",
    },
    {
        "url": "https://tnagrisnet.tn.gov.in/",
        "name": "Tamil Nadu Agriculture",
        "state": "Tamil Nadu",
    },
]

# Known scheme detail URLs that can be scraped directly
KNOWN_SCHEME_URLS: list[dict[str, str]] = [
    {
        "url": "https://pmkisan.gov.in/",
        "name": "PM-KISAN",
        "state": "Central",
    },
    {
        "url": "https://pmfby.gov.in/",
        "name": "PM Fasal Bima Yojana",
        "state": "Central",
    },
    {
        "url": "https://www.india.gov.in/spotlight/kisan-credit-card",
        "name": "Kisan Credit Card",
        "state": "Central",
    },
]


class StatePortalSpider:
    """Spider for state government scheme portals.

    Uses Playwright for JS-rendered pages, falls back to httpx for static content.
    Implements robots.txt compliance, rate limiting, and change detection.
    """

    name = "state_portal"
    allowed_domains = [
        "india.gov.in",
        "myscheme.gov.in",
        "tnagrisnet.tn.gov.in",
        "pmkisan.gov.in",
        "pmfby.gov.in",
    ]
    start_urls = [entry["url"] for entry in KNOWN_SCHEME_URLS]

    REQUEST_DELAY = 2  # seconds between requests
    TIMEOUT = 30.0  # seconds

    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    ]

    def __init__(self):
        self.change_detector = ChangeDetector()
        self.extractor = SchemeExtractor()
        self._session_index = 0

    def _get_headers(self) -> dict[str, str]:
        ua = self.USER_AGENTS[self._session_index % len(self.USER_AGENTS)]
        self._session_index += 1
        return {
            "User-Agent": ua,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-IN,en;q=0.9,hi;q=0.8",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
        }

    async def _check_robots(self, url: str) -> bool:
        """Return True if the URL is allowed by robots.txt."""
        try:
            parsed = urlparse(url)
            robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(robots_url)
                if resp.status_code != 200:
                    return True  # No robots.txt — assume allowed
                # Simple check: if "Disallow: /" appears, skip; otherwise allow
                text = resp.text.lower()
                path = parsed.path.lower()
                for line in text.splitlines():
                    if line.startswith("disallow:"):
                        disallowed = line.split(":", 1)[1].strip()
                        if disallowed and path.startswith(disallowed):
                            logger.info("Robots.txt disallows %s", url)
                            return False
                return True
        except Exception:
            return True  # On error, assume allowed

    async def fetch_url(self, url: str) -> str:
        """Fetch page content, trying Playwright first then httpx."""
        # Try Playwright
        try:
            from playwright.async_api import async_playwright

            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=["--no-sandbox", "--disable-setuid-sandbox",
                          "--disable-blink-features=AutomationControlled"],
                )
                ctx = await browser.new_context(user_agent=self._get_headers()["User-Agent"])
                page = await ctx.new_page()
                await page.goto(url, wait_until="domcontentloaded",
                                timeout=int(self.TIMEOUT * 1000))
                await asyncio.sleep(1)
                content = await page.content()
                await browser.close()
                return content
        except Exception:
            logger.debug("Playwright unavailable for %s, using httpx", url)

        # httpx fallback
        async with httpx.AsyncClient(
            headers=self._get_headers(),
            timeout=self.TIMEOUT,
            follow_redirects=True,
        ) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.text

    async def scrape_url(self, url: str) -> dict[str, Any] | None:
        """Scrape a single URL, returning extracted scheme data or None."""
        # Robots check
        if not await self._check_robots(url):
            logger.info("Skipping %s (robots.txt)", url)
            return None

        try:
            content = await self.fetch_url(url)
        except Exception as exc:
            logger.error("Failed to fetch %s: %s", url, exc)
            return None

        # Change detection
        change = await self.change_detector.has_changed(url, content)
        if not change.changed:
            logger.info("No change detected for %s — skipping", url)
            return None

        # LLM extraction
        try:
            extraction = self.extractor.extract(content, source_url=url)
        except Exception as exc:
            logger.error("Extraction failed for %s: %s", url, exc)
            return None

        scheme = extraction.record.model_dump()
        scheme.update({
            "source_url": url,
            "content_hash": change.new_hash,
            "confidence_score": extraction.confidence,
            "crawled_at": datetime.utcnow().isoformat(),
        })
        if not scheme.get("official_url"):
            scheme["official_url"] = url

        logger.info(
            "Scraped %s → scheme_id=%s (confidence=%.2f)",
            url,
            scheme.get("scheme_id"),
            extraction.confidence,
        )
        return scheme

    async def run(self, urls: list[str] | None = None) -> list[dict[str, Any]]:
        """Run spider against list of URLs, with rate limiting."""
        target_urls = urls or self.start_urls
        results: list[dict[str, Any]] = []

        for i, url in enumerate(target_urls):
            logger.info("Scraping [%d/%d] %s", i + 1, len(target_urls), url)
            result = await self.scrape_url(url)
            if result:
                results.append(result)
            # Rate limit
            if i < len(target_urls) - 1:
                await asyncio.sleep(self.REQUEST_DELAY)

        logger.info("StatePortalSpider complete: %d/%d URLs yielded data",
                    len(results), len(target_urls))
        return results
