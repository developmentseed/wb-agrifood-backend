from __future__ import annotations

import os

import lancedb
from fastapi import FastAPI
from mangum import Mangum
from models import Answer
from models import Prompt
from openai import OpenAI

# from dotenv import load_dotenv

# LOAD ENV VARS
# load_dotenv()
OPENAI_ASSISTANT_NAME = os.environ['OPENAI_ASSISTANT_NAME']
OPENAI_API_KEY = os.environ['OPENAI_API_KEY']
OPENAI_MODEL = os.environ['OPENAI_MODEL']
OPENAI_EMBEDDING_MODEL = os.environ['OPENAI_EMBEDDING_MODEL']

# START SERVICES
client = OpenAI(api_key=OPENAI_API_KEY)
app = FastAPI()
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


handler = Mangum(app, lifespan='off')
