from __future__ import annotations

import logging
import os

from openai import OpenAI
from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra='ignore')
    OPENAI_ASSISTANT_NAME: str
    OPENAI_API_KEY: str
    OPENAI_MODEL: str
    OPENAI_EMBEDDING_MODEL: str
    FORCE_RECREATE: bool = False


settings = Settings(
    # Comment explaining  why the ignore is needed
    # need it's own noqa because of flake8's line length
    # restrictions :(
    # ignore NOTE: https://github.com/blakeNaccarato/pydantic/blob/c5a29ef77374d4fda85e8f5eb2016951d23dac33/docs/visual_studio_code.md?plain=1#L260-L272 # noqa
    _env_file=os.environ.get('ENV_FILE', '.env'),  # type: ignore
)


client = OpenAI(api_key=settings.OPENAI_API_KEY)


# Create tools
tools = [
    {
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
    You are the AgriFood Data Lab, a helpful assistant supporting World Bank staff in
    gathering data and extracting insights to support their work. \n
    Instructions: \n
    1. When the user submits a query, ask them if they want to restrict their results to a specific datatype (one of app, project, dataset, microdataset, and youtube_video) or search across datatypes.\n
    2. With the user's query and datatype (if they have selected one), to call the search_knowledge_base function and return the result to the user. If the user has not selected a datatype, omit the parameter in the function call\n
    3. If the user requests more information on a resource, call the appropriate get function and return the results to the user.\n
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
