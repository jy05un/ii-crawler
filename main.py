from dotenv import load_dotenv
from modules.cafe_post_crawler import CafePostCrawler
from modules.x_post_cralwer import XPostCrawler
from modules.ig_post_crawler import IgPostCrawler
from modules.soop_post_crawler import SoopPostCrawler
from modules.db import DB
from modules.azure_blob import AzureBlob
from models.streamer import Streamer
from threading import Thread
from sqlalchemy import select
from init import init

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

if __name__ == "__main__":
    print("testing...")
    load_dotenv()

    db = DB()
    azure_blob = AzureBlob()
    
    stmt = select(Streamer)
    streamers = db.session.execute(stmt).scalars()
    if len(list(streamers)) != 7:
        print("[INIT] initializing streamer information")
        init(db)
    
    
    cafe_post_crawler = CafePostCrawler(db, azure_blob)
    x_post_crawler = XPostCrawler(db)
    ig_post_crawler = IgPostCrawler(db, azure_blob)
    soop_post_cralwer = SoopPostCrawler(db)
    
    th_cafe = Thread(target=cafe_post_crawler.crawl_loop)
    th_x = Thread(target=x_post_crawler.crawl_loop, args=(True, ))
    th_soop = Thread(target=soop_post_cralwer.crawl_loop)
    th_ig = Thread(target=ig_post_crawler.crawl_loop)
    
    th_cafe.start()
    th_x.start()
    th_soop.start()
    th_ig.start()
    
    th_cafe.join()
    th_x.join()
    th_soop.join()
    th_ig.join()