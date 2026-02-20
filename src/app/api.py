from fastapi import Body, FastAPI, HTTPException

from .agent import SYSTEM_PROMPT, run_agent, run_followup_and_send
from .logging_setup import logger

app = FastAPI(title="Job Application Agent (Gemini)")


@app.post("/apply")
async def apply_job(details: dict = Body(...)):
    """
    POST /apply
    Body (JSON, all fields optional):
    {
        "name": "Mainak Mukherjee",
        "bio": "...",
        "skills": "...",
        "role": "SDE-1",
        "resume_path": "resume.pdf",
        "rhyming_word": "Why"
    }
    """
    logger.info("POST /apply request received keys=%s", sorted(details.keys()))
    name = details.get("name", "Mainak Mukherjee")
    bio = details.get(
        "bio",
        "Software engineer with internships at Accenture, Graet, and "
        "CodemateAI, passionate about building end-to-end applications.",
    )
    skills = details.get(
        "skills",
        "Proficient in Python and TypeScript, interested in AI agents, "
        "system design (REST vs. GraphQL).",
    )
    role = details.get("role", "SDE-1")
    resume_path = details.get("resume_path", "resume.pdf")
    rhyming_word = details.get("rhyming_word", "Why")

    user_prompt = f"""
Applicant details:
- Name: {name}
- Bio: {bio}
- Skills/Experience: {skills}
- Applying for role: {role}
- Resume filename: {resume_path}
- Rhyming word for subject line: {rhyming_word}

Now perform your tasks. Start by searching for Unravel.tech founders.
""".strip()

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    try:
        logger.info("apply_job invoking run_agent")
        email_draft = run_agent(messages)
        logger.info("apply_job completed email_chars=%d", len(email_draft))
        return {"email_draft": email_draft}
    except Exception as exc:
        logger.exception("apply_job failed")
        raise HTTPException(status_code=500, detail=f"Agent error: {exc}") from exc


@app.post("/followup/send")
async def send_followup(details: dict = Body(...)):
    """
    POST /followup/send
    Body (JSON):
    {
        "applicant_name": "Mainak Mukherjee",
        "sender_email": "mainakcollege8967@gmail.com",
        "repo_url": "https://github.com/mainak9163/unravel-swe-apply",
        "recipient_override": "foundername.foundername@gmail.com",
        "video_note": "I will add a process walkthrough video link in the repository shortly.",
        "transparency_note": "...",
        "subject": "Re: Application - Agent Code Repository"
    }
    """
    logger.info("POST /followup/send request received keys=%s", sorted(details.keys()))
    applicant_name = details.get("applicant_name", "Mainak Mukherjee")
    sender_email = details.get("sender_email", "").strip()
    repo_url = details.get("repo_url", "").strip()
    recipient_override = details.get("recipient_override", "").strip()
    video_note = details.get("video_note", "")
    transparency_note = details.get("transparency_note", "")
    subject = details.get("subject", "Re: Application - Agent Code Repository")

    if not sender_email:
        raise HTTPException(status_code=400, detail="sender_email is required.")
    if not repo_url:
        raise HTTPException(status_code=400, detail="repo_url is required.")

    try:
        result = run_followup_and_send(
            applicant_name=applicant_name,
            sender_email=sender_email,
            repo_url=repo_url,
            video_note=video_note,
            transparency_note=transparency_note,
            subject=subject,
            recipient_override=recipient_override,
        )
        logger.info(
            "send_followup completed founder_email=%s subject=%r",
            result["founder_email"],
            result["subject"],
        )
        return result
    except Exception as exc:
        logger.exception("send_followup failed")
        raise HTTPException(status_code=500, detail=f"Agent error: {exc}") from exc
