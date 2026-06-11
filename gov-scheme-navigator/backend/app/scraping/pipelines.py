from __future__ import annotations


class NormalizeItemPipeline:
    def process_item(self, item: dict[str, object]) -> dict[str, object]:
        raise NotImplementedError("Normalization and storage will be implemented here.")


class StoragePipeline:
    def process_item(self, item: dict[str, object]) -> dict[str, object]:
        raise NotImplementedError("Persistence will be implemented here.")
