"""
Job Application Agent — Gemini + Source-backed Web Search version

Requirements:
    pip install fastapi uvicorn requests ddgs

Environment:
    GEMINI_API_KEY=<your_api_key>
    SERPER_API_KEY=<optional_google_search_api_key>
    TAVILY_API_KEY=<optional_tavily_api_key>
"""

from src.app import app

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)

