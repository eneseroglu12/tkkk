"""Optional, human-reviewed Groq wording assistance and local bilingual checks.

Never sends source Excel records or secret notes. Only transmits the candidate-safe
text that the HR reviewer explicitly consents to submit to an external provider.
"""
import re
from collections import Counter

INTERNAL_CODE = re.compile(r"(?<!\w)(?:AS|IFT|IK|İK|SNV|ING|İNG|GRP|VID|KNT|KAY|BEC)-[\w-]+", re.I)
APPLICATION_CODE = re.compile(r"\bBSV-\d+\b", re.I)
DIGITS = re.compile(r"(?<!\w)\d+(?:[.,]\d+)?(?!\w)")


def bilingual_check(tr, en, rejection_type=""):
    """Heuristic signals only: cannot establish semantic equivalence."""
    issues = []
    if not tr.strip() or not en.strip():
        issues.append("İki dilde de metin bulunmalı.")
    if Counter(DIGITS.findall(tr)) != Counter(DIGITS.findall(en)):
        issues.append("Türkçe ve İngilizce taslaklarda sayıların sayısı/değeri farklı.")
    if APPLICATION_CODE.search(tr) or APPLICATION_CODE.search(en):
        issues.append("Başvuru ID'si aday e-postasında görünüyor.")
    if INTERNAL_CODE.search(tr) or INTERNAL_CODE.search(en):
        issues.append("Aday metninde kurum içi kod görünüyor.")
    if rejection_type == "KONTENJAN_KISITI":
        if not re.search(r"kontenjan", tr, re.I) or not re.search(r"quota|capacity", en, re.I):
            issues.append("Kontenjan gerekçesi her iki dilde açık görünmüyor.")
    if not re.search(r"olumsuz|ilerleyem|devam edem|sonuçlan", tr, re.I) or not re.search(r"unable to|not proceed|unsuccessful|not moving forward|concluded", en, re.I):
        issues.append("Olumsuz kararın iki dilde açıkça yazıldığını gözden geçirin.")
    return issues


def polish_via_groq(text, language, api_key, model):
    """Send only explicitly reviewed candidate-facing text; return a suggestion, not approval."""
    if not api_key or not text.strip():
        raise ValueError("Groq API anahtarı ve taslak metin gerekli.")
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError("Groq bağlantısı için 'openai' kütüphanesini yükleyin.") from exc
    if language not in {"tr", "en"}:
        raise ValueError("Dil desteklenmiyor.")
    client = OpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1", timeout=30.0, max_retries=0)
    prompt = (
        "You are an HR wording editor. Polish ONLY the language of the user-provided email in "
        + ("Turkish" if language == "tr" else "English")
        + ". Do not add or remove ANY facts, numbers, decisions, past achievements, scoring details, "
          "rejection reasons, explanations, promises, or recommendations. Do not add any application IDs, "
          "internal record IDs, internal skill codes, minimum passing scores, or sensitive evaluator notes. "
          "Keep subject and respectful sign-off. Never change a capacity/quota rejection into a competence rejection. "
          "Output ONLY the full polished email, no commentary or Markdown."
    )
    resp = client.chat.completions.create(
        model=model,
        temperature=0,
        messages=[{"role": "system", "content": prompt}, {"role": "user", "content": text}],
    )
    answer = (resp.choices[0].message.content or "").strip()
    if not answer:
        raise RuntimeError("Groq boş sonuç döndürdü.")
    return answer


def suggestion_issues(original, suggestion, validator, bid, rejection_type="", language="tr"):
    issues = validator(bid, suggestion)
    if Counter(DIGITS.findall(original)) != Counter(DIGITS.findall(suggestion)):
        issues.append("Öneri, orijinal taslaktaki sayıları değiştirmiş.")
    if INTERNAL_CODE.search(suggestion) or APPLICATION_CODE.search(suggestion):
        issues.append("Öneride kurum içi kod veya başvuru numarası var.")
    if language == "tr" and not suggestion.startswith("Konu:"):
        issues.append("Türkçe e-posta konu satırı korunmamış.")
    if language == "en" and not suggestion.startswith("Subject:"):
        issues.append("İngilizce e-posta konu satırı korunmamış.")
    if rejection_type == "KONTENJAN_KISITI":
        if not re.search("kontenjan", suggestion, re.I) and language == "tr":
            issues.append("Kontenjan gerekçesi öneriden çıkarılmış.")
        if not re.search("quota|capacity", suggestion, re.I) and language == "en":
            issues.append("Quota gerekçesi öneriden çıkarılmış.")
    return list(dict.fromkeys(issues))
