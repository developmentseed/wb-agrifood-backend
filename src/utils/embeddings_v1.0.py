from __future__ import annotations

import concurrent.futures
import csv
import json
import os

import tiktoken
from openai import OpenAI
from tqdm import tqdm


def get_tokens(text: str):
    text = text.replace('\n', ' ')
    encoding = tiktoken.get_encoding('cl100k_base')
    return encoding.encode(text)


def get_embedding(tokens: list):

    if len(tokens) > 8191:
        raise Exception('Token length execeeds 8191 tokens, truncating to 8191 tokens')
        tokens = tokens[:8191]

    return (
        client.embeddings.create(input=tokens, model='text-embedding-3-small')
        .data[0]
        .embedding
    )


if __name__ == '__main__':

    data_files = [
        'wb_ag_datasets.csv',
        'wb_ag_projects.csv',
        'wb_youtube_videos.json',
        'wb_ag_ext_papers.csv',
        'wb_ag_usecases.csv',
    ]
    data = []

    for file in data_files:
        print(f'FILE: {file}')
        if file.endswith('.json'):
            with open(f'../../data/{file}') as f:
                rows = json.loads(f.read())
        else:
            with open(f'../../data/{file}', 'r') as f:
                rows = [r for r in csv.DictReader(f)]
        print(rows[0].keys())
        data.extend(
            [
                {
                    **row,
                    'type': file.replace('wb_', '')
                    .replace('ag_', '')
                    .split('.')[0][:-1],
                }
                for row in rows
            ],
        )
    len(data)

    for d in data:
        if not d.get('id') and d.get('dataset_id'):
            d['id'] = d['dataset_id']
        elif not d.get('id') and d['type'] == 'youtube_video':
            d['video_id'] = (
                d['link'].replace('https://www.youtube.com/watch?v=', '').split('&')[0]
            )
            d['timestamp'] = (
                d['link']
                .replace('https://www.youtube.com/watch?v=', '')
                .split('&')[1]
                .replace('t=', '')[:-1]
            )
            d['id'] = (
                d['link']
                .replace('https://www.youtube.com/watch?v=', '')
                .replace('&t=', '_')[:-1]
            )

    for d in data:
        d['text_to_embed'] = '. '.join([v for v in d.values()])

    key_set = set()
    for d in data:
        key_set.update(set(d.keys()))
    data = [{**{k: None for k in key_set}, **d} for d in data]

    client = OpenAI(api_key=os.environ['OPENAI_API_KEY'])

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        embeddings = list(
            tqdm(
                executor.map(
                    lambda d: get_embedding(
                        get_tokens(d['text_to_embed']),
                    ),  # some boto3 operation
                    data,
                ),
                total=len(data),  # sets total length of progressbar
            ),
        )
