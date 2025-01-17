from dotenv import load_dotenv
from modules.cafe_post_crawler import CafePostCrawler
from modules.db import DB
import models.models as Models
from utils.cookie_parser import parse_cookie_file

if __name__ == "__main__":
    load_dotenv()
    db = DB()

def init(db):
    db.session.add(Models.Streamer(name="woowakgood"))
    db.session.add(Models.Streamer(name="ine"))
    db.session.add(Models.Streamer(name="jingburger"))
    db.session.add(Models.Streamer(name="lilpa"))
    db.session.add(Models.Streamer(name="jururu"))
    db.session.add(Models.Streamer(name="gosegu"))
    db.session.add(Models.Streamer(name="viichan"))
    db.session.commit()
    db.session.close()    