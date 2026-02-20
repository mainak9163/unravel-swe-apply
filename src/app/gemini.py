import json
import re
import time
from typing import Any

import requests

from .config import GEMINI_API_KEY, GEMINI_API_URL, GEMINI_MODEL
from .logging_setup import logger


def call_gemini(user_content: str, system_prompt: str) -> str:
    """Call Gemini generateContent and return text output."""
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not set.")

    payload = {
        "system_instruction": {"parts": [{"text": system_prompt}]},
        "contents": [{"role": "user", "parts": [{"text": user_content}]}],
        "generationConfig": {"temperature": 0.2},
    }
    start = time.perf_counter()
    logger.info("call_gemini start model=%s", GEMINI_MODEL)
    response = requests.post(
        GEMINI_API_URL,
        params={"key": GEMINI_API_KEY},
        json=payload,
        timeout=45,
    )
    elapsed_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "call_gemini status=%d duration_ms=%.1f", response.status_code, elapsed_ms
    )
    response.raise_for_status()
    data = response.json()
    candidates = data.get("candidates") or []
    if not candidates:
        raise RuntimeError(f"No Gemini candidates in response: {data}")
    parts = (candidates[0].get("content") or {}).get("parts") or []
    text = "\n".join(part.get("text", "") for part in parts if part.get("text")).strip()
    if not text:
        raise RuntimeError(f"No text returned by Gemini: {data}")
    return text


def _extract_first_json_object(text: str) -> dict[str, Any] | None:
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        return None
    try:
        parsed = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def identify_target_founder(evidence_context: str) -> dict[str, str]:
    """Use Gemini to extract founder candidates and choose the PR match."""
    extractor_prompt = """
You are extracting facts from evidence about Unravel.tech.
Rules:
- Use only the provided evidence.
- Do not guess.
- Choose target_founder only if the name contains letters "pr" (case-insensitive).
- Return valid JSON only.

Output schema:
{
  "founders": [{"name": "...", "source_url": "..."}],
  "target_founder": "...",
  "target_source_url": "...",
  "confidence": "high|medium|low",
  "notes": "short reason"
}
""".strip()

    extraction_input = (
        "Evidence:\n"
        f"{evidence_context}\n\n"
        "Extract founders and select the PR-matching founder."
    )

    for attempt in range(1, 4):
        logger.info("identify_target_founder attempt=%d", attempt)
        raw = call_gemini(extraction_input, system_prompt=extractor_prompt)
        parsed = _extract_first_json_object(raw)
        if not parsed:
            logger.warning("identify_target_founder invalid_json attempt=%d", attempt)
            continue
        target = str(parsed.get("target_founder") or "").strip()
        source_url = str(parsed.get("target_source_url") or "").strip()
        if target and "pr" in target.lower():
            logger.info(
                "identify_target_founder success target=%r source=%r",
                target,
                source_url,
            )
            return {"name": target, "source_url": source_url}
        logger.warning(
            "identify_target_founder no_valid_target attempt=%d target=%r",
            attempt,
            target,
        )
    raise RuntimeError("Could not confidently identify founder containing 'PR'.")

