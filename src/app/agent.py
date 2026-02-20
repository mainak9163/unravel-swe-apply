from .config import GEMINI_MODEL
from .gemini import call_gemini, identify_target_founder
from .logging_setup import logger
from .search import collect_search_context

SYSTEM_PROMPT = """
You are an AI assistant applying for a job at Unravel.tech as per their X post instructions.

Your tasks IN ORDER:
1. Use the provided evidence to find the founders of Unravel.tech
   (the AI-focused startup founded in 2023 — NOT Unravel Data or travel apps).
2. Identify the founder whose name contains the letters 'PR' (case-insensitive).
3. Use their first name (lowercase) to construct the email address: <first_name>@unravel.tech
4. Write a professional cover letter for the applicant using the details provided.
5. Subject must be: "Apply with DSPy: <rhyming_word>" where rhyming_word is given by the user.

IMPORTANT:
- Never mention model knowledge cutoffs or inability to browse.
- Base founder identification only on provided evidence.
- Output ONLY the final email draft in this exact format (no extra text before/after):

To: [email]
Subject: [subject]
Body:
[body text]
Attachment: [resume filename]
""".strip()


def is_valid_email_draft(content: str) -> bool:
    """Validate strict output format for final response."""
    if not content:
        return False
    text = content.strip()
    return (
        "To:" in text
        and "Subject:" in text
        and "Body:" in text
        and "Attachment:" in text
        and text.startswith("To:")
    )


def has_disallowed_phrases(content: str) -> bool:
    """Block known failure-text patterns from being returned as final output."""
    lowered = (content or "").lower()
    blocked = [
        "knowledge cutoff",
        "unable to browse",
        "could not be identified",
        "recommend calling web_search again",
    ]
    return any(phrase in lowered for phrase in blocked)


def run_agent(messages: list[dict]) -> str:
    """Run search first, then ask Gemini to generate the final email using evidence."""
    logger.info(
        "run_agent start model=%s initial_messages=%d", GEMINI_MODEL, len(messages)
    )
    user_prompt = messages[-1].get("content", "")
    search_context = collect_search_context()
    target_founder = identify_target_founder(search_context)
    founder_name = target_founder["name"]
    founder_first = founder_name.split()[0].lower()
    founder_email = f"{founder_first}@unravel.tech"
    logger.info(
        "run_agent founder_selected name=%r email=%r", founder_name, founder_email
    )

    combined_prompt = (
        f"{user_prompt}\n\n"
        f"Selected founder: {founder_name}\n"
        f"Required recipient email: {founder_email}\n"
        f"Source URL for selected founder: {target_founder.get('source_url', '')}\n\n"
        "Evidence (for verification only):\n"
        f"{search_context}\n\n"
        "Now produce the final answer in the required format. "
        "Do not change the recipient email."
    )

    for attempt in range(1, 4):
        logger.info("run_agent gemini_attempt=%d", attempt)
        final_content = call_gemini(combined_prompt, system_prompt=SYSTEM_PROMPT)
        if not is_valid_email_draft(final_content):
            logger.warning(
                "run_agent rejected_response reason=invalid_format attempt=%d",
                attempt,
            )
            combined_prompt += (
                "\n\nYour previous output was invalid. Return ONLY:\n"
                "To: ...\nSubject: ...\nBody:\n...\nAttachment: ..."
            )
            continue
        if has_disallowed_phrases(final_content):
            logger.warning(
                "run_agent rejected_response reason=disallowed_phrases attempt=%d",
                attempt,
            )
            combined_prompt += (
                "\n\nDo not mention knowledge cutoff or browsing limits. "
                "Use provided snippets."
            )
            continue
        logger.info("run_agent success attempt=%d", attempt)
        return final_content

    raise RuntimeError("Gemini did not produce a valid final response.")

