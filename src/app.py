from robyn import Robyn, Request, Response, jsonify
from robyn.robyn import QueryParams
from robyn.types import PathParams

from datetime import datetime

from loguru import logger
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler


from robyn import __version__ as robynversion
from sqlalchemy import __version__ as alchversion
from alembic import __version__ as alembicversion
from yt_dlp.version import __version__ as ytversion

from src.database import interactions
from src.downloader.metadata import meta
from src.downloader import Downloader
from src.config import config
import src.utils as utils

#logging.basicConfig(level=logging.ERROR)
#logger = logging.getLogger('apscheduler')
#logger.setLevel(logging.ERROR)


apscheduler_logger = logging.getLogger('apscheduler')
apscheduler_logger.setLevel(logging.NOTSET)
handler = logging.StreamHandler()
handler.setLevel(logging.NOTSET) 
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
apscheduler_logger.addHandler(handler)
if not config.debug or config.trace:
    logging.getLogger('apscheduler.executors.default').setLevel(logging.WARNING)

app = Robyn(__file__)

startTime = datetime.now()
app.inject_global(starttime=startTime)

app.inject_global(downloadinfo={"Nothing":"N/A"})
utils.initapp(app)


@app.startup_handler
async def startup_handler():
    try:
        await interactions.connect()
        scheduler = AsyncIOScheduler()

        scheduler.add_job(scanDatabase, 'interval', seconds=5)
        scheduler.start()
    except Exception as e:
        logger.error(e)
        logger.error("Failed to Start")

async def scanDatabase():
    next_item = await interactions.fetchNextItem()
    if next_item is not None:
        manager = Downloader()
        manager.startDownload(next_item.url)


@app.get("/info")
async def get_server_info(global_dependencies):
    """Gets Info about the running server
    eg.  
    version  
    uptime  
    Important lib Versions  
    How many songs have been downloaded
    """
    uptime = datetime.now() - global_dependencies['starttime']
    with open("version") as f:
        version = f.readline()
    return jsonify({
        "app_version": version,
        "uptime": f"{uptime}",
        "DownloadedItems": "WIP",
        "RegisteredUsers": "WIP",
        "versions": {
            "Robyn": robynversion,
            "Yt-DLP": ytversion,
            "SqlAlchemy": alchversion,
            "Alembic": alembicversion,
        },
    })


# TODO: Authentication
@app.get("/downloads/active")
async def downloading_info(global_dependencies):
    """Gets info About the current downloading item"""
    infojson = global_dependencies["downloadinfo"]
    return jsonify(infojson)


# TODO: Authentication
@app.get("/latest/:num")
async def get_latest_downloads(request, path_params: PathParams):
    """Get latest downloaded items
    Gets same number of recent as you provide with num var
    within a 64 bit range
    """
    num: int = int(path_params['num'])
    return jsonify({"message": "WIP: Coming soon, I'm just lazy"})


@app.get("/ping")
async def ping(request):

    with open("version") as f:
        version = f.readline()
    return jsonify(
        {
            "ping": "pong!",
            "version": version,
         }

    )



# TODO: Authentication
@app.post("/download/:url")
async def download(request, path_params: PathParams):
    """Takes a url and downloads the supplied video/song/playlist"""
    url: str = path_params['url']
    metadata = meta.retrieve(url, flat=True)
    if metadata == None:
        return "Failed to Fetch Metadata"
    return await interactions.createEntry(url, metadata[0].extractor)


@app.post("/login")
async def login():
    """Logs the user into the app and supplies them with a jwt"""
    await interactions.newUser("test", "test", "test")

@app.post("/register")
async def register():
    """Register a new user and add them to the database"""
    pass



