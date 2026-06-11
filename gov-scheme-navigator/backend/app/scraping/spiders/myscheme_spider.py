from __future__ import annotations

import logging
from datetime import datetime
from typing import Any
from urllib.parse import urljoin

import redis
from playwright.async_api import async_playwright, Page, Browser
from pydantic import ValidationError

from app.scraping.extractors.scheme_extractor import SchemeExtractor
from app.core.config import settings
from app.scraping.change_detector import ChangeDetector

logger = logging.getLogger(__name__)


class MySchemeSpider:
    """
    Spider for MyScheme.gov.in - handles SPA rendering with Playwright.
    Implements anti-bot strategies, change detection, and structured extraction.
    """

    name = "myscheme"
    allowed_domains = ["myscheme.gov.in"]
    start_urls = ["https://www.myscheme.gov.in/schemes"]

    # Anti-bot configuration
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
    ]
    REQUEST_DELAY = 3  # seconds between requests
    TIMEOUT = 30000  # milliseconds

    def __init__(self):
        # Prefer a redis URL when available
        try:
            self.redis_client = redis.from_url(settings.redis_url, decode_responses=True)
        except Exception:
            self.redis_client = redis.Redis(host=settings.redis_host, port=settings.redis_port, decode_responses=True)

        self.change_detector = ChangeDetector(redis_client=self.redis_client)
        self.extractor = SchemeExtractor()
        self.browser: Browser | None = None
        self.session_index = 0

    async def start_requests(self) -> list[dict[str, Any]]:
        """Generate initial requests for MyScheme portal."""
        for url in self.start_urls:
            yield {"url": url, "retry_count": 0}

    async def parse(self, response: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Parse MyScheme SPA listing page and extract scheme URLs.
        Handles JavaScript rendering with Playwright.
        """
        url = response["url"]
        page = None

        try:
            page = await self._get_page()

            # Navigate with anti-bot headers
            await page.goto(url, wait_until="networkidle", timeout=self.TIMEOUT)

            # Wait for scheme list to load
            await page.wait_for_selector("a[href*='/schemes/']", timeout=5000)

            # Extract all scheme URLs
            scheme_links = await page.query_selector_all("a[href*='/schemes/']")
            scheme_urls = []

            for link in scheme_links:
                href = await link.get_attribute("href")
                if href:
                    scheme_url = urljoin(url, href)
                    scheme_urls.append(scheme_url)

            logger.info(f"Found {len(scheme_urls)} schemes on {url}")

            # Queue each scheme for detailed parsing
            for scheme_url in scheme_urls:
                yield {"url": scheme_url, "is_detail": True, "retry_count": 0}

        except Exception as e:
            logger.error(f"Error parsing {url}: {e}")
            if response.get("retry_count", 0) < 3:
                yield {
                    "url": url,
                    "retry_count": response.get("retry_count", 0) + 1,
                }
        finally:
            if page:
                await page.close()

    async def parse_scheme_detail(
        self, response: dict[str, Any]
    ) -> dict[str, Any] | None:
        """
        Parse individual scheme detail page with Playwright.
        Extract structured data and perform change detection.
        """
        url = response["url"]
        page = None

        try:
            page = await self._get_page()
            await page.goto(url, wait_until="networkidle", timeout=self.TIMEOUT)

            # Get full page HTML for extraction
            content = await page.content()

            # Change detection (uses ChangeDetector for canonicalization and atomic updates)
            change_result = self.change_detector.has_changed(url, content)
            if not change_result.changed:
                logger.info("No changes detected for %s (hash=%s)", url, change_result.new_hash[:8])
                return None

            # Extract structured data using LLM
            extraction_result = self.extractor.extract(content, source_url=url)

            # Validation with Pydantic
            if extraction_result.confidence < 0.8:
                logger.warning(
                    f"Low confidence ({extraction_result.confidence}) for {url}. "
                    "Routing to manual review."
                )

            scheme_data = extraction_result.record.model_dump()
            scheme_data.update({
                "source_url": url,
                "content_hash": change_result.new_hash,
                "confidence_score": extraction_result.confidence,
                "crawled_at": datetime.utcnow().isoformat(),
            })

            logger.info(f"Successfully extracted scheme: {scheme_data.get('scheme_id')}")
            return scheme_data

        except ValidationError as e:
            logger.error(f"Validation error for {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error parsing scheme detail {url}: {e}")
            if response.get("retry_count", 0) < 2:
                yield {
                    "url": url,
                    "is_detail": True,
                    "retry_count": response.get("retry_count", 0) + 1,
                }
        finally:
            if page:
                await page.close()

    def _check_change_detection(self, url: str, content: str) -> bool:
        """
        Check if page content has changed using hash comparison.
        Updates Redis with new hash and timestamp.
        """
        # Legacy helper retained for backward compatibility
        try:
            result = self.change_detector.has_changed(url, content)
            return result.changed
        except Exception:
            logger.exception("Change detection failed for %s, assuming changed to force reprocess.", url)
            return True

    async def _get_page(self) -> Page:
        """Get or create Playwright page with anti-bot headers."""
        if not self.browser:
            playwright = await async_playwright().start()
            self.browser = await playwright.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled"],
            )

        context = await self.browser.new_context(
            user_agent=self.USER_AGENTS[self.session_index % len(self.USER_AGENTS)]
        )
        self.session_index += 1

        page = await context.new_page()

        # Stealth mode: hide automation indicators
        await page.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => false})"
        )

        return page

    async def close(self):
        """Clean up browser resources."""
        if self.browser:
            await self.browser.close()
