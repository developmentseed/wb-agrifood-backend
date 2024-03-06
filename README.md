# World Bank Agrifood API

## Installation

```
poetry install
```

## Running

Copy `.env.example` to `.env` and set your OpenAI API Key and your preferred model.

```
uvicorn main:app --reload
```

## API Docs

The API docs is available at http://localhost:8000/docs.

## Deployment

```
nvm use 18
npm install -g aws-cdk
ENV_FILE=.env.dev cdk deploy
```
(Specify `ENV_FILE` if using an env file other than `.env`, such as `.env.dev`)
