import asyncio
import yt_dlp
from munch import munchify
from typing import Optional, Any
from loguru import logger
import sys


from .metadata import meta, properties
from src.config import config
from src.database import interactions
from robyn import Robyn, jsonify





class robyn:
    @classmethod
    def __init__(cls, app: Robyn):
        cls.robyn = app.dependencies.__dict__["global_dependency_map"]

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
        filename = None
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

        def __init__(
            self,
            host: Optional[str] = None,
            download_path: Optional[str] = 'downloads/',
        ):
            self.db = interactions  # type: ignore
            if not host == None:
                self.host = host
                self.download_path = download_path

        def progress_hook(self, d):
            d = munchify(d)

            if d.status == 'error':  # type: ignore
                pass

            if d.status == 'downloading':  # type: ignore
                if not self.StatusStarted:
                    logger.trace(f'Now Downloading "{
                                 d["filename"]}"')  # type: ignore
                    self.StatusStarted = True

                self.Status = 'Downloading'
                self.filename = d['filename']  # type: ignore
                self.percent = d['_percent_str']  # type: ignore
                self.eta = d['_eta_str']  # type: ignore

                try:
                    self.time_elapse = d['elapsed']  # type: ignore
                except Exception:
                    pass

                try:
                    speed = float(d['speed']) # type: ignore
                    self.speed = speed / (1024 * 1024)
                except Exception:
                    pass

                self.buildjson()

            if d.status == 'finished':  # type: ignore
                logger.trace(f'Done Downloading "{
                             d["filename"]}"')  # type: ignore
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
                self.time_elapse=0



            if d.status == 'finished':  # type: ignore
                logger.trace('PostProcessor Hook finished')
                if not self.PostProcessorStarted:
                    loop = asyncio.get_running_loop()
                    asyncio.create_task(self.db.newDownloaded(
                        playlisturl=self.playlist_url,
                        url=self.url,
                        title=self.title,
                        download_path=self.download_path,
                        elapsed=self.time_elapse))

                    self.PostProcessorStarted = True
                self.Status = 'Finished'
                self.buildjson()

        @property
        def ydl_opts(self):

            ydl_opts = {
                'ratelimit': config.ratelimit,  # Kilobytes
                'restrictfilenames': config.restrictfilenames,
                'logger': MyLogger(),
                'breakonexisting': True,
                'progress_hooks': [self.progress_hook],
                'postprocessor_hooks': [self.postprocessor_hooks],
                'writethumbnail': True,
                'skip_broken': True,
                'ignoreerrors': True,
                'extract_flat': False,
                'playlistrandom': False,
                'writeinfojson': False,
                'postprocessors': [
                    {'key': 'FFmpegExtractAudio',
                     'preferredcodec': config.codec,
                     'preferredquality': 'best'},
                    {'add_metadata': 'True', 'key': 'FFmpegMetadata'},
                    {'already_have_thumbnail': False, 'key': 'EmbedThumbnail'}
                ]}

            return ydl_opts

        def startDownload(self, url):
            """Start Download using a url """

            logger.info(f'begin download for {url}')

            metadata = meta.retrieve(url)
            if metadata == None:
                return

            opts = self.ydl_opts

            if metadata.extractor == "youtube":
                pathOpts: str = "%(uploader)s/[%(id)s]"
            else:
                pathOpts: str = "%(playlist_title)s/%(playlist_autonumber)s-[%(id)s]"

            if config.restrictfilenames:
                opts["outtmpl"] = f'downloads/{pathOpts}-%(title)s.%(ext)s'
            else:
                opts["outtmpl"] = f'downloads/{pathOpts} - %(title)s.%(ext)s'

            with yt_dlp.YoutubeDL(opts) as ydl:
                self.playlist_url = url
                ydl.download(url)
                _ = asyncio.get_running_loop()
            asyncio.create_task((self.db.playlistDownloaded(self.playlist_url, str(self.Album))))




        def buildjson(self):
            buildjson: dict = {
                "status": f"{self.Status}",
                "Download Path": f"{self.download_path}",
                "filename": f"{self.filename}",
                "Percent": f"{self.percent}",
                "url": f"{self.url}",
                "Album": f"{self.Album}",
                "Elapsed": f"{self.time_elapse}",
                "Speed": f"{self.speed}",
                "eta": f"{self.eta}"}
            robyn.robyn["downloadinfo"] = buildjson




except Exception as e:
    logger.error(e)
