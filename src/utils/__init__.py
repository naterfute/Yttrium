from src.database.migrate import migrateDb
from src.downloader import robyn
# from src.utils.hash import hasher

from robyn import Robyn


def initapp(app: Robyn):
  migrateDb()
  # hasher()
  robyn(app)
