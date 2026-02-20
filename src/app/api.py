from fastapi import Body, FastAPI, HTTPException

from .agent import SYSTEM_PROMPT, run_agent
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

