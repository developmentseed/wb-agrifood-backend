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
                        'description': 'The data type to search for',
                        'enum': [
                            'dataset',
                            'project',
                            'video',
                            'paper',
                            'usecase',
                        ],
                    },
                },
                'required': ['query'],
            },
        },
    },
    # {
    #     "type": "function",
    #     "function": {
    #         "name": "format_response",
    #         "description": "Formats the response from the search_knowledge_base function and adds an explanation to each result.",  # noqa
    #         "parameters": {
    #             "type": "object",
    #             "properties": {
    #                 "knowledge_base_result": {
    #                     "type": "array",
    #                     "description": "Response from the search_knowledge_base function call",
    #                     "items": {"type": "object", "properties": {}},
    #                 },
    #                 "explanations": {
    #                     "type": "array",
    #                     "description": "List of explanations for each result in the knowledge_base_result list",
    #                     "items": {"type": "string"},
    #                 },
    #             },
    #             "required": ["knowldege_base_result", "explanations"],
    #         },
    #     },
    # },
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
    1. When the user submits a query, ask them if they want to restrict their results to one of the following datatypes: [datset, project, youtube video, external paper, usecase] or if they would like to search across datatypes. If the user chooses a dataype, find the datatype from the following list: ["dataset", "project", "video", "paper", "usecase"] which most closely matches the user's requested datatype and call the search_knowledge_base function with the user's query and datatype. If the user chooses to search across datatypes, omit the datatype parameter and call the search_knowledge_base function with just the user's query. Response format instructions: The response must be a single JSON array, with 5 objects, each with the following attributes ["_distance", "id", "type", "title", "description", "summary", "url", "link"]. IMPORTANT: Do NOT ADD ANY TEXT OR CHARACTERS OUTSIDE OF THE JSON STRING.
    2. If the user requests more information one of the resources from the output of the search_knowledge_base function, call the appropriate get_ function with the provided resource id and return the results to the user.
    """,  # noqa
        model='gpt-4-turbo-preview',
        tools=tools,  # type: ignore
    )

[assistant] = [
    assistant
    for assistant in client.beta.assistants.list()
    if assistant.name == OPENAI_ASSISTANT_NAME
]

print(assistant)
