from __future__ import annotations

import concurrent.futures
import json
import logging
from pathlib import Path

import boto3
import lancedb
import tiktoken
from config import settings
from openai import OpenAI


logger = logging.getLogger(__name__)
logging.getLogger().setLevel(logging.INFO)

TABLE_NAME = 'agrifood'

OPENAI_CLIENT = OpenAI(api_key=settings.OPENAI_API_KEY)
BOTO3_CLIENT = boto3.client('cloudformation', region_name='us-east-1')
DATA_FILE_PATH = Path('data/records.json')


def instantiate_database() -> lancedb.DBConnection:

    response = BOTO3_CLIENT.describe_stacks(
        StackName=f'wb-agrifoods-data-lab-{settings.STAGE}'.lower(),
    )
    outputs = response['Stacks'][0]['Outputs']
    [bucket_name] = [
        o['OutputValue'] for o in outputs if o['OutputKey'] == 'bucketname'
    ]

    return lancedb.connect(f's3://{bucket_name}/{settings.LANCEDB_DATA_PATH}')


def generate_embeddings(records: list[dict]) -> list[dict]:

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        embeddings = list(
            executor.map(
                lambda d: get_embedding(get_tokens(get_text_to_embed(d))), records,
            ),
        )

    records = [
        {**d, 'embedding': embedding} for d, embedding in zip(records, embeddings)
    ]
    return records


def prep_records_for_insert(records: list[dict]) -> list[dict]:
    # Flatten records
    records = [
        {'vector': r['embedding'], **{k: v for k, v in r.items() if k != 'embedding'}}
        for r in records
    ]

    # LanceDB assumes uses the keys from the first list element
    # as the table columns, so we first ensure that all records
    # have the set same of keys (values will be None for keys
    # not relevant to a record)
    key_set = set()
    for r in records:
        key_set.update(set(r.keys()))
    return [{**{k: None for k in key_set}, **d} for d in records]


def upload_data(database: lancedb.DBConnection, records: list[dict]):

    database.create_table(TABLE_NAME, records, mode='overwrite')
    logger.info(f'Loaded table with {len(records)}')
    return database.open_table(TABLE_NAME)


def get_text_to_embed(d: dict) -> str:
    return '\n '.join(
        [f'{key}: {value}' for key, value in d.items() if value is not None],
    )


def get_tokens(text: str) -> list[int]:
    text = text.replace('\n', ' ')
    encoding = tiktoken.get_encoding('cl100k_base')
    return encoding.encode(text)


def get_embedding(tokens: list) -> list[float]:

    if len(tokens) > 8191:
        print('WARNING: Token length execeeds 8191 tokens, truncating to 8191 tokens')
        tokens = tokens[:8191]

    return (
        OPENAI_CLIENT.embeddings.create(input=tokens, model='text-embedding-3-small')
        .data[0]
        .embedding
    )


if __name__ == '__main__':

    database = instantiate_database()

    # NOTE: must be run from project root!
    with open(DATA_FILE_PATH, 'r') as f:
        records = json.loads(f.read())[:10]

    prepped_records = prep_records_for_insert(generate_embeddings(records))

    table = upload_data(database, prepped_records)

    logger.info(table.head())

    query = 'How is food security affected by drought in north africa?'
    query_vector = (
        OPENAI_CLIENT.embeddings.create(
            input=query, model=settings.OPENAI_EMBEDDING_MODEL,
        )
        .data[0]
        .embedding
    )

    query_result = table.search(query_vector).metric('cosine').limit(5)
    filtered_query_result = (
        table.search(query_vector).metric('cosine').where("type='project'").limit(5)
    )

    logger.info(f'Query: {query}')
    logger.info(f'Result (WITHOUT filter): {query_result.to_list()}')
    logger.info(f'Result (WITH filter): {filtered_query_result.to_list()}')
