from dotenv import load_dotenv
from modules.cafe_post_crawler import CafePostCrawler
from modules.x_post_cralwer import XPostCrawler
from modules.ig_post_crawler import IgPostCrawler
from modules.soop_post_crawler import SoopPostCrawler
from modules.db import DB
import models.models as Models
from utils.cookie_parser import parse_cookie_file
from modules.azure_blob import AzureBlob
from models.x_post import XPost

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

print("testing...")
load_dotenv()

db = DB()
azure_blob = AzureBlob()

# cafe_post_crawler = CafePostCrawler(db, azure_blob)
# cafe_post_crawler.crawl()

# x_post_crawler = XPostCrawler(db)
# # x_post_crawler.crawl_loop()
# x_post_crawler.crawl()

ig_post_crawler = IgPostCrawler(db)
ig_post_crawler.crawl()

# soop_post_cralwer = SoopPostCrawler(db)
# soop_post_cralwer.crawl()