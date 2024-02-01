import os
from dotenv import load_dotenv

from fastapi import FastAPI
from openai import OpenAI

from models import Prompt, Answer

# LOAD ENV VARS
load_dotenv()
OPEN_AI_APIKEY = os.getenv("OPEN_AI_APIKEY")
OPEN_AI_MODEL = os.getenv("OPEN_AI_MODEL")

# START SERVICES
client = OpenAI(api_key=OPEN_AI_APIKEY)
app = FastAPI()


@app.post("/openai/")
def openai_request(prompt: Prompt):
    response = client.chat.completions.create(
        model=OPEN_AI_MODEL,
        messages=[
            {
                "role": "user",
                "content": prompt.text,
            },
        ],
    )
    return Answer(text=response.choices[0].message.content)
