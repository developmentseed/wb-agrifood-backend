from __future__ import annotations

import json
import os
import time
from typing import Optional

import lancedb
import requests
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum
from models import Prompt
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
app = FastAPI()
origins = [FRONTEND_DOMAIN or '*']
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)
client = OpenAI(api_key=OPENAI_API_KEY)
assistants = [
    assistant
    for assistant in client.beta.assistants.list()
    if assistant.name == OPENAI_ASSISTANT_NAME
]
if not assistants:
    raise Exception(f'Assistant {OPENAI_ASSISTANT_NAME} not found')
assistant = assistants[0]

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
def get_rag_matches(query: str, datatype: Optional[str] = None, num_results: int = 10):
    query_embedding = get_embedding(query)
    search_query = table.search(query_embedding).metric('cosine').limit(num_results)

    if datatype:
        search_query = search_query.where(f"type = '{datatype}'", prefilter=True)

    query_response = [
        {k: v for k, v in r.items() if k != 'vector'} for r in search_query.to_list()
    ]

    print('Query response: ', query_response)

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
def search_knowledge_base(query: str, datatype: Optional[str] = None):
    return '\n'.join(get_rag_matches(query, datatype))


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


# @app.post("/vector_search")
# def vector_search(prompt: Prompt):
#     table = db.open_table("agrifood")

#     query_vector = (
#         client.embeddings.create(
#             input=prompt.message,
#             model=OPENAI_EMBEDDING_MODEL,
#         )
#         .data[0]
#         .embedding
#     )
#     return [
#         {k: v for k, v in r.items() if k != "vector"}
#         for r in table.search(query_vector).metric("cosine").limit(10).to_list()
#     ]


@app.get('/healthcheck')
def healthcheck():
    return {'status': 'running'}


# @app.post("/openai")
# def openai_request(prompt: Prompt):
#     response = client.chat.completions.create(
#         model=OPENAI_MODEL,
#         messages=[
#             {
#                 "role": "user",
#                 "content": prompt.text,
#             },
#         ],
#     )
#     return Answer(text=response.choices[0].message.content)


# @app.post("/thread/")
# def create_thread(message: Prompt):
#     thread = client.beta.threads.create(
#         messages=[
#             {
#                 "role": "user",
#                 "content": message.text,
#             },
#         ],
#     )
#     return Thread(id=thread.id, created=datetime.fromtimestamp(thread.created_at))


def wait_for_status(thread_id: str, run_id: str):
    run = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run_id)
    while run.status in ['queued', 'in_progress', 'cancelling']:
        time.sleep(1)
        run = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run_id)
    return run


@app.post('/threads')
def create_thread():
    thread = client.beta.threads.create()
    return thread


@app.post('/threads/{thread_id}/messages')
def create_message(thread_id: str, prompt: Prompt):

    client.beta.threads.messages.create(
        thread_id=thread_id,
        role='user',
        content=prompt.message,
    )

    run = client.beta.threads.runs.create(
        thread_id=thread_id,
        assistant_id=assistant.id,
    )

    run = wait_for_status(thread_id, run.id)

    if run.status == 'requires_action':
        print('Action required by the assistant...')
        for tool_call in run.required_action.submit_tool_outputs.tool_calls:  # type: ignore

            # Eventually tool_call.type may be other than
            # `function`, at which point we'll need to handle
            function_name = tool_call.function.name

            arguments = json.loads(tool_call.function.arguments)

            if function_name not in function_mapping.keys():
                raise Exception(f'Function {function_name} unknown')

            print(f'Calling function {function_name} with args: {arguments}')

            response = function_mapping[function_name](**arguments)  # type: ignore

            print(f'Function response: {response}')
            submit_tool_outputs(thread_id, run.id, tool_call.id, response)

    return run


@app.get('/threads/{thread_id}/messages')
def get_messages(thread_id: str):
    messages = client.beta.threads.messages.list(thread_id=thread_id)
    return messages.data


@app.get('/threads/{thread_id}/runs/{run_id}/status')
def get_run_status(run_id: str, thread_id: str):
    run = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run_id)
    return {'status': run.status}


handler = Mangum(app, lifespan='off')
