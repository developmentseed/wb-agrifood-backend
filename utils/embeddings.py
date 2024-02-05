from __future__ import annotations

import json
import logging

import tiktoken
from dotenv import load_dotenv
from openai import OpenAI
from tqdm import tqdm

load_dotenv()


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

client = OpenAI()


def get_tokens(text: str):
    text = text.replace('\n', ' ')
    encoding = tiktoken.get_encoding('cl100k_base')
    return encoding.encode(text)


def get_embedding(tokens: list):

    if len(tokens) > 8191:
        logger.error('Token length execeeds 8191 tokens, truncating to 8191 tokens')
        tokens = tokens[:8191]

    return (
        client.embeddings.create(input=tokens, model='text-embedding-3-small')
        .data[0]
        .embedding
    )


def get_text_to_embed(data):

    text = data.get('description')
    if not text:
        text = data.get('name')
    if not text:
        text = data.get('summary')
    if not text:
        text = data.get('Project Development Objective')
    if not text:
        text = data.get('exerpt')
    if not text:
        return None
    return text


def prep_data():
    # TODO: fetch these from github?
    records = []
    for f in [
        'wb_ag_apps.json',
        'wb_ag_projects.json',
        'wb_ag_datasets.json',
        'wb_ag_microdatasets.json',
        'wb_ag_projects_datasets.json',
        'wb_youtube_videos.json',
        'wb_datasets.json',
        'wb_projects.json',
    ]:
        logger.info(f'Processing file: {f}')

        with open(f'../data/{f}') as fp:
            data = json.load(fp)
            if isinstance(data, dict):
                if data.get('data'):
                    data = data['data']
                else:
                    data = data.values()

        _type = f.split('_')[-1].replace('s.json', '')
        # TODO: generate in batches
        records.extend(
            [
                {
                    'text_to_embed': get_text_to_embed(d),
                    'tokens': get_tokens(get_text_to_embed(d)),
                    'metadata': {**d, 'type': _type},
                }
                for d in data
                if get_text_to_embed(d)
            ],
        )
    logger.info(f'Prepped {len(records)} records to embed')
    return records


# TODO: batch embeddings queries for speed
# def split_into_batches(data, threshold=8191):
#     result = []
#     current_batch = []

#     for d in data:
#         if sum([len(cd["tokens"]) for cd in current_batch]) + len(d["tokens"]) <= X:
#             current_batch.append(d["tokens"])
#         else:
#             result.append(current_batch)
#             current_batch = [d["tokens"]]

#     if current_batch:
#         result.append(current_batch)

#     return result


def generate_embeddings():
    data = prep_data()

    data = [{'embedding': get_embedding(d['tokens']), **d} for d in tqdm(data)]

    with open('records.json', 'w') as fp:
        json.dump(data, fp)

    num_tokens = sum([len(d['tokens']) for d in data])
    logger.info(
        f'Estimated total cost: {num_tokens / 1000 * 0.00002} dollars (for {num_tokens} tokens)',
    )
