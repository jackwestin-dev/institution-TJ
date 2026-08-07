"""
Essay answer-guide fetching and concept-checking.

Three backends are supported (in increasing capability order):
  1. "keyword"  — no API key required; pure text matching
  2. "gemini"   — Google Gemini free API (aistudio.google.com, just a Google account)
  3. "anthropic" — Anthropic Claude (requires console.anthropic.com account)
"""
import re
import json
import requests


# ── Google Doc helper ─────────────────────────────────────────────────────────

def extract_google_doc_id(url: str) -> "str | None":
    m = re.search(r'/document/d/([a-zA-Z0-9_-]+)', url)
    return m.group(1) if m else None


def fetch_google_doc(url: str) -> str:
    doc_id = extract_google_doc_id(url)
    if not doc_id:
        raise ValueError(
            "Not a valid Google Docs URL. "
            "It should look like: docs.google.com/document/d/..."
        )
    export_url = f"https://docs.google.com/document/d/{doc_id}/export?format=txt"
    r = requests.get(export_url, timeout=15)
    if r.status_code in (401, 403):
        raise PermissionError(
            "Document is not accessible. "
            "Share it as 'Anyone with the link can view' and try again."
        )
    r.raise_for_status()
    return r.text


# ── Keyword backend (no API) ──────────────────────────────────────────────────

# Common English stop words to skip when extracting key terms
_STOP = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "shall",
    "should", "may", "might", "can", "could", "this", "that", "these",
    "those", "it", "its", "they", "them", "their", "which", "who", "what",
    "when", "where", "how", "if", "as", "from", "into", "about", "not",
}


def _key_words(text: str) -> list:
    """Extract meaningful words from text (lowercase, no stop words, ≥4 chars)."""
    words = re.findall(r"[a-z]{4,}", text.lower())
    return [w for w in words if w not in _STOP]


def _extract_concepts_from_text(text: str) -> list:
    """
    Parse plain-text answer guide section into a list of concept strings.
    Handles bullet points (-, *, •, numbers) and plain paragraphs.
    """
    concepts = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        # Strip leading bullet/number markers
        line = re.sub(r'^(?:[-*•]|\d+[.):])\s*', '', line)
        if line:
            concepts.append(line)
    return concepts


def parse_answer_guide_keyword(doc_text: str) -> dict:
    """
    Parse an answer guide document without any AI.
    Returns {question_label: [concept_string, …]}.

    Recognises sections like:
      Q1: / Question 1: / 1. / 1)
    followed by bullet-pointed or paragraph key concepts.
    """
    result: dict = {}
    current_label: "str | None" = None
    current_lines: list = []

    def _flush():
        if current_label and current_lines:
            result[current_label] = _extract_concepts_from_text("\n".join(current_lines))

    for line in doc_text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue

        # Detect a question header line
        m = re.match(
            r'^(?:(?:Q(?:uestion)?\s*(\d+)\s*[:.)])|(\d+)[.):])\s*(.*)',
            stripped, re.IGNORECASE,
        )
        if m:
            _flush()
            q_num = m.group(1) or m.group(2)
            q_text = (m.group(3) or "").strip()
            current_label = f"Q{q_num}" + (f": {q_text[:60]}" if q_text else "")
            current_lines = []
        else:
            current_lines.append(stripped)

    _flush()

    # Fallback: if no question headers found, treat the whole doc as one guide
    if not result and doc_text.strip():
        result["Q1"] = _extract_concepts_from_text(doc_text)

    return result


def concept_check_keyword(
    question_label: str,
    concepts: list,
    student_response: str,
) -> dict:
    """
    Check essay coverage using keyword matching — no API required.

    A concept is considered "covered" if ≥ 60 % of its key words appear in
    the student response (case-insensitive substring matching).
    """
    response_lower = student_response.lower()
    covered, missing = [], []

    for concept in concepts:
        kws = _key_words(concept)
        if not kws:
            continue
        matches = sum(1 for w in kws if w in response_lower)
        if matches / len(kws) >= 0.40:
            covered.append(concept)
        else:
            missing.append(concept)

    total = len(covered) + len(missing)
    pct = round(len(covered) / total * 100) if total else 0

    if not student_response.strip():
        feedback = "No response provided."
    elif pct >= 80:
        feedback = f"Good coverage — addressed {len(covered)}/{total} key concept(s)."
    elif pct >= 50:
        feedback = f"Partial coverage — {len(missing)} concept(s) not clearly addressed."
    else:
        feedback = f"Low coverage — {len(missing)}/{total} concept(s) missing from response."

    return {
        "covered": covered,
        "missing": missing,
        "coverage_pct": pct,
        "feedback": feedback,
    }


# ── Google Gemini backend (free tier) ─────────────────────────────────────────

def _gemini_available() -> bool:
    try:
        from google import genai  # noqa: F401
        return True
    except ImportError:
        return False


def parse_answer_guide_gemini(doc_text: str, api_key: str) -> dict:
    """Parse answer guide using Google Gemini (free tier via google-genai SDK)."""
    from google import genai
    client = genai.Client(api_key=api_key)

    prompt = (
        "This document is an MCAT essay answer guide for a Canvas quiz. "
        "Extract each question and the key concepts or criteria expected in a complete answer.\n\n"
        f"Document:\n{doc_text[:6000]}\n\n"
        "Return ONLY valid JSON — no markdown fences, no commentary:\n"
        '{"Q1": "Key concept A; Key concept B", "Q2": "Key concept C; Key concept D"}\n'
        "Use question numbers (Q1, Q2...) if visible, otherwise use the first five words of each question."
    )
    resp = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
    text = resp.text.strip()
    text = re.sub(r'^```(?:json)?\s*', '', text)
    text = re.sub(r'\s*```$', '', text).strip()
    return json.loads(text)


def concept_check_gemini(
    question_label: str,
    answer_guide: str,
    student_response: str,
    api_key: str,
) -> dict:
    """Evaluate one essay response using Google Gemini (free tier via google-genai SDK)."""
    from google import genai
    client = genai.Client(api_key=api_key)

    prompt = (
        f"Evaluate this MCAT student essay response for {question_label}.\n\n"
        f"Expected key concepts:\n{answer_guide}\n\n"
        f"Student response:\n{student_response or '(no response provided)'}\n\n"
        "Return ONLY valid JSON — no markdown fences, no commentary:\n"
        "{\n"
        '  "covered": ["concept clearly addressed"],\n'
        '  "missing": ["concept not addressed or only partially addressed"],\n'
        '  "coverage_pct": 70,\n'
        '  "feedback": "One sentence of constructive feedback for the student."\n'
        "}"
    )
    resp = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
    text = resp.text.strip()
    text = re.sub(r'^```(?:json)?\s*', '', text)
    text = re.sub(r'\s*```$', '', text).strip()
    return json.loads(text)


# ── Anthropic backend ─────────────────────────────────────────────────────────

def parse_answer_guide(doc_text: str, client) -> dict:
    """Parse answer guide using Anthropic Claude."""
    msg = client.messages.create(
        model="claude-opus-4-8",
        max_tokens=2048,
        messages=[{
            "role": "user",
            "content": (
                "This document is an MCAT essay answer guide for a Canvas quiz. "
                "Extract each question and the key concepts or criteria expected in a complete answer.\n\n"
                f"Document:\n{doc_text[:6000]}\n\n"
                "Return ONLY valid JSON — no markdown fences, no commentary:\n"
                '{"Q1": "Key concept A; Key concept B", "Q2": "Key concept C"}\n'
                "Use question numbers (Q1, Q2…) if visible, otherwise use the first five words of each question."
            )
        }]
    )
    text = msg.content[0].text.strip()
    text = re.sub(r'^```(?:json)?\s*', '', text)
    text = re.sub(r'\s*```$', '', text).strip()
    return json.loads(text)


def concept_check(
    question_label: str,
    answer_guide: str,
    student_response: str,
    client,
) -> dict:
    """Evaluate one essay response using Anthropic Claude."""
    msg = client.messages.create(
        model="claude-opus-4-8",
        max_tokens=512,
        messages=[{
            "role": "user",
            "content": (
                f"Evaluate this MCAT student essay response for {question_label}.\n\n"
                f"Expected key concepts:\n{answer_guide}\n\n"
                f"Student response:\n{student_response or '(no response provided)'}\n\n"
                "Return ONLY valid JSON — no markdown fences, no commentary:\n"
                "{\n"
                '  "covered": ["concept clearly addressed"],\n'
                '  "missing": ["concept not addressed or only partially addressed"],\n'
                '  "coverage_pct": 70,\n'
                '  "feedback": "One sentence of constructive, specific feedback for the student."\n'
                "}"
            )
        }]
    )
    text = msg.content[0].text.strip()
    text = re.sub(r'^```(?:json)?\s*', '', text)
    text = re.sub(r'\s*```$', '', text).strip()
    return json.loads(text)
