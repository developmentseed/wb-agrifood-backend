from __future__ import annotations

import json
import os

import boto3
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum
from models import Prompt
from openai import OpenAI

# LOAD ENV VARS
# TODO: migrate this to Pydantic.BaseSettings (see utils/config.py)
# Ideally import for a shared location to avoid code duplication
OPENAI_ASSISTANT_ID = os.environ['OPENAI_ASSISTANT_ID']
OPENAI_API_KEY = os.environ['OPENAI_API_KEY']

THREAD_RUNNER_LAMBDA_ARN = os.environ['THREAD_RUNNER_LAMBDA_ARN']


FRONTEND_DOMAIN = os.environ.get('FRONTEND_DOMAIN')


_lambda = boto3.client('lambda')

app = FastAPI()

# START SERVICES
# TODO: place in app.startup routing

origins = [FRONTEND_DOMAIN or '*']
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)
client = OpenAI(api_key=OPENAI_API_KEY)


@app.get('/healthcheck')
def healthcheck():
    return {'status': 'running'}


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

    # TODO: check for any active runs first
    run = client.beta.threads.runs.create(
        thread_id=thread_id, assistant_id=OPENAI_ASSISTANT_ID,
    )

    # TODO: invoke thread_run_handler lambda
    _lambda.invoke(
        FunctionName=THREAD_RUNNER_LAMBDA_ARN,
        InvocationType='Event',
        Payload=json.dumps({'thread_id': thread_id, 'run_id': run.id}).encode('utf-8'),
    )

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
