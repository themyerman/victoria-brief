from __future__ import annotations

"""
NLP utilities: deduplication, scoring, major story detection, summarization, sentiment.
Uses NLTK + scikit-learn. NLTK data (~3MB) is auto-downloaded on first run.
"""

import sys
import nltk


def _ensure_nltk_data() -> None:
    needed = [
        ("sentiment/vader_lexicon.zip", "vader_lexicon"),
        ("corpora/stopwords.zip",        "stopwords"),
        ("tokenizers/punkt_tab.zip",     "punkt_tab"),
    ]
    for path, pkg in needed:
        try:
            nltk.data.find(path)
        except LookupError:
            print(f"  [nltk] Downloading {pkg}...", file=sys.stderr)
            nltk.download(pkg, quiet=True)


# ---------------------------------------------------------------------------
# Local relevance scoring
# ---------------------------------------------------------------------------

_LOCAL_TERMS = {
    "victoria", "saanich", "esquimalt", "langford", "colwood", "sooke",
    "sidney", "oak bay", "nanaimo", "comox", "courtenay",
    "campbell river", "port alberni", "tofino", "ucluelet",
    "vancouver island", "island", "bc", "british columbia",
    "songhees", "wsanec", "lekwungen", "first nations", "indigenous",
    "fnlc", "treaty", "reconciliation", "uvic", "camosun", "bc ferries",
}

def _local_score(item: dict) -> float:
    text = (item.get("title", "") + " " + item.get("summary", "")).lower()
    hits = sum(1 for term in _LOCAL_TERMS if term in text)
    return min(hits / 3.0, 1.0)  # cap at 1.0


def _recency_score(item: dict) -> float:
    """1.0 = just published, 0.0 = 26h ago. None published = 0.5."""
    pub = item.get("published")
    if pub is None:
        return 0.5
    from datetime import datetime, timezone
    pub_dt = datetime(*pub[:6], tzinfo=timezone.utc)
    from datetime import timedelta
    age_hours = (datetime.now(timezone.utc) - pub_dt).total_seconds() / 3600
    return max(0.0, 1.0 - age_hours / 26.0)


def _vader_magnitude(item: dict) -> float:
    """Strong sentiment (either direction) = more newsworthy than flat wire copy."""
    _ensure_nltk_data()
    from nltk.sentiment.vader import SentimentIntensityAnalyzer
    sia = SentimentIntensityAnalyzer()
    text = item.get("title", "") + ". " + item.get("summary", "")
    return abs(sia.polarity_scores(text)["compound"])


def score_items(items: list[dict], drop_zero_local: bool = False) -> list[dict]:
    """
    Score and sort items by composite heuristic:
      0.4 * recency + 0.4 * local_relevance + 0.2 * vader_magnitude
    Returns items sorted descending by score, with '_score' attached.
    If drop_zero_local=True, items with no local relevance signal are removed.
    """
    scored = []
    for item in items:
        local = _local_score(item)
        if drop_zero_local and local == 0.0:
            continue
        s = (0.4 * _recency_score(item) +
             0.4 * local +
             0.2 * _vader_magnitude(item))
        scored.append(dict(item, _score=round(s, 4)))
    return sorted(scored, key=lambda x: x["_score"], reverse=True)


# ---------------------------------------------------------------------------
# Cross-source major story detection
# ---------------------------------------------------------------------------

def find_major_stories(
    sources: dict[str, list[dict]],
    min_sources: int = 3,
    max_stories: int = 5,
    similarity_threshold: float = 0.35,
) -> list[dict]:
    """
    Find stories covered by >= min_sources distinct sources using TF-IDF clustering.
    Returns up to max_stories representative items (highest-scoring from each cluster),
    sorted by cluster size descending.
    """
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
        import numpy as np
    except ImportError:
        print("  [warn] scikit-learn not installed — skipping major stories", file=sys.stderr)
        return []

    # Flatten all items, tagging which source each came from
    all_items = []
    for source_name, items in sources.items():
        for item in items:
            all_items.append(dict(item, _source=source_name))

    if len(all_items) < min_sources:
        return []

    texts = [
        (item.get("title", "") + " " + item.get("summary", "")).strip().lower()
        for item in all_items
    ]

    try:
        tfidf = TfidfVectorizer(stop_words="english", min_df=1).fit_transform(texts)
    except ValueError:
        return []

    sims = cosine_similarity(tfidf)

    # Union-find clustering
    parent = list(range(len(all_items)))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x, y):
        parent[find(x)] = find(y)

    for i in range(len(all_items)):
        for j in range(i + 1, len(all_items)):
            if sims[i, j] >= similarity_threshold:
                union(i, j)

    # Group items by cluster root
    clusters: dict[int, list[int]] = {}
    for idx in range(len(all_items)):
        root = find(idx)
        clusters.setdefault(root, []).append(idx)

    # Keep clusters spanning >= min_sources distinct sources
    major = []
    for root, indices in clusters.items():
        source_names = {all_items[i]["_source"] for i in indices}
        if len(source_names) >= min_sources:
            # Pick the best-scored item as the representative
            cluster_items = [all_items[i] for i in indices]
            scored = score_items(cluster_items)
            best = scored[0]
            major.append({
                "title": best["title"],
                "link": best["link"],
                "summary": best.get("summary", ""),
                "source_count": len(source_names),
                "sources": sorted(source_names),
                "_score": best["_score"],
            })

    # Sort by source_count desc, then score desc
    major.sort(key=lambda x: (x["source_count"], x["_score"]), reverse=True)
    return major[:max_stories]


# ---------------------------------------------------------------------------
# Source gravity scoring + sorting
# ---------------------------------------------------------------------------

_GRAVITY_TERMS: dict[str, float] = {
    # National / federal
    "parliament":       1.5, "senate":          1.5, "prime minister":  1.5,
    "federal":          1.3, "supreme court":   2.0, "national":        1.2,
    "house of commons": 1.5, "trudeau":         1.3, "carney":          1.3,
    "rcmp":             1.3, "inquiry":         1.4, "tribunal":        1.4,

    # BC politics
    "legislature":      1.4, "provincial":      1.2, "minister":        1.2,
    "eby":              1.3, "nanaimo":         1.0, "bill":            1.1,
    "policy":           1.0, "election":        1.5, "budget":          1.4,
    "referendum":       1.5, "cabinet":         1.3,

    # Big story signals
    "breaking":         1.5, "emergency":       1.5, "death":           1.4,
    "wildfire":         1.4, "flood":           1.4, "earthquake":      1.6,
    "arrest":           1.3, "verdict":         1.4, "shooting":        1.5,
    "evacuation":       1.5, "closure":         1.2, "strike":          1.3,
    "protest":          1.2, "scandal":         1.4, "resignation":     1.4,

    # First Nations gravity
    "treaty":           1.4, "reconciliation":  1.3, "title":           1.3,
    "rights":           1.2, "landback":        1.4, "residential":     1.5,
    "inquiry":          1.4,
}


def _gravity_score(items: list[dict], top_n: int = 3) -> float:
    """
    Score a source's top_n stories for 'heavy news' signal.
    Returns a multiplier >= 1.0; higher = more important today.
    """
    if not items:
        return 1.0

    best = 1.0
    for item in items[:top_n]:
        text = (item.get("title", "") + " " + item.get("summary", "")).lower()
        score = 1.0
        for term, boost in _GRAVITY_TERMS.items():
            if term in text:
                score = max(score, boost)
        best = max(best, score)
    return best


def sort_sources(
    sources: dict[str, list[dict]],
    weights: dict[str, float],
    top_n: int = 3,
) -> dict[str, list[dict]]:
    """
    Sort sources by (base_weight × gravity_score), highest first.
    Sources with no items sort to the bottom.
    """
    def sort_key(name: str) -> float:
        items = sources.get(name, [])
        if not items:
            return -1.0
        base = weights.get(name, 1.0)
        gravity = _gravity_score(items, top_n)
        return base * gravity

    sorted_names = sorted(sources.keys(), key=sort_key, reverse=True)
    return {name: sources[name] for name in sorted_names}


# ---------------------------------------------------------------------------
# Within-source deduplication
# ---------------------------------------------------------------------------

def deduplicate(items: list[dict], threshold: float = 0.70) -> list[dict]:
    if len(items) < 2:
        return items
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
    except ImportError:
        return items

    texts = [
        (item.get("title", "") + " " + item.get("summary", "")).lower().strip()
        for item in items
    ]
    try:
        tfidf = TfidfVectorizer(stop_words="english", min_df=1).fit_transform(texts)
    except ValueError:
        return items

    sims = cosine_similarity(tfidf)
    kept, dropped = [], set()
    for i in range(len(items)):
        if i in dropped:
            continue
        kept.append(items[i])
        for j in range(i + 1, len(items)):
            if sims[i, j] >= threshold:
                dropped.add(j)
    return kept


# ---------------------------------------------------------------------------
# Extractive summarization
# ---------------------------------------------------------------------------

def summarize_item(item: dict, sentences: int = 1) -> str:
    _ensure_nltk_data()
    from nltk.corpus import stopwords
    from nltk.tokenize import sent_tokenize, word_tokenize

    text = item.get("summary", "").strip()
    if not text or len(text) < 120:
        return text

    stop = set(stopwords.words("english"))
    words = [w.lower() for w in word_tokenize(text) if w.isalpha() and w.lower() not in stop]
    freq = nltk.FreqDist(words)
    sent_list = sent_tokenize(text)
    if len(sent_list) <= sentences:
        return text

    def score(sent):
        return sum(freq[w.lower()] for w in word_tokenize(sent) if w.isalpha())

    ranked = set(sorted(sent_list, key=score, reverse=True)[:sentences])
    return " ".join(s for s in sent_list if s in ranked)


# ---------------------------------------------------------------------------
# Sentiment analysis
# ---------------------------------------------------------------------------

def sentiment_summary(sources: dict[str, list[dict]]) -> dict:
    _ensure_nltk_data()
    from nltk.sentiment.vader import SentimentIntensityAnalyzer
    sia = SentimentIntensityAnalyzer()

    pos = neu = neg = 0
    compound_total = 0.0
    all_items = [item for items in sources.values() for item in items]

    if not all_items:
        return {"overall": "neutral", "score": 0.0,
                "positive_pct": 0, "neutral_pct": 100, "negative_pct": 0}

    for item in all_items:
        text = (item.get("title", "") + ". " + item.get("summary", "")).strip()
        scores = sia.polarity_scores(text)
        compound_total += scores["compound"]
        if scores["compound"] >= 0.05:
            pos += 1
        elif scores["compound"] <= -0.05:
            neg += 1
        else:
            neu += 1

    total = pos + neu + neg
    avg = compound_total / total if total else 0.0
    overall = "positive" if avg >= 0.05 else "negative" if avg <= -0.05 else "neutral"

    return {
        "overall": overall,
        "score": round(avg, 3),
        "positive_pct": round(pos / total * 100),
        "neutral_pct": round(neu / total * 100),
        "negative_pct": round(neg / total * 100),
    }
