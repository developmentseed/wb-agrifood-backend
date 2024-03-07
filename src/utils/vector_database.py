from __future__ import annotations

import json
import logging

import boto3
import embeddings
import lancedb
from config import settings

# TODO: why doesn't logger print anything?
logger = logging.getLogger(__name__)
logging.getLogger().setLevel(logging.INFO)

client = boto3.client('cloudformation', region_name='us-east-1')

response = client.describe_stacks(
    StackName=f'wb-agrifoods-data-lab-{settings.STAGE}'.lower(),
)
outputs = response['Stacks'][0]['Outputs']
[bucket_name] = [o['OutputValue'] for o in outputs if o['OutputKey'] == 'bucketname']


db = lancedb.connect(f's3://{bucket_name}/{settings.LANCEDB_DATA_PATH}')

with open('records_v1.0.json', 'r') as f:
    records = json.loads(f.read())
# Flatten records
data = [
    {'vector': r['embedding'], **{k: v for k, v in r.items() if k != 'embedding'}}
    for r in records
]

# LanceDB assumes uses the keys from the first list element
# as the table columns, so we first ensure that all records
# have the set same of keys (values will be None for keys
# not relevant to a record)
key_set = set()
for d in data:
    key_set.update(set(d.keys()))
data = [{**{k: None for k in key_set}, **d} for d in data]

print(len(data))

# Note: AWS S3 Buckets are not region specific, so the region
# doesn't really matter here

db.create_table('agrifood', data, mode='overwrite')

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
