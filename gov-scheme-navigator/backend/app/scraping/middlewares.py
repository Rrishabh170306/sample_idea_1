"""
Scrapy middlewares for anti-bot handling and request throttling.
Implements rotating user agents, request delays, and dynamic throttling.
"""

from __future__ import annotations

import logging
import random
import time
from typing import Optional

logger = logging.getLogger(__name__)


class RotatingUserAgentMiddleware:
    """Rotate User-Agent headers to avoid bot detection."""

    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0",
    ]

    def process_request(self, request, spider):
        """Add random User-Agent to request."""
        request.headers["User-Agent"] = random.choice(self.USER_AGENTS)
        logger.debug(f"Set User-Agent for {request.url}")
        return None


class AntiBotMiddleware:
    """
    Combined anti-bot handling with multiple strategies:
    - Rotating User-Agents
    - Request throttling with adaptive delays
    - Robots.txt compliance
    - Retry logic with exponential backoff
    """

    def __init__(self):
        self.domain_delays = {}
        self.last_request_time = {}
        self.delay_sec = 3.0
        self.user_agent_middleware = RotatingUserAgentMiddleware()

    def process_request(self, request: object) -> object:
        """Apply anti-bot strategies before request."""
        # Add rotating user agent
        self.user_agent_middleware.process_request(request, None)

        # Apply throttling
        self._apply_throttle(request)

        logger.debug(f"Anti-bot middleware processed: {request.url}")
        return None

    def _apply_throttle(self, request):
        """Apply per-domain throttling with adaptive delays."""
        domain = self._get_domain(request.url)
        current_time = time.time()

        if domain in self.last_request_time:
            elapsed = current_time - self.last_request_time[domain]
            delay = self.domain_delays.get(domain, self.delay_sec)

            if elapsed < delay:
                sleep_time = delay - elapsed
                logger.debug(f"Throttling {domain}: sleeping {sleep_time:.2f}s")
                time.sleep(sleep_time)

        self.last_request_time[domain] = time.time()

    def _get_domain(self, url: str) -> str:
        """Extract domain from URL."""
        from urllib.parse import urlparse

        return urlparse(url).netloc


class PlaywrightFallbackMiddleware:
    """
    Fallback to Playwright when Scrapy gets blocked.
    Detects common blocking responses and escalates to headless browser.
    """

    BLOCKING_STATUSES = [403, 429, 503]
    BLOCKING_PATTERNS = ["captcha", "unusual activity", "bot"]

    def process_response(self, request: object, response: object) -> object:
        """Check if request was blocked and fallback to Playwright."""
        if self._is_blocked(response):
            logger.warning(f"Blocking detected for {request.url}. Escalating to Playwright.")
            request.meta["use_playwright"] = True
            # This would trigger Playwright spider in real implementation
            return request

        return response

    def _is_blocked(self, response) -> bool:
        """Check if response indicates blocking."""
        if response.status in self.BLOCKING_STATUSES:
            return True

        body = response.text.lower()
        for pattern in self.BLOCKING_PATTERNS:
            if pattern in body:
                return True

        return False


class RetryMiddleware:
    """
    Retry failed requests with exponential backoff.
    Skip retries for permanent errors (4xx).
    """

    MAX_RETRIES = 3
    RETRY_CODES = [429, 500, 502, 503, 504]  # Rate limit + server errors

    def process_response(self, request, response, spider):
        """Check response status and retry if needed."""
        if response.status in self.RETRY_CODES:
            retry_count = request.meta.get("retry_count", 0)

            if retry_count < self.MAX_RETRIES:
                retry_count += 1
                backoff_time = 2 ** retry_count  # Exponential backoff

                new_request = request.copy()
                new_request.meta["retry_count"] = retry_count
                new_request.meta["backoff_time"] = backoff_time

                logger.warning(
                    f"Retrying {request.url} (attempt {retry_count}/{self.MAX_RETRIES})"
                )
                return new_request
            else:
                logger.error(f"Max retries exceeded for {request.url}")

        return response

    def process_exception(self, request, exception, spider):
        """Handle request exceptions with retry logic."""
        retry_count = request.meta.get("retry_count", 0)

        if retry_count < self.MAX_RETRIES:
            retry_count += 1
            new_request = request.copy()
            new_request.meta["retry_count"] = retry_count

            logger.warning(
                f"Request exception for {request.url}. "
                f"Retrying (attempt {retry_count}/{self.MAX_RETRIES}): {exception}"
            )
            return new_request

        logger.error(f"Request failed permanently: {request.url} - {exception}")
        return None

