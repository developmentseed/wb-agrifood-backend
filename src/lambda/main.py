import os

# from dotenv import load_dotenv

from fastapi import FastAPI
from openai import OpenAI
from mangum import Mangum

from models import Prompt, Answer

# LOAD ENV VARS
# load_dotenv()
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
OPENAI_MODEL = os.environ["OPENAI_MODEL"]

# START SERVICES
client = OpenAI(api_key=OPENAI_API_KEY)
app = FastAPI()


@app.get("/ping")
def ping():
    return {"ping": "pong"}


@app.post("/openai/")
def openai_request(prompt: Prompt):
    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {
                "role": "user",
                "content": prompt.text,
            },
        ],
    )
    return Answer(text=response.choices[0].message.content)


handler = Mangum(app, lifespan="off")
