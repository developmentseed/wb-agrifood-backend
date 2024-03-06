from __future__ import annotations

import os

from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra='ignore')
    VPC_ID: str = ''
    STAGE: str
    OWNER: str
    OPENAI_ASSISTANT_NAME: str
    OPENAI_API_KEY: str
    OPENAI_EMBEDDING_MODEL: str
    LANCEDB_DATA_PATH: str
    FORCE_RECREATE: bool = False


settings = Settings(
    # Note: any existing environment variables will take precedence
    # over values in the .env file (ref: https://docs.pydantic.dev/latest/concepts/pydantic_settings/#dotenv-env-support) # noqa
    # The following comment, which explains  why the ignore is needed needs it's own
    # noqa because of flake8's line lengthrestrictions :(
    # ignore NOTE: https://github.com/blakeNaccarato/pydantic/blob/c5a29ef77374d4fda85e8f5eb2016951d23dac33/docs/visual_studio_code.md?plain=1#L260-L272 # noqa
    _env_file=os.environ.get('ENV_FILE', '.env'),  # type: ignore
)
