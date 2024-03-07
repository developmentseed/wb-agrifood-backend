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
                        'description': "The vector type to search (one of: 'app', 'project', 'dataset', 'microdataset' or 'video').",  # noqa
                    },
                },
                'required': ['query'],
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'format_response',
            'description': 'Formats the response from the search_knowledge_base function and adds an explanation to each result.',  # noqa
            'parameters': {
                'type': 'object',
                'properties': {
                    'knowledge_base_result': {
                        'type': 'array',
                        'description': 'Response from the search_knowledge_base function call',
                        'items': {'type': 'object', 'properties': {}},
                    },
                    'explanations': {
                        'type': 'array',
                        'description': 'List of explanations for each result in the knowledge_base_result list',
                        'items': {'type': 'string'},
                    },
                },
                'required': ['knowldege_base_result', 'explanations'],
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
OPENAI_ASSISTANT_NAME = f'{settings.OPENAI_ASSISTANT_NAME}-{settings.STAGE}'

assistants = [
    assistant
    for assistant in client.beta.assistants.list()
    if assistant.name == OPENAI_ASSISTANT_NAME
]

if assistants and settings.FORCE_RECREATE:
    print('Deleting assistant')
    client.beta.assistants.delete(assistants[0].id)
    assistants = []

if not assistants:
    print('Creating assistant')

    client.beta.assistants.create(
        name=OPENAI_ASSISTANT_NAME,
        instructions="""
    Role:\n
    You are the AgriFood Data Lab, a helpful assistant supporting World Bank staff in gathering data and extracting insights to support their work.
    Instructions:
    1. When the user submits a query, ask them if they want to restrict their results to a specific datatype (one of dataset, project, youtube video, ext paper and usecase) or search across datatypes.
    2. If the user has specified a dataype, use the datatype from the following list: dataset, project, youtube_video, ext_paper, usecase, which most closely matches the user's requested datatype and call the search_knowledge_base function with the user's query and datatype. If the user chooses to search across datatypes, omit the datatype parameter and call the search_knowledge_base function with just the user's query. For each result in the search_knowledge_base function output, generate an explanation of why that result is relevant to the user's query, based on the value of the "text_to_embed" key. Submit these explanations as a list of string, along with the search_knowledge_base function output to the provided format_response function. Return the results of the format_response function to the user. Important: do not modify or add anything to the output of the format_response function. Return it directly to the user as is.
    3. If the user requests more information on a resource, call the appropriate get function and return the results to the user.
    """,  # noqa
        model='gpt-4-1106-preview',
        tools=tools,  # type: ignore
    )

[assistant] = [
    assistant
    for assistant in client.beta.assistants.list()
    if assistant.name == OPENAI_ASSISTANT_NAME
]

print(assistant)
