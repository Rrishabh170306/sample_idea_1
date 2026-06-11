from __future__ import annotations


class StatePortalSpider:
    name = "state_portal"
    allowed_domains = ["example.gov.in"]
    start_urls = ["https://example.gov.in/schemes"]

    def parse(self, response: object) -> list[dict[str, object]]:
        raise NotImplementedError("State portal crawl logic will be implemented here.")
