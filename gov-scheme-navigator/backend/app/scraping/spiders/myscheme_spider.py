from __future__ import annotations


class MySchemeSpider:
    name = "myscheme"
    allowed_domains = ["myscheme.gov.in"]
    start_urls = ["https://www.myscheme.gov.in/schemes"]

    def parse(self, response: object) -> list[dict[str, object]]:
        raise NotImplementedError("MyScheme crawl logic will be implemented here.")
