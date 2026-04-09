from __future__ import annotations

"""
NLP utilities using NLTK + scikit-learn.

First run will download small NLTK data packages (~3MB total) automatically.
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
# Deduplication
# ---------------------------------------------------------------------------

def deduplicate(items: list[dict], threshold: float = 0.70) -> list[dict]:
    """
    Remove near-duplicate items across a list using TF-IDF cosine similarity.
    Items with similarity >= threshold to an already-kept item are dropped.
    Preserves original order; keeps the first occurrence.
    """
    if len(items) < 2:
        return items

    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
    except ImportError:
        print("  [warn] scikit-learn not installed — skipping deduplication", file=sys.stderr)
        return items

    texts = [
        (item.get("title", "") + " " + (item.get("summary") or item.get("snippet", "")))
        .lower()
        .strip()
        for item in items
    ]

    try:
        tfidf = TfidfVectorizer(stop_words="english", min_df=1).fit_transform(texts)
    except ValueError:
        return items

    sims = cosine_similarity(tfidf)
    kept = []
    dropped = set()
    for i in range(len(items)):
        if i in dropped:
            continue
        kept.append(items[i])
        for j in range(i + 1, len(items)):
            if sims[i, j] >= threshold:
                dropped.add(j)

    return kept


def deduplicate_by_category(rss_items: dict, supplemental: dict) -> tuple[dict, dict]:
    """
    Deduplicate within each category across both rss_items and supplemental combined,
    then split back out. Returns (rss_deduped, supplemental_deduped).
    """
    all_categories = set(list(rss_items.keys()) + list(supplemental.keys()))
    rss_out: dict = {}
    sup_out: dict = {}

    for cat in all_categories:
        rss = rss_items.get(cat, [])
        sup = supplemental.get(cat, [])
        # Tag source so we can split back out after dedup
        tagged = [dict(item, _src="rss") for item in rss] + \
                 [dict(item, _src="sup") for item in sup]
        deduped = deduplicate(tagged)
        rss_out[cat] = [
            {k: v for k, v in item.items() if k != "_src"}
            for item in deduped if item["_src"] == "rss"
        ]
        sup_out[cat] = [
            {k: v for k, v in item.items() if k != "_src"}
            for item in deduped if item["_src"] == "sup"
        ]

    return rss_out, sup_out


# ---------------------------------------------------------------------------
# Keyword extraction
# ---------------------------------------------------------------------------

def top_keywords(rss_items: dict, supplemental: dict, n: int = 20) -> list[str]:
    """
    Extract the top N meaningful keywords across all collected items
    using NLTK frequency distribution after stopword removal.
    """
    _ensure_nltk_data()

    from nltk.corpus import stopwords
    from nltk.tokenize import word_tokenize

    stop = set(stopwords.words("english"))
    # Add noise words common in news headlines
    stop.update({
        "say", "says", "said", "new", "one", "two", "three", "also", "us",
        "would", "could", "like", "get", "use", "make", "year", "years",
        "week", "day", "time", "first", "last", "back", "good", "way",
        "victoria", "bc", "british", "columbia",  # too common to be signal
    })

    all_text = []
    for items in list(rss_items.values()) + list(supplemental.values()):
        for item in items:
            all_text.append(item.get("title", ""))
            all_text.append(item.get("summary") or item.get("snippet", ""))

    tokens = word_tokenize(" ".join(all_text).lower())
    words = [
        w for w in tokens
        if w.isalpha() and len(w) > 3 and w not in stop
    ]

    freq = nltk.FreqDist(words)
    return [word for word, _ in freq.most_common(n)]


# ---------------------------------------------------------------------------
# Sentiment analysis
# ---------------------------------------------------------------------------

def sentiment_summary(rss_items: dict, supplemental: dict) -> dict:
    """
    Run VADER sentiment on all item titles + snippets.
    Returns {
        "overall": "positive" | "neutral" | "negative",
        "score": float,          # compound score -1.0 to +1.0
        "positive_pct": int,
        "neutral_pct": int,
        "negative_pct": int,
        "counts": {"pos": int, "neu": int, "neg": int},
    }
    """
    _ensure_nltk_data()

    from nltk.sentiment.vader import SentimentIntensityAnalyzer

    sia = SentimentIntensityAnalyzer()

    pos = neu = neg = 0
    compound_total = 0.0

    all_items = []
    for items in list(rss_items.values()) + list(supplemental.values()):
        all_items.extend(items)

    if not all_items:
        return {"overall": "neutral", "score": 0.0,
                "positive_pct": 0, "neutral_pct": 100, "negative_pct": 0,
                "counts": {"pos": 0, "neu": 0, "neg": 0}}

    for item in all_items:
        text = (item.get("title", "") + ". " +
                (item.get("summary") or item.get("snippet", ""))).strip()
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

    if avg >= 0.05:
        overall = "positive"
    elif avg <= -0.05:
        overall = "negative"
    else:
        overall = "neutral"

    return {
        "overall": overall,
        "score": round(avg, 3),
        "positive_pct": round(pos / total * 100),
        "neutral_pct": round(neu / total * 100),
        "negative_pct": round(neg / total * 100),
        "counts": {"pos": pos, "neu": neu, "neg": neg},
    }


# ---------------------------------------------------------------------------
# Extractive summarization
# ---------------------------------------------------------------------------

def summarize_item(item: dict, sentences: int = 2) -> str:
    """
    Return an extractive summary of an item's snippet/summary by scoring
    sentences using word frequency. Falls back to the raw snippet if text
    is too short to summarize meaningfully.
    """
    _ensure_nltk_data()

    from nltk.corpus import stopwords
    from nltk.tokenize import sent_tokenize, word_tokenize

    text = (item.get("summary") or item.get("snippet", "")).strip()
    if not text or len(text) < 120:
        return text  # too short to bother summarizing

    stop = set(stopwords.words("english"))
    words = [w.lower() for w in word_tokenize(text) if w.isalpha() and w.lower() not in stop]
    freq = nltk.FreqDist(words)

    sent_list = sent_tokenize(text)
    if len(sent_list) <= sentences:
        return text

    def score(sent: str) -> float:
        return sum(freq[w.lower()] for w in word_tokenize(sent) if w.isalpha())

    ranked = sorted(sent_list, key=score, reverse=True)[:sentences]
    # Return in original document order
    ordered = [s for s in sent_list if s in ranked]
    return " ".join(ordered)


def summarize_all(rss_items: dict, supplemental: dict) -> tuple[dict, dict]:
    """
    Apply extractive summarization to every item in-place (adds/replaces 'summary').
    Returns updated (rss_items, supplemental).
    """
    def _apply(items: list[dict]) -> list[dict]:
        return [dict(item, summary=summarize_item(item)) for item in items]

    return (
        {cat: _apply(items) for cat, items in rss_items.items()},
        {cat: _apply(items) for cat, items in supplemental.items()},
    )
