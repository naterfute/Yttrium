from sys import exception
from sqlalchemy import except_, insert, select, update
import sqlalchemy
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import func as sqlfunc
from sqlalchemy.exc import (
  DuplicateColumnError,
  DBAPIError,
  IntegrityError,
  OperationalError,
)
from urllib.parse import urlparse, parse_qs
from sqlalchemy.ext.asyncio import (
  create_async_engine,
  AsyncSession,
  AsyncEngine,
  async_sessionmaker,
)

from typing import Any, TypedDict
from enum import Enum

from bcrypt import gensalt
import argon2

from loguru import logger


from src.config import config


from src.database.models import Requests, Downloaded, Users, Authors


async def remakeInteraction():
  logger.error('Remaking Interactions')
  interactions()
  await interactions.connect()
  logger.error(interactions.engine)


class DBConn(int, Enum):
  DISCONNECTED = 0
  CONNECTED = 1
  FAILURE = 2


class DBInfo(TypedDict):
  database: str
  driver: str
  port: int


class DBTypes:
  postgresql: DBInfo = {'database': 'postgresql', 'driver': 'asyncpg', 'port': 5432}
  mysql: DBInfo = {'database': 'mysql', 'driver': 'aiomysql', 'port': 3306}
  mariadb: DBInfo = {'database': 'mysql', 'driver': 'aiomysql', 'port': 3306}
  sqlite: DBInfo = {'database': 'sqlite', 'driver': 'aiosqlite', 'port': 0}


class interactions:
  engine: AsyncEngine
  engineType: DBInfo = DBTypes.postgresql
  status: DBConn = DBConn.DISCONNECTED

  username: str = config.db.user
  password: str = config.db.password
  host: str = config.db.host
  port: int = config.db.port
  database: str = config.db.db

  @classmethod
  async def setEnginetype(cls, etype: DBInfo):
    cls.engineType = etype

  @classmethod
  async def setUsername(cls, username) -> None:
    cls.username = username

  @classmethod
  async def setPassword(cls, password) -> None:
    cls.password = password

  @classmethod
  async def setHost(cls, host) -> None:
    cls.host = host

  @classmethod
  async def setPort(cls, port) -> None:
    cls.port = port

  @classmethod
  async def setDatabase(cls, database) -> None:
    cls.database = database

  @classmethod
  async def connect(cls) -> AsyncEngine:
    """
    Connects to the database and persist a connection using a connection pool
    ---
    """
    if cls.port == 0:
      cls.port = cls.engineType['port']
    try:
      if not cls.engineType['database'] == 'sqlite':
        cls.engine = create_async_engine(
          url=f'{cls.engineType["database"]}+{cls.engineType["driver"]}://{cls.username}:{cls.password}@{cls.host}:{cls.port}/{cls.database}',
          pool_size=10,
          max_overflow=10,
          pool_timeout=30,
          echo=True if config.debug is True else False,
          pool_pre_ping=True,
        )

      else:
        cls.engine = create_async_engine(
          url=f'{cls.engineType["database"]}+{cls.engineType["driver"]}:///{cls.database}.sqlite',
          echo=True if config.debug is True else False,
          pool_pre_ping=True,
        )

      cls.AsyncSession = async_sessionmaker(
        cls.engine, class_=AsyncSession, expire_on_commit=False
      )
      cls.status = DBConn.CONNECTED

    except Exception as e:
      logger.error('Failed to connect to the database!')
      logger.error(e)
      cls.status = DBConn.FAILURE
      exit()

    if not isinstance(cls.engine, AsyncEngine):
      logger.error(f'engine Responded with type: {type(cls.engine)}')
      exit()

    return cls.engine

  @classmethod
  async def disconnect(cls) -> int:
    try:
      await cls.engine.dispose()
      cls.status = DBConn.DISCONNECTED
      return 1
    except Exception as e:
      logger.error(e)
      return 0

    @classmethod
    async def reconnect(cls) -> int:
      """
      Disconnects and reconnects to database
      ---
      """

      try:
        if hasattr(cls, 'engine') and cls.engine:
          await cls.engine.dispose()

        await cls.connect()
        return 1
      except Exception as e:
        logger.error(f'Reconnection failed: {e}')
        cls.status = DBConn.FAILURE
        return 0

  @classmethod
  async def checkDuplicates(cls, url: str) -> bool:
    """
    Checks a url against the database to see if it already exists
    ---
    Returns:
      True: If url Exists
      False: if url doesn't exist
    """
    try:
      stmt = select(Requests).where(Requests.url == url)

      async with cls.AsyncSession() as session:
        fetch = await session.execute(stmt)

        if fetch.first() == None:
          await session.close()
          return False
        else:
          await session.close()
          return True

    except Exception:
      return True

  @classmethod
  async def createEntry(
    cls, uri: str, extractor: str
  ) -> dict[str, dict[str, str]] | None:
    """
    Creates a new entry in the requests table to download once it's called in queue
    ---
    """
    try:
      async with cls.AsyncSession() as session:
        new_entry = Requests(url=uri, extractor=extractor)
        session.add(new_entry)
        await session.commit()
        logger.trace(f'New Request with ID: {new_entry.id}')

        return {
          'data': {
            'message': f'New request with ID: {new_entry.id} has been created',
          }
        }
    except DuplicateColumnError as e:
      logger.debug(e)
      return {
        'data': {'message': f'Duplicate Entry. Link already exists', 'error': '3000'}
      }
    except IntegrityError as e:
      logger.debug(e)
      return {
        'data': {'message': f'Duplicate Entry. Link already exists', 'error': '3000'}
      }

  @classmethod
  async def fetchNextItem(cls) -> Requests | None:
    """
    Fetches next eligible item for download from the database
    ---
    """

    query = (
      select(Requests)
      .where(Requests.queue_status == 'queued')
      .order_by(Requests.id.asc())
      .limit(1)
    )
    try:
      async with cls.AsyncSession() as session:
        result = await session.execute(query)
        item: Requests = result.scalar_one_or_none()
        if item == None:
          return
        logger.debug(f"""
                             result: {result.__dict__}
                             item: {item}
                """)

        if isinstance(item, Requests):
          logger.trace(item)
          return item
        else:
          return None

    except Exception as e:
      # logger.debug(f'Failed to fetch next item {e}')
      return None

  @classmethod
  async def newDownloaded(
    cls, playlisturl: Any, url: Any, title: Any, download_path: Any, elapsed: Any
  ) -> None:
    """
    Creates a new entry in the Downloaded Table
    and marks it downloaded with all relevent info
    ---
    """
    try:
      logger.trace(f'Marking video: {url} as downloaded')
      async with cls.AsyncSession() as session:
        newItem = Downloaded(
          playlist_url=playlisturl,
          url=url,
          title=title,
          path=download_path,
          elapsed=str(elapsed),
        )
        session.add(newItem)
        await session.commit()
        logger.trace(f'New Download with ID: {newItem.id}')

    except Exception as e:
      logger.error(e)

  @classmethod
  async def playlistDownloaded(
    cls,
    url: str,
    name: str,
  ) -> None:
    """
    Takes a playlist id and set's it's status to completed in the db
    ---
    """
    logger.trace(f'Marking playlist: {url} downloaded')
    try:
      query = (
        update(Requests)
        .where(Requests.url == url)
        .values(title=name, download_time=sqlfunc.now(), queue_status='completed')
      )
      async with cls.AsyncSession() as session:
        await session.execute(query)

        await session.commit()

    except Exception as e:
      logger.error(e)

  @classmethod
  async def newUser(cls, username: str, hash: str, salt: str) -> int:
    """
    Creates a new entry in the database for a new user
    ---
    """
    try:
      async with cls.AsyncSession() as session:
        newUser = Users(username=username, password=hash, salt=salt)
        session.add(newUser)
        await session.commit()
        logger.trace(f'New User with username of: {username}')
        return 1
    except Exception as e:
      logger.error(e)
      return 0

  @classmethod
  async def fetchUser(cls, username: str) -> Users | None:
    """
    Fetches a user from the database
    ---
    """

    query = select(Users).where(Users.username == username).limit(1)

    try:
      async with cls.AsyncSession() as session:
        result = await session.execute(query)
        user: Users = result.scalar_one_or_none()

        if result == None:
          return None
        else:
          return user

    except Exception as e:
      print(e)
      return

  @classmethod
  async def verifyUser(cls, username, password) -> Users | None:
    """
    Verify A username and hash against it in the database
    ---
    """
    user = await cls.fetchUser(username)
    if user is None:
      return
    return user

  @classmethod
  async def newAuthor(cls, author_name) -> int:
    """
    Adds a new author to the database for future reference
    ---
    """
    try:
      async with cls.AsyncSession() as session:
        newAuthor = Authors(author=author_name)
        session.add(newAuthor)
        await session.commit()
        logger.trace(f'New User with username of: {author_name}')
        return 1

    except Exception as e:
      logger.error(e)
      return 0

  @classmethod
  async def deleteAuthor(cls, author_name) -> None:
    """
    Deletes specified author from the database in a cascade delete
    ---
    """
    pass

  @classmethod
  async def fetchAuthor(cls, author_name) -> Authors | None:
    """
    Searches database for reference to this author
    ---
    """

    query = select(Authors).where(Authors.author == author_name).limit(1)
    try:
      async with cls.AsyncSession() as session:
        result = await session.execute(query)
        item: Requests = result.scalar_one_or_none()

        logger.debug(f"""
                             result: {result.__dict__}
                             item: {item}
                """)

        if isinstance(item, Authors):
          logger.debug(item)
          return item
        elif item == None:
          return None

    except Exception as e:
      logger.error(f'Error occured when fetching an Author: {e}')
      return None
