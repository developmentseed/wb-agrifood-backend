from __future__ import annotations

import os
from datetime import datetime

import lancedb
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum
from models import Answer, Thread, Prompt
from openai import OpenAI

# from dotenv import load_dotenv

# LOAD ENV VARS
# load_dotenv()
OPENAI_ASSISTANT_NAME = os.environ.get('OPENAI_ASSISTANT_NAME')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
OPENAI_MODEL = os.environ.get('OPENAI_MODEL')
OPENAI_EMBEDDING_MODEL = os.environ.get('OPENAI_EMBEDDING_MODEL')
FRONTEND_DOMAIN = os.environ.get('FRONTEND_DOMAIN')

# START SERVICES
client = OpenAI(api_key=OPENAI_API_KEY)
app = FastAPI()
origins = [FRONTEND_DOMAIN or "*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
db = lancedb.connect('.lancedb')


@app.post('/vector_search')
def vector_search(prompt: Prompt):
    table = db.open_table('agrifood')

    query_vector = (
        client.embeddings.create(
            input=prompt.text,
            model=OPENAI_EMBEDDING_MODEL,
        )
        .data[0]
        .embedding
    )
    return [
        {k: v for k, v in r.items() if k != 'vector'}
        for r in table.search(query_vector).metric('cosine').limit(10).to_list()
    ]


@app.get('/healthcheck')
def healthcheck():
    return {'status': 'running'}


@app.post('/openai')
def openai_request(prompt: Prompt):
    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {
                'role': 'user',
                'content': prompt.text,
            },
        ],
    )
    return Answer(text=response.choices[0].message.content)


@app.post("/thread/")
def create_thread():
    thread = client.beta.threads.create()
    return Thread(id=thread.id, created=datetime.fromtimestamp(thread.created_at))


@app.post("/thread/{id}")
def add_to_thread(id: str, prompt: Prompt):
    client.beta.threads.messages.create(
        thread_id=id,
        role="user",
        content=prompt.text,
    )
    assistant = [
        assistant
        for assistant in client.beta.assistants.list()
        if assistant.name == OPENAI_ASSISTANT_NAME
    ]
    if not prompt.run_id:
        run = client.beta.threads.runs.create(thread_id=id, assistant_id=assistant[0].id)

    run = client.beta.threads.runs.retrieve(thread_id=id, run_id=prompt.run_id or run.id)
    reply = client.beta.threads.messages.list(thread_id=id)

    return reply.data


handler = Mangum(app, lifespan='off')
