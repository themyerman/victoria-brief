import yaml
from pathlib import Path


def load_config(path: str | Path = "feeds.yaml") -> tuple[dict, list, dict]:
    """
    Load feeds.yaml and return (feeds, stocks, web_search_queries).
    Looks for feeds.yaml next to main.py (repo root) by default.
    """
    with open(path) as f:
        cfg = yaml.safe_load(f)
    return (
        cfg.get("feeds", {}),
        cfg.get("stocks", []),
        cfg.get("web_search_queries", {}),
    )
