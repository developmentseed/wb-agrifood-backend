from __future__ import annotations

import json
import os
from datetime import datetime

import lancedb
import requests
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum
from models import Answer
from models import Prompt
from models import Thread
from openai import OpenAI

# LOAD ENV VARS
# TODO: migrate this to Pydantic.BaseSettings (see utils/config.py)
# Ideally import for a shared location to avoid code duplication
OPENAI_ASSISTANT_NAME = os.environ['OPENAI_ASSISTANT_NAME']
OPENAI_API_KEY = os.environ['OPENAI_API_KEY']
OPENAI_MODEL = os.environ['OPENAI_MODEL']
OPENAI_EMBEDDING_MODEL = os.environ['OPENAI_EMBEDDING_MODEL']
FRONTEND_DOMAIN = os.environ.get('FRONTEND_DOMAIN')

# START SERVICES
# TODO: place in app.startup routing
client = OpenAI(api_key=OPENAI_API_KEY)
app = FastAPI()
origins = [FRONTEND_DOMAIN or '*']
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)
db = lancedb.connect('.lancedb')
table = db.open_table('agrifood')


# TODO: adding typing to function parameters + output
# Function to get use case details
def get_use_case_details(use_case_id):
    url = 'https://search.worldbank.org/api/v2/projects'
    params = {'id': use_case_id}
    response = requests.post(url, params=params)
    return response.json() if response.status_code == 200 else None


# Function to get data details
def get_data_details(data_unique_id):
    url = 'https://datacatalogapi.worldbank.org/ddhxext/DatasetView'
    params = {'dataset_unique_id': data_unique_id}
    response = requests.post(url, params=params)
    return response.json() if response.status_code == 200 else None


# Function to get data file details
def get_data_file_details(data_file_unique_id):
    url = 'https://datacatalogapi.worldbank.org/ddhxext/ResourceView'
    params = {'resource_unique_id': data_file_unique_id}
    response = requests.post(url, params=params)
    return response.json() if response.status_code == 200 else None


# Function to download data file
def download_data_file(data_file_unique_id, version_id):
    url = 'https://datacatalogapi.worldbank.org/ddhxext/DownloadResource'
    params = {'resource_unique_id': data_file_unique_id, 'version_id': version_id}
    response = requests.post(url, params=params)
    return response.json() if response.status_code == 200 else None


# Function to open data file
def open_data_file(data_file_unique_id):
    url = 'https://datacatalogapi.worldbank.org/ddhxext/OpenResource'
    params = {'resource_unique_id': data_file_unique_id}
    response = requests.post(url, params=params)
    return response.json() if response.status_code == 200 else None


# Function to get embeddings
def get_embedding(text: str):
    return (
        client.embeddings.create(input=text, model=OPENAI_EMBEDDING_MODEL)
        .data[0]
        .embedding
    )


# Function to get top 10 query results from Pinecone
def get_rag_matches(query: str, _type: str, num_results: int = 10):
    query_embedding = get_embedding(query)
    query_response = [
        {k: v for k, v in r.items() if k != 'vector'}
        for r in table.search(query_embedding)
        .metric('cosine')
        .limit(num_results)
        .where(f"type = '{_type}'", prefilter=True)
        .to_list()
    ]

    rag_matches = [
        r['text_to_embed'] + ' Unique ID: ' + str(r['id']) for r in query_response
    ]
    return rag_matches


# TODO: do we need re-ranking?
# # Function to rerank the top 10 query results from Pinecone
# def rerank_rag_matches(query, documents):
#     reranked_results = co.rerank(
#         query=query, documents=documents, top_n=5, model="rerank-multilingual-v2.0"
#     )
#     return reranked_results


# Function to search a knowledge base
def search_knowledge_base(query: str, _type: str):
    return '\n'.join(get_rag_matches(query, _type))


# Function to submit tool outputs
def submit_tool_outputs(thread_id, run_id, tool_call_id, output):
    client.beta.threads.runs.submit_tool_outputs(
        thread_id=thread_id,
        run_id=run_id,
        tool_outputs=[{'tool_call_id': tool_call_id, 'output': json.dumps(output)}],
    )


# Function mapping
function_mapping = {
    'search_knowledge_base': search_knowledge_base,
    'get_use_case_details': get_use_case_details,
    'get_data_details': get_data_details,
    'get_data_file_details': get_data_file_details,
    'download_data_file': download_data_file,
    'open_data_file': open_data_file,
}


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


@app.post('/thread/')
def create_thread():
    thread = client.beta.threads.create()
    return Thread(id=thread.id, created=datetime.fromtimestamp(thread.created_at))


@app.post('/thread/{id}')
def add_to_thread(id: str, prompt: Prompt):
    client.beta.threads.messages.create(
        thread_id=id,
        role='user',
        content=prompt.text,
    )
    assistant = [
        assistant
        for assistant in client.beta.assistants.list()
        if assistant.name == OPENAI_ASSISTANT_NAME
    ]
    if not prompt.run_id:
        run = client.beta.threads.runs.create(
            thread_id=id, assistant_id=assistant[0].id,
        )

    run = client.beta.threads.runs.retrieve(
        thread_id=id, run_id=prompt.run_id or run.id,
    )
    reply = client.beta.threads.messages.list(thread_id=id)

    return reply.data


handler = Mangum(app, lifespan='off')
