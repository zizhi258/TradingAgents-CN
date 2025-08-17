import re


def _split_sentences(text: str) -> list[str]:
    # naive sentence split for CN/EN
    parts = re.split(r"(?<=[。！？.!?])\s+|\n+", text or "")
    return [p.strip() for p in parts if p and len(p.strip()) > 2]


def _score_sentence(q_tokens: list[str], sent: str) -> float:
    s_lower = sent.lower()
    hits = sum(1 for t in q_tokens if t and t.lower() in s_lower)
    return hits / max(1, len(set(q_tokens)))


def extract_evidence_snippets(
    query: str, sources: dict[str, str], top_k: int = 2
) -> list[tuple[str, str]]:
    """
    Lightweight local evidence search across provided reports.

    Args:
        query: free text to match against sentences
        sources: mapping of source name -> report text
        top_k: number of snippets to return

    Returns:
        List of (source_name, snippet) sorted by simple relevance
    """
    if not query:
        query = ""
    # tokenize query by words and Chinese characters (fallback)
    tokens = re.findall(r"[A-Za-z0-9_]+|[\u4e00-\u9fa5]", query)
    candidates: list[tuple[float, str, str]] = []  # (score, source, sentence)
    for name, text in (sources or {}).items():
        if not text:
            continue
        for sent in _split_sentences(text):
            score = _score_sentence(tokens, sent)
            if score > 0:
                candidates.append((score, name, sent))
    candidates.sort(key=lambda x: x[0], reverse=True)
    results: list[tuple[str, str]] = []
    for _, name, sent in candidates[: max(1, top_k)]:
        results.append((name, sent))
    return results
