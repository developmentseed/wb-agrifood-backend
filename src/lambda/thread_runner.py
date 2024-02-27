from __future__ import annotations

import json
import os
import time
from typing import Optional

import lancedb
import requests
from openai import OpenAI

# TODO: import this from a shared location (with main.py)
OPENAI_API_KEY = os.environ['OPENAI_API_KEY']
OPENAI_EMBEDDING_MODEL = os.environ['OPENAI_EMBEDDING_MODEL']
LANCEDB_DATA_PATH = os.environ.get('LANCEDB_DATA_PATH')
BUCKET_NAME = os.environ.get('BUCKET_NAME')


db = lancedb.connect(f's3://{BUCKET_NAME}/{LANCEDB_DATA_PATH}')
table = db.open_table('agrifood')

client = OpenAI(api_key=OPENAI_API_KEY)


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
def get_rag_matches(query: str, datatype: Optional[str] = None, num_results: int = 5):
    query_embedding = get_embedding(query)
    search_query = table.search(query_embedding).metric('cosine').limit(num_results)

    if datatype:
        search_query = search_query.where(f"type = '{datatype}'", prefilter=True)

    query_response = [
        {k: v for k, v in r.items() if k != 'vector'} for r in search_query.to_list()
    ]

    print('Query response: ', query_response)
    return query_response

    # rag_matches = [
    #     r["text_to_embed"] + " Unique ID: " + str(r["id"]) for r in query_response
    # ]
    # return rag_matches


# TODO: do we need re-ranking?
# # Function to rerank the top 10 query results from Pinecone
# def rerank_rag_matches(query, documents):
#     reranked_results = co.rerank(
#         query=query, documents=documents, top_n=5, model="rerank-multilingual-v2.0"
#     )
#     return reranked_results


# Function to search a knowledge base
def search_knowledge_base(query: str, datatype: Optional[str] = None):
    # return "\n".join(get_rag_matches(query, datatype))
    return get_rag_matches(query, datatype)


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


def process_thread_run(thread_id: str, run_id: str):

    run = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run_id)

    while run.status != 'completed':

        if run.status == 'requires_action':
            print('Action required by the assistant')
            for tool_call in run.required_action.submit_tool_outputs.tool_calls:  # type: ignore

                # Eventually tool_call.type may be other than
                # `function`, at which point we'll need to handle
                function_name = tool_call.function.name

                arguments = json.loads(tool_call.function.arguments)

                if function_name not in function_mapping.keys():
                    raise Exception(f'Function requested: {function_name} unknown')

                print(f'Calling function {function_name} with args: {arguments}')

                response = function_mapping[function_name](**arguments)  # type: ignore

                print(f'Function response: {response}')
                submit_tool_outputs(thread_id, run.id, tool_call.id, response)

        time.sleep(1)
        run = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run_id)


def handler(event, context):
    # TODO: validate event contains thread_id and run_id
    print(f"Processing thread run: {event['thread_id'], event['run_id']}")
    process_thread_run(event['thread_id'], event['run_id'])
