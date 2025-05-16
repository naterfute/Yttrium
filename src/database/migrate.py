from src.config import config
from src.database import DBTypes

from alembic.config import Config
from alembic import command

from loguru import logger


def migrateDb(
    engine: str = config.db.engine.lower(),
    username: str | None = config.db.user,
    password: str | None = config.db.password,
    host: str | None = config.db.host,
    port: int | None = None,
    database: str = config.db.db
) -> int:
    alembic_cfg = Config()
    alembic_cfg.set_main_option("script_location", "src/database/alembic")
    alembic_cfg.set_main_option("prepend_sys_path", ".")
    engineType = getattr(DBTypes, str(engine), None)
    logger.debug(engineType)
    if engineType is None:
        logger.error(f"The Database \"{engine}\" is not compatible with this app")
        return 0

    if port is None:
        port = engineType["port"]
    if not engineType['database'] in ["sqlite", "mysql", "mariadb"]:
        alembic_cfg.set_main_option("sqlalchemy.url", f'{engineType["database"]}://{username}:{password}@{host}:{port}/{database}')
    elif engineType['database'] not in ["postgres", "sqlite"]:
        alembic_cfg.set_main_option("sqlalchemy.url", f'{engineType["database"]}+pymysql://{username}:{password}@{host}:{port}/{database}')
    elif engineType['database'] in ['sqlite']:
        alembic_cfg.set_main_option("sqlalchemy.url", f'{engineType["database"]}:///{database}.sqlite')
    else:
        logger.error(f"Incorrect database type {engineType}")
    logger.debug(alembic_cfg.get_main_option("sqlalchemy.url"))

    try:
        command.ensure_version(alembic_cfg)
        command.upgrade(alembic_cfg, "head")
        return 1
    except Exception as e:
        logger.error(e)
        exit(0)

