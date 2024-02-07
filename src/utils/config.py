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
    OPENAI_MODEL: str
    OPENAI_EMBEDDING_MODEL: str
    LANCEDB_DATA_PATH: str


settings = Settings(
    # Comment explaining  why the ignore is needed
    # need it's own noqa because of flake8's line length
    # restrictions :(
    # ignore NOTE: https://github.com/blakeNaccarato/pydantic/blob/c5a29ef77374d4fda85e8f5eb2016951d23dac33/docs/visual_studio_code.md?plain=1#L260-L272 # noqa
    _env_file=os.environ.get('ENV_FILE', '.env'),  # type: ignore
)
