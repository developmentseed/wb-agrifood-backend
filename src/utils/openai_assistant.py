from __future__ import annotations

import logging

from config import settings
from openai import OpenAI

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


client = OpenAI(api_key=settings.OPENAI_API_KEY)


# Create tools
tools = [
    {
        'type': 'function',
        'function': {
            'name': 'search_knowledge_base',
            'description': "Search for the most relevant data from the Data Lab's knowledge base.",
            'parameters': {
                'type': 'object',
                'properties': {
                    'query': {
                        'type': 'string',
                        'description': "The user's query summarized from the conversation.",
                    },
                    'datatype': {
                        'type': 'string',
                        'description': "The vector type to search (one of: 'app', 'project', 'dataset', 'microdataset' or 'youtube_video').",  # noqa
                    },
                },
                'required': ['query'],
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'get_use_case_details',
            'description': 'Get additional information for a use case.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'use_case_id': {
                        'type': 'string',
                        'description': 'The unique identifier of the World Bank use case.',
                    },
                },
                'required': ['use_case_id'],
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'get_data_details',
            'description': 'Get additional information for a data',
            'parameters': {
                'type': 'object',
                'properties': {
                    'data_unique_id': {
                        'type': 'string',
                        'description': 'Identifies the data',
                    },
                },
                'required': ['data_unique_id'],
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'get_data_file_details',
            'description': 'Get additional information for a data file',
            'parameters': {
                'type': 'object',
                'properties': {
                    'data_file_unique_id': {
                        'type': 'string',
                        'description': 'Identifies the data file',
                    },
                },
                'required': ['data_file_unique_id'],
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'download_data_file',
            'description': 'Download a data file.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'data_file_unique_id': {
                        'type': 'string',
                        'description': 'Identifies the data file',
                    },
                },
                'required': ['data_file_unique_id'],
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'open_data_file',
            'description': 'Open a CSV or Excel data file in json format for data analysis',
            'parameters': {
                'type': 'object',
                'properties': {
                    'data_file_unique_id': {
                        'type': 'string',
                        'description': 'Identifies the data file',
                    },
                },
                'required': ['data_file_unique_id'],
            },
        },
    },
    {'type': 'code_interpreter'},
]

assistants = [
    assistant
    for assistant in client.beta.assistants.list()
    if assistant.name == settings.OPENAI_ASSISTANT_NAME
]

if assistants and settings.FORCE_RECREATE:
    print('Deleting assistant')
    client.beta.assistants.delete(assistants[0].id)
    assistants = []

if not assistants:
    print('Creating assistant')

    client.beta.assistants.create(
        name=settings.OPENAI_ASSISTANT_NAME,
        instructions="""
    Role:\n
    You are the AgriFood Data Lab, a helpful assistant supporting World Bank staff in gathering data and extracting insights to support their work.
    Instructions:
    1. When the user submits a query, ask them if they want to restrict their results to a specific datatype (one of app, project, dataset, microdataset, and youtube_video) or search across datatypes.
    2. If the user has specified a dataype, use the datatype from the following list: app, project, dataset, microdataset and youtube_video, which most closely the user's requested datatype and call the search_knowledge_base function with the user's query and datatype. If the user chooses to search across datatypes, omit the datatype parameter and call the search_knowledge_base function with just the user's query. The result of the function will be a json encoded list of dictionaries. For each result, generate an explanation of why that result is relevant to the user's query, based on the value of the "text_to_embed" key. Add this explanation to the result under a key named "explanation". Return this list to the user as a json encoded list of dictionaries. Important: do not return plain text to the user. Return a json encoded list of dictionaries. Do not include any markdown formatting elements, such as "```json```" and "\\n", or any other additional text)
    3. If the user requests more information on a resource, call the appropriate get function and return the results to the user.
    """,  # noqa
        model='gpt-4-1106-preview',
        tools=tools,  # type: ignore
    )

[assistant] = [
    assistant
    for assistant in client.beta.assistants.list()
    if assistant.name == settings.OPENAI_ASSISTANT_NAME
]

print(assistant)
