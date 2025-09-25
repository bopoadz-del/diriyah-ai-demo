from fastapi import APIRouter, Query
import os, openai

router = APIRouter()

@router.get("/ai/process")
def process(prompt: str = Query(...)):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return {"status": "error", "message": "OpenAI key not set"}
    openai.api_key = api_key
    try:
        response = openai.Completion.create(engine="text-davinci-003", prompt=prompt, max_tokens=100)
        return {"status": "ok", "response": response.choices[0].text.strip()}
    except Exception as e:
        return {"status": "error", "message": str(e)}
