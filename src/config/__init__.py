from typing import Optional
from pydantic import BaseModel, ValidationError
import yaml
import sys
from loguru import logger


class DbConfig(BaseModel):
  engine: str
  host: str
  port: int
  db: str
  user: str
  password: str
  timezone: str


class AppConfig(BaseModel):
  host: str
  # port: int
  # username: str
  # password: str
  debug: bool
  trace: bool
  ratelimit: int
  codec: str
  restrictfilenames: bool
  # dbScanRate: int
  db: DbConfig


codec_list: list = ['flac', 'opus', 'mp3', 'aac', 'alac', 'best']


def load_config(file_path: str) -> AppConfig:
  with open(file_path, 'r') as file:
    yaml_data = yaml.safe_load(file)
    try:
      config = AppConfig(**yaml_data)
      if config.codec not in codec_list:
        logger.error(f'Not a supported codec! {config.codec}')
        raise EnvironmentError(f'Not A supported Codec! {config.codec}')
      return config
    except ValidationError as e:
      raise ValueError(f'Invalid configuration: {e}')


file_path = 'config.yaml'

try:
  config = load_config(file_path)
except ValueError as e:
  logger.error(e)
  sys.exit(0)
