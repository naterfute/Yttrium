import yt_dlp
from loguru import logger
from pydantic import BaseModel as Base
import re
from src.config import config


class properties:
  @staticmethod
  def metadata_opts():
    ydl_opts = {
      # 'quiet': True,
      'extract_flat': False,
      'cookiefile': 'cookies.txt',
      'skip_download': True,
      'skip_broken': True,
      'ignoreerrors': True,
      'playlistrandom': False,
      'playlistend': None,
      'writeinfojson': False,
    }

    return ydl_opts

  class metadata(Base):
    extractor: str | None
    author: str | None
    creators: list[str] | None
    artists: list[str] | None
    album: str | None
    song_title: str | None
    title: str | None
    sanatized_title: str | None
    channel: str | None
    verified: bool | None = False
    url: str = ''


class meta:
  @staticmethod
  def retrieve(url: str, flat: bool = False) -> list[properties.metadata] | None:
    """
    Retrieves metadata for the specified url such as
    ---
    Extractor
    Album
    Artists
    Title
    ---
    """
    opts = properties.metadata_opts()

    with yt_dlp.YoutubeDL(opts) as ydl:  # type: ignore
      metadata = ydl.extract_info(url, download=False)
      if type(metadata) is not dict:
        return

      try:
        extracted = metadata['entries']
      except KeyError:
        extracted = [metadata]

      data: list[properties.metadata] = []

      for x in extracted:
        try:
          creators = x.get('creators')
          artists = x.get('artists')
          album = x.get('album')
          song_title = x.get('title')
          title = x.get('alt_title')
          channel = x.get('channel')
          verified = x.get('channel_is_verified')
          extractor = x.get('extractor')
          url = str(x.get('webpage_url'))

          if artists != None:
            author_actual = str(artists)[2:-2]
          elif creators != None:
            author_actual = str(creators)[2:-2]
          elif verified != None:
            author_actual = str(channel)[2:-2]
          else:
            author_actual = None

          if extractor == None:
            return

          newMeta = properties.metadata(
            extractor=extractor,
            author=author_actual,
            creators=creators,
            artists=artists,
            album=album,
            song_title=song_title,
            title=title,
            sanatized_title=meta.sanatize_title(str(song_title)),
            channel=channel,
            verified=verified,
            url=url,
          )

          logger.debug(newMeta)

          data.append(newMeta)
        except Exception as e:
          logger.error(e)

      return data

  @staticmethod
  def sanatize_author(author: str | None) -> str:
    if author is None:
      return 'NA'

    patterns = [
      # Common channel name patterns
      {
        'pattern': r'(?P<artist>.+?)\s*(?:[-–—|]\s*Topic)$',
        'score': 5,
      },  # YouTube auto-generated channels
      {'pattern': r'(?P<artist>.+?)\s*(?:[-–—|]\s*VEVO)$', 'score': 5},  # VEVO channels
      {
        'pattern': r'(?P<artist>.+?)\s*(?:[-–—|]\s*Official)$',
        'score': 4,
      },  # Official channels
      {
        'pattern': r'(?P<artist>.+?)\s*(?:[-–—|]\s*(?:Channel|Music))$',
        'score': 3,
      },  # Generic music channels
      # Social media tags
      {
        'pattern': r'(?P<artist>.+?)\s*(?:[@#]\w+|(?:fb|ig|twitter|tiktok)[\./]\w+)$',
        'score': 4,
      },
      # Copyright/record label info
      {'pattern': r'(?P<artist>.+?)\s*(?:©|℗|®|™|\[.*label.*\])', 'score': 3},
      # Website URLs
      {'pattern': r'(?P<artist>.+?)\s*(?:https?://\S+|www\.\S+\.\w+)', 'score': 4},
    ]

    clean_author = author.strip()
    best_candidate = None
    best_score = -1

    # Match against patterns
    for entry in patterns:
      match = re.match(entry['pattern'], clean_author, flags=re.IGNORECASE)
      if not match:
        continue

      groups = match.groupdict()
      score = entry['score']

      if 'artist' in groups and 'song' in groups:
        candidate = f'{groups["artist"].strip()} - {groups["song"].strip()}'
      else:
        candidate = groups.get('song', '').strip()

      if score > best_score:
        best_candidate = candidate
        best_score = score

    if best_candidate:
      clean_title = best_candidate

    # Post-processing: remove junk like "(Official Video)", resolutions, etc.
    junk_patterns = [
      r'\s*[\(\[][^\)\]]*(official|channel|vevo|topic|music|page|account|profile|artist)[^\)\]]*[\)\]]',
      r'\s*[\(\[]\s*(subscribe|follow|like|share)[^\)\]]*[\)\]]',
      r'\s*[\(\[]\s*(C|℗|©|®|™)\s*[^\)\]]*[\)\]]',  # Copyright symbols
      r'\s*[\(\[]\s*\d{1,2}[-/]\d{1,2}[-/]\d{2,4}[\)\]]',  # Dates
      r'\s*[\(\[]\s*\d+\s*(?:subscribers|followers|views|likes)[\)\]]',
      r'\s*[\(\[]\s*(verified|unverified)[\)\]]',
      r'\s*[\(\[]\s*(original|cover|remix|tribute)[\)\]]',
      r'\s*[\(\[]\s*[^\)\]]*label[^\)\]]*[\)\]]',
      r'\s*[\(\[]\s*[^\)\]]*records?[^\)\]]*[\)\]]',
      r'\s*[\(\[]\s*[^\)\]]*entertainment[^\)\]]*[\)\]]',
      r'\s*[\(\[]\s*[^\)\]]*production[^\)\]]*[\)\]]',
      r'\s*[\(\[]\s*[^\)\]]*studios?[^\)\]]*[\)\]]',
      r'\s*[\(\[]\s*[^\)\]]*presents[^\)\]]*[\)\]]',
      r'\/',
    ]

    for pattern in junk_patterns:
      clean_author = re.sub(pattern, '', clean_author, flags=re.IGNORECASE)

    clean_author = re.sub(r'\s+', ' ', clean_author).strip()

    if getattr(config, 'restrictfilenames', False):
      clean_author = re.sub(r'\s+', '-', clean_author)

    return clean_author or author

  @staticmethod
  def sanatize_title(title: str) -> str:
    """
    Cleans and normalizes video titles by matching against known patterns.
    Returns the most probable clean version of the title.
    """

    # Define regex patterns with associated confidence scores
    patterns = [
      {
        'pattern': r'(?P<artist>.+?)\s*[-–—|]\s*(?P<song>.+?)(?:\s*[\(\[][^\)\]]*(official|lyric|audio)[^\)\]]*[\)\]])?$',
        'score': 5,
      },
      {'pattern': r'"(?P<song>[^"]+)"\s*by\s*(?P<artist>.+)$', 'score': 4},
      {
        'pattern': r'(?P<artist>.+?)\s+[-–—]\s+(?P<song>.+?)(?:\s+\(.*\))?$',
        'score': 4,
      },
      {
        'pattern': r'(?P<song>.+?)\s*(official\s*)?(lyric\s*)?(video|audio|lyrics)\s*[-–—|]\s*(?P<artist>.+)$',
        'score': 3,
      },
      {
        'pattern': r'(watch|listen to)\s*(?P<song>.+?)\s*(by|from)\s*(?P<artist>.+)$',
        'score': 2,
      },
      {
        'pattern': r'(?P<song>.+?)\s*\((live|cover)(@\s*.+?)?\)\s*[-–—]\s*(?P<artist>.+)$',
        'score': 3,
      },
      {'pattern': r'(?P<song>.+?)\s*[-–—]\s*(?P<artist>.+?)(\s+\(.*\))?$', 'score': 1},
      {'pattern': r'(?P<song>.+)$', 'score': 0},
    ]

    clean_title = title.strip()
    best_candidate = None
    best_score = -1

    # Match against patterns
    for entry in patterns:
      match = re.match(entry['pattern'], clean_title, flags=re.IGNORECASE)
      if not match:
        continue

      groups = match.groupdict()
      score = entry['score']

      if 'artist' in groups and 'song' in groups:
        candidate = f'{groups["artist"].strip()} - {groups["song"].strip()}'
      else:
        candidate = groups.get('song', '').strip()

      if score > best_score:
        best_candidate = candidate
        best_score = score

    if best_candidate:
      clean_title = best_candidate

    # Post-processing: remove junk like "(Official Video)", resolutions, etc.
    junk_patterns = [
      r'\s*[\(\[][^\)\]]*(official\s*)?(lyric\s*)?(video|audio|lyrics|hd|hq|4k|1080p|720p)[^\)\]]*[\)\]]',
      r'\s*[\(\[]\s*(ft\.?|feat\.?|featuring|with)\s+.+?[\)\]]',
      r'\s*[\(\[]\s*(live|cover)(@\s*.+?)?[\)\]]',
      r'\s*[\(\[]\s*\d{4}\s*[\)\]]',
      r'\s*[\(\[][^\)\]]+[\)\]]',
      r'\s*[|].*$',
    ]

    for pattern in junk_patterns:
      clean_title = re.sub(pattern, '', clean_title, flags=re.IGNORECASE)

    clean_title = re.sub(r'\s+', ' ', clean_title).strip()

    if getattr(config, 'restrictfilenames', False):
      clean_title = re.sub(r'\s+', '-', clean_title)

    return clean_title or title

  @staticmethod
  def normalize_authors(meta: list[properties.metadata]) -> str | None:
    """
    Attempts to find a consistent author name across all items in the playlist metadata.

    Iterates through the given metadata and compares author/album fields to identify a common or
    dominant author name. If a sufficiently consistent match is found, returns that author name.
    Otherwise, returns None.

    ---
    Args:
        meta (list[properties.metadata]): Metadata list containing author/album information for a playlist.
    Returns:
        str | None: The normalized author name if a consistent match is found; otherwise, None.
    ---
    """
    artists: dict[str, int] = {}
    albums: dict[str, int] = {}

    for song in meta:
      print(song.author)
