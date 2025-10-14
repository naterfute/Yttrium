import asyncio
import yt_dlp
from munch import munchify
from typing import Generator, Optional, Any
from loguru import logger
import sys
from enum import Enum

import musicbrainzngs
import functools

from .metadata import meta, properties
from src.config import config
from src.database import interactions
from robyn import Robyn, jsonify


unkown_artist = 'unknown_artist'
unknown_album = 'unknown_album'


class shared_data(int, Enum):
  UNKNOWN = 0  # NOTE: I can't find any sort of corolation or it's so bad it errored out
  SOLO = 1  # NOTE: Each item is it's own serpate thing. probably a playlist
  SHARED_COMPLETE = 2  # NOTE: All Data eg; Albums and Artists shared
  SHARED_AUTHORS = (
    3  # NOTE: Shared authors eg; Only artists are shared between them all
  )
  SHARED_ALBUMS = (
    4  # NOTE: Shared Albums eg; Only album names are shared between them all
  )

  NO_SHARED_ALBUMS = (
    5  # NOTE: No Shared Albums eg; some may have the same album but not all
  )


class robyn:
  @classmethod
  def __init__(cls, app: Robyn):
    cls.robyn = app.dependencies.__dict__['global_dependency_map']
    musicbrainzngs.set_useragent(
      'Yttrium-Music-Downloader',
      cls.robyn['version'],
      'https://github.com/naterfute/Yttrium',
    )


try:

  def debug_init(trace, debug):
    logger.remove()
    if debug:
      logger.add(sys.stderr, level='DEBUG')
    elif trace:
      logger.add(sys.stderr, level='TRACE')
    else:
      logger.add(sys.stderr, level='INFO')
      pass
    pass

  debug_init(config.trace, config.debug)

  class MyLogger:
    def debug(self, msg):
      # For compatibility with youtube-dl, both debug and info are passed into debug
      # You can distinguish them by the prefix '[debug] '
      if msg.startswith('[debug] '):
        logger.debug(msg)
      else:
        self.info(msg)

    def info(self, msg):
      pass

    def warning(self, msg):
      pass

    def error(self, msg):
      print(msg)
      pass

  class Downloader:
    wait = False
    StatusStarted = False
    Started = False
    host = None
    port = None
    download_path = None
    Status = None
    filename = ''
    time_elapse = None
    percent = None
    eta = None
    url = None
    title = None
    playlist_url = None
    PostProcessorStarted = None
    Album = None
    downloading = False
    speed = None
    sanatized_title = ''

    def __init__(
      self,
      host: Optional[str] = None,
      download_path: Optional[str] = 'downloads/',
    ):
      self.db = interactions
      if not host == None:
        self.host = host
        self.download_path = download_path

    def progress_hook(self, d):
      d = munchify(d)

      if d.status == 'error':  # type: ignore
        pass

      if d.status == 'downloading':  # type: ignore
        if not self.StatusStarted:
          logger.trace(f'Now Downloading "{d["filename"]}"')  # type: ignore
          self.StatusStarted = True

        self.Status = 'Downloading'
        self.filename: str = d['filename']  # type: ignore
        self.percent = d['_percent_str']  # type: ignore
        self.eta = d['_eta_str']  # type: ignore

        try:
          self.time_elapse = d['elapsed']  # type: ignore
        except Exception:
          pass

        try:
          speed = float(d['speed'])  # type: ignore
          self.speed = speed / (1024 * 1024)
        except Exception:
          pass

        self.buildjson()

      if d.status == 'finished':  # type: ignore
        logger.trace(f'Done Downloading "{d["filename"]}"')  # type: ignore
        self.StatusStarted = False  # type: ignore
        self.filename = d['filename']  # type: ignore

        try:
          self.time_elapse = d['elapsed']  # type: ignore
        except:
          pass

        self.PostProcessorStarted = False
        self.buildjson()

    def postprocessor_hooks(self, d):
      d = munchify(d)
      if d.status == 'started':  # type: ignore
        info = munchify(d['info_dict'])  # type: ignore
        self.Album = info.album  # type: ignore
        self.url = info.webpage_url  # type: ignore
        self.title = info.title  # type: ignore
        self.download_path = info.filepath  # type: ignore
        self.Status = 'Started'
        self.time_elapse = 0

      if d.status == 'finished':  # type: ignore
        logger.trace('PostProcessor Hook finished')
        if not self.PostProcessorStarted:
          loop = asyncio.get_running_loop()
          result = asyncio.create_task(
            self.db.newDownloaded(
              playlisturl=self.playlist_url,
              url=self.url,
              title=self.title,
              download_path=self.download_path,
              elapsed=self.time_elapse,
            )
          )

          self.PostProcessorStarted = True
          self.Status = 'Finished'

        self.buildjson()

    @property
    def ydl_opts(self):
      ydl_opts = {
        'ratelimit': config.ratelimit,  # Kilobytes
        'verbose': True if config.debug is True else False,
        'cookiefile': 'cookies.txt',
        'restrictfilenames': config.restrictfilenames,
        'logger': MyLogger(),
        'breakonexisting': True,
        'progress_hooks': [self.progress_hook],
        'postprocessor_hooks': [self.postprocessor_hooks],
        'abortonerror': False,
        'writethumbnail': True,
        'skip_broken': True,
        'ignoreerrors': True,
        'extract_flat': False,
        'playlistrandom': False,
        'writeinfojson': False,
        'keepvideo': False,
        'postprocessors': [
          {
            'key': 'FFmpegExtractAudio',
            'preferredcodec': config.codec,
            'preferredquality': 'best',
          },
          {'add_metadata': 'True', 'key': 'FFmpegMetadata'},
          {'already_have_thumbnail': False, 'key': 'EmbedThumbnail'},
        ],
      }

      return ydl_opts

    def stringifyAuthors(self, authors: list):
      returnauthors: str = ''
      for author in authors[:-1]:
        returnauthors += f'{author} '
      returnauthors += f'{authors[-1]}'

    def normifyMetadata(self, metadata: list[properties.metadata]) -> shared_data:
      """
      detects common data through-out all items got through metadata
      """
      known_authors: dict[str, list[str]] = {}
      unknown_authors: dict[str, list[str]] = {}
      known_albums: dict[str, int] = {}

      albumMatch: bool = True

      for item in metadata:
        if item.author is not None:
          for loc, value in enumerate(item.author):
            author_exists = musicbrainzngs.search_artists(query=value)
            sys.exit()

            known_authors[f'{loc}'].append(value)

        if item.album is not None:
          if known_albums.get(item.album) is None:
            known_albums[item.album] = len(known_albums) + 1
          else:
            known_albums[item.album] += 1

      return shared_data.UNKNOWN

    def matchAuthors(self, metadata: list[properties.metadata]) -> bool:
      known_albums: dict[str, int] = {}
      print(metadata)
      for item in metadata:
        if item.album is not None:
          if known_albums.get(item.album) is None:
            known_albums[item.album] = 1
          else:
            known_albums[item.album] += 1

      if not len(known_albums) > 1:
        return True
      else:
        return False

    async def startDownload(self, url: str):
      """Start Download using a url"""

      logger.info(f'begin download for {url}')

      logger.trace('retrieving metadata')
      metadata = meta.retrieve(url)

      if type(metadata) == None:
        logger.trace('metadata is None, returning')
        return
      elif metadata == []:
        logger.trace('metadata is Empty, returning')
        return

      elif type(metadata) == list:
        pass

      else:
        logger.error('Returning')
        logger.error(type(metadata))
        logger.error(metadata)
        return

      opts = self.ydl_opts

      logger.trace('Getting Metadata')

      # author_match = self.matchAuthors(metadata)

      for data in metadata:
        logger.debug(data)
        if data.author is not None:
          author = meta.sanatize_author(data.author)
        else:
          author = meta.sanatize_author(data.author)

        if data.extractor == 'youtube' and data.author and data.album == None:
          # NOTE: Single Video Authored, No Album
          pathOpts: str = f'{author}/{data.sanatized_title}'
          logger.trace(pathOpts)
          logger.trace(1)

        elif data.extractor == 'youtube' and data.author and data.album:
          # NOTE: Single Video Authored, With Album
          pathOpts: str = f'{author}/{data.album}/'
          logger.trace(pathOpts)
          logger.trace('Author with Album')

        elif (
          data.extractor == 'youtube:playlist'
          and data.author
          and data.album is not None
        ):
          # NOTE: Playlist, No Album, with Artist
          pathOpts: str = f'{author}/{unknown_album}/'
          logger.trace(pathOpts)
          logger.trace(3)

        elif data.extractor == 'youtube:playlist' and data.author:
          # NOTE: Playlist, With Album
          pathOpts: str = f'{author}/{data.album}/'
          logger.trace(pathOpts)
          logger.trace(4)

        elif (
          data.extractor == 'youtube:playlist' and data.album and data.author == None
        ):
          # NOTE: Playlist, no Author with Album(shouldn't be possible?)
          pathOpts: str = f'{unkown_artist}/{data.album}/'
          logger.trace(pathOpts)
          logger.trace(5)

        # WARN: These are only last resort. These paths will make it extremly hard for apps such as plex/jellyfin
        # to correctly index your library

        else:
          pathOpts: str = f'{unkown_artist}/{unknown_album}/'
          logger.trace(6)

        pathOpts = pathOpts.replace(' ', '-')

        self.playlist_url = url
        index = 0
        for x in metadata:
          if config.restrictfilenames:
            opts['outtmpl'] = (
              f'downloads/{pathOpts}{index}--[%(id)s]--{x.sanatized_title}.%(ext)s'
            )
          else:
            opts['outtmpl'] = f'downloads/{pathOpts}{index} {x.sanatized_title}.%(ext)s'
          with yt_dlp.YoutubeDL(opts) as ydl:  # type: ignore
            ydl.download(x.url)
          index += 1
          if index == len(metadata):
            break
        await self.db.playlistDownloaded(self.playlist_url, str(self.Album))

    def buildjson(self):
      buildjson: dict = {
        'status': f'{self.Status}',
        'Download Path': f'{self.download_path}',
        'filename': f'{self.filename}',
        'Percent': f'{self.percent}',
        'url': f'{self.url}',
        'Album': f'{self.Album}',
        'Elapsed': f'{self.time_elapse}',
        'Speed': f'{self.speed}',
        'eta': f'{self.eta}',
      }
      robyn.robyn['downloadinfo'] = buildjson

except Exception as e:
  logger.error(e)
