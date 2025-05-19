import yt_dlp
from loguru import logger
from pydantic import BaseModel as Base
from pprint import pprint
from typing import Generator, Any
import re
from src.config import config

class properties:

    @staticmethod
    def metadata_opts():
        ydl_opts = {
            'quiet': True,
            'extract_flat': False,
            'skip_download': True,
            'playlistrandom': False,
            'playlistend': None,
            'writeinfojson': False,
        }

        return ydl_opts

    class metadata(Base):
        extractor: str
        author: list[str] | None
        creators: list[str] | None
        artists: list[str] | None
        album: str | None
        song_title: str | None
        title: str | None
        sanatized_title: str | None
        channel: str | None
        verified: bool | None = False
        url: str = ""


class meta:
    @staticmethod
    def retrieve(url: str, flat: bool = False) -> list[properties.metadata] |  None:
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
        if flat:
            opts.pop("extract_flat")
            opts["extract_flat"] = True

        with yt_dlp.YoutubeDL(opts) as ydl:
            metadata = ydl.extract_info(url, download=False)
            if not type(metadata) == dict:
                return

            try:
                extracted = metadata["entries"]
            except KeyError:
                extracted = [metadata]

            data: list[properties.metadata] = []

            for x in extracted:
                creators=x.get('creators')
                artists=x.get('artists')
                album=x.get('album')
                song_title=x.get('title')
                title=x.get('alt_title')
                channel=x.get('channel')
                verified=x.get('channel_is_verified')
                extractor=x.get('extractor')
                url=str(x.get('webpage_url'))

                if artists != None:
                    author_actual = [str(artists)]
                elif creators != None:
                    author_actual = [str(creators)]
                elif verified != None:
                    author_actual = [str(channel)]
                else:
                    author_actual = None

                if extractor == None:
                    return

                data.append(properties.metadata(
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
                    url=url
                ))
            return data

    @staticmethod
    def sanatize_title(title: str) -> str:
        """
        Cleans and normalizes video titles by matching against known patterns.
        Returns the most probable clean version of the title.
        """

        # Define regex patterns with associated confidence scores
        patterns = [
            {'pattern': r'(?P<artist>.+?)\s*[-–—|]\s*(?P<song>.+?)(?:\s*[\(\[][^\)\]]*(official|lyric|audio)[^\)\]]*[\)\]])?$', 'score': 5},
            {'pattern': r'"(?P<song>[^"]+)"\s*by\s*(?P<artist>.+)$', 'score': 4},
            {'pattern': r'(?P<artist>.+?)\s+[-–—]\s+(?P<song>.+?)(?:\s+\(.*\))?$', 'score': 4},
            {'pattern': r'(?P<song>.+?)\s*(official\s*)?(lyric\s*)?(video|audio|lyrics)\s*[-–—|]\s*(?P<artist>.+)$', 'score': 3},
            {'pattern': r'(watch|listen to)\s*(?P<song>.+?)\s*(by|from)\s*(?P<artist>.+)$', 'score': 2},
            {'pattern': r'(?P<song>.+?)\s*\((live|cover)(@\s*.+?)?\)\s*[-–—]\s*(?P<artist>.+)$', 'score': 3},
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
                candidate = f"{groups['artist'].strip()} - {groups['song'].strip()}"
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

        if getattr(config, "restrictfilenames", False):
            clean_title = re.sub(r'\s+', '-', clean_title)

        return clean_title or title

