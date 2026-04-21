from __future__ import annotations

import os
from functools import lru_cache
from typing import Any

import boto3

from ruter_chatbot.utility.secrets import secrets


@lru_cache(maxsize=1)
def configure_bedrock_auth() -> None:
    bedrock_token = (
        os.getenv("AWS_BEARER_TOKEN_BEDROCK")
        or os.getenv("AWS_BEDROCK_TOKEN")
        or secrets.get("aws_bedrock_token")
    )
    if bedrock_token:
        os.environ["AWS_BEARER_TOKEN_BEDROCK"] = bedrock_token


@lru_cache(maxsize=None)
def bedrock_runtime(region_name: str | None) -> Any:
    configure_bedrock_auth()
    return boto3.client("bedrock-runtime", region_name=region_name)
