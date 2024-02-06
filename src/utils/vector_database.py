from __future__ import annotations

import json
import logging

import embeddings
import lancedb
from config import settings

# TODO: why doesn't logger print anything?
logger = logging.getLogger(__name__)
logging.getLogger().setLevel(logging.INFO)


with open('records.json', 'r') as f:
    records = json.loads(f.read())
# Flatten records
data = [{'vector': r['embedding'], **r['metadata']} for r in records]

# LanceDB assumes uses the keys from the first list element
# as the table columns, so we first ensure that all records
# have the set same of keys (values will be None for keys
# not relevant to a record)
key_set = set()
for d in data:
    key_set.update(set(d.keys()))
data = [{**{k: None for k in key_set}, **d} for d in data]

db = lancedb.connect('.lancedb')
db.create_table('agrifood', data, mode='overwrite')

db = lancedb.connect('.lancedb')
table = db.open_table('agrifood')


logger.info(table.head())
queries = [
    'How is food security affected by drought in north africa?',
    'How has climate change affected wheat production in asian minor in the past decade?',
    'In what regions of the world is pivot irrigation most common?',
]
query_vectors = [
    embeddings.client.embeddings.create(input=q, model=settings.OPENAI_EMBEDDING_MODEL)
    .data[0]
    .embedding
    for q in queries
]

for q, v in zip(queries, query_vectors):
    _type = 'project'
    query_result = table.search(v).metric('cosine').where(f"type='{_type}'").limit(5)
    print(f'QUERY: {q}')
    print(f'RESULT: {query_result.to_list()}')
    print('\n')
