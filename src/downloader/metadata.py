import yt_dlp
from loguru import logger
from pydantic import BaseModel as Base
from pprint import pprint
from typing import Generator, Any
import re

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
        author: list | str | None
        creators: list | None
        artists: list | None
        album: str | None
        song_title: str | None
        title: str | None
        sanatized_title: str | None
        channel: str | None
        verified: bool | None = False


class meta:
    @staticmethod
    def retrieve(url: str, flat: bool = False) -> list[properties.metadata] | Generator[properties.metadata, Any, None] |  None:
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
                #logger.error(x)
                creators=x.get('creators')
                artists=x.get('artists')
                album=x.get('album')
                song_title=x.get('title')
                title=x.get('alt_title')
                channel=x.get('channel')
                verified=x.get('channel_is_verified')
                extractor=x.get('extractor')

                if artists != None:
                    author_actual = artists 
                elif creators != None:
                    author_actual = creators
                elif verified != None:
                    author_actual = channel
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
                    sanatized_title=meta.sanitize_title(str(song_title)),
                    channel=channel,
                    verified=verified
                ))
                logger.error(data)
            return data

    @staticmethod
    def sanitize_title(title: str) -> str:
        """
        Cleans title of videos and ranks them based on regex tags.
        Returns the most likely clean version of the title.
        """
        # Define patterns with their respective scores (higher score = more reliable pattern)
        patterns = [
            # Common patterns (high score)
            {'pattern': r'(?P<artist>.+?)\s*[-–—|]\s*(?P<song>.+?)(?:\s*[\(\[](?:official|lyric|audio).*[\)\]])?$', 'score': 5},
            {'pattern': r'"(?P<song>[^"]+)"\s*by\s*(?P<artist>.+)$', 'score': 4},
            {'pattern': r'(?P<artist>.+?)\s+[-–—]\s+(?P<song>.+?)(?:\s+\(.*\))?$', 'score': 4},

            # Video-specific patterns (medium score)
            {'pattern': r'(?P<song>.+?)\s*(?:official\s*)?(?:lyric\s*)?(?:video|audio|lyrics)\s*[-–—|]\s*(?P<artist>.+)$', 'score': 3},
            {'pattern': r'(?:watch|listen to)\s*(?P<song>.+?)\s*(?:by|from)\s*(?P<artist>.+)$', 'score': 2},

            # Live/cover patterns
            {'pattern': r'(?P<song>.+?)\s*\((?:live|cover)\s*(?:@\s*.+?)?\)\s*[-–—]\s*(?P<artist>.+)$', 'score': 3},

            # Fallback patterns (low score)
            {'pattern': r'(?P<song>.+?)\s*[-–—]\s*(?P<artist>.+?)(?:\s+\(.*\))?$', 'score': 1},
            {'pattern': r'(?P<song>.+)$', 'score': 0},
        ]

        best_match = None
        best_score = -1
        clean_title = title.strip()

        # Try all patterns and keep the highest scoring match
        for entry in patterns:
            match = re.match(entry['pattern'], clean_title, flags=re.IGNORECASE)
            if match:
                groups = match.groupdict()
                current_score = entry['score']

                # If we have both artist and song, format them nicely
                if 'artist' in groups and 'song' in groups:
                    artist = groups['artist'].strip()
                    song = groups['song'].strip()
                    candidate = f"{artist} - {song}"

                    # Prefer this match if it has higher score
                    if current_score > best_score:
                        best_match = candidate
                        best_score = current_score

                # If we only have song, use that
                elif 'song' in groups:
                    candidate = groups['song'].strip()
                    if current_score > best_score:
                        best_match = candidate
                        best_score = current_score

        # Remove common junk from titles
        if best_match:
            clean_title = best_match

        # Additional cleanup regardless of pattern matching
        clean_title = re.sub(r'\s*[\(\[]\s*(?:official\s*)?(?:lyric\s*)?(?:video|audio|lyrics|hd|hq|4k|1080p|720p).*?[\)\]]', '', clean_title, flags=re.IGNORECASE)
        clean_title = re.sub(r'\s*[\(\[]\s*(?:ft\.?|feat\.?|featuring|with)\s*.+?[\)\]]', '', clean_title, flags=re.IGNORECASE)
        clean_title = re.sub(r'\s*[\(\[]\s*(?:live\s*(?:@\s*.+?)?|cover\s*(?:of\s*.+?)?)[\)\]]', '', clean_title, flags=re.IGNORECASE)
        clean_title = re.sub(r'\s*[\(\[]\s*\d{4}\s*[\)\]]', '', clean_title)
        clean_title = re.sub(r'\s*[\(\[]\s*.+\s*[\)\]]', '', clean_title)
        clean_title = re.sub(r'\s*[|]\s*.+$', '', clean_title)
        clean_title = re.sub(r'\s+', ' ', clean_title).strip()
        
        return clean_title if clean_title else title
