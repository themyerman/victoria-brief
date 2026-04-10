from typing import Union
import yaml
from pathlib import Path


def load_config(path: "Union[str, Path]" = "feeds.yaml") -> "tuple[dict, list, dict]":
    """
    Load feeds.yaml and return (feeds, stocks, web_search_queries).
    Looks for feeds.yaml next to main.py (repo root) by default.
    """
    with open(path) as f:
        cfg = yaml.safe_load(f)
    sources = cfg.get("sources", [])
    categories = {s["name"]: s.get("category", "Other") for s in sources}
    return (
        sources,
        cfg.get("notify", []),
        {"categories": categories},
    )
