from __future__ import annotations


class AntiBotMiddleware:
    def process_request(self, request: object) -> object:
        raise NotImplementedError("Request throttling and anti-bot logic will live here.")


class PlaywrightFallbackMiddleware:
    def process_response(self, request: object, response: object) -> object:
        raise NotImplementedError("Playwright fallback handling will live here.")
