from data.adapters.api_adapter import APIAdapter
from data.adapters.base import DataAdapter
from data.adapters.file_adapters import CSVAdapter, ExcelAdapter
from data.adapters.live_market import LiveMarketAdapter
from data.adapters.synthetic_adapter import SyntheticAdapter


def get_adapter(mode: str, **kwargs) -> DataAdapter:
    registry = {
        "synthetic": SyntheticAdapter,
        "live": LiveMarketAdapter,
        "csv": CSVAdapter,
        "excel": ExcelAdapter,
        "api": APIAdapter,
    }
    if mode not in registry:
        raise ValueError(f"Unknown data_source_mode '{mode}'. Choose from {list(registry)}.")
    return registry[mode](**kwargs)


__all__ = [
    "DataAdapter", "SyntheticAdapter", "LiveMarketAdapter", "CSVAdapter", "ExcelAdapter",
    "APIAdapter", "get_adapter",
]
