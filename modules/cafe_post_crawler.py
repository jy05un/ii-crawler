from modules.base_crawler import BaseCrawler
import os
from requests import Session
from bs4 import BeautifulSoup
from utils.cookie_parser import parse_cookie_file
import json
from sqlalchemy import select, update
from models.cafe_post import CafePost
from models.streamer import Streamer
from models.file import File, FileType
from models.post import Post, PostType
from datetime import datetime
import time
import random
import uuid

original_print = print
def print(content):
    original_print("\t[CafeCrawler]: ", end="")
    original_print(content)

class CafePostCrawler(BaseCrawler):
        
    def __init__(self, db, azure_blob):
        super().__init__(db)
        self.azure_blob = azure_blob
        self.ids = {}
        self.ids["woowakgood"] = os.getenv("CAFE_WOOWAKGOOD_ID")
        self.ids["ine"] = os.getenv("CAFE_INE_ID")
        self.ids["jingburger"] = os.getenv("CAFE_JINGBURGER_ID")
        self.ids["lilpa"] = os.getenv("CAFE_LILPA_ID")
        self.ids["jururu"] = os.getenv("CAFE_JURURU_ID")
        self.ids["gosegu"] = os.getenv("CAFE_GOSEGU_ID")
        self.ids["viichan"] = os.getenv("CAFE_VIICHAN_ID")
        self.names = ["woowakgood", "ine", "jingburger", "lilpa", "jururu", "gosegu", "viichan"]
        
        self.board_api = lambda cafe_id : os.getenv("CAFE_BOARD_API").replace("{cafe_id}", cafe_id)
        self.post_api = lambda post_id : os.getenv("CAFE_POST_API").replace("{post_id}", post_id)
        
        self.session = Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Origin": "https://cafe.naver.com"
        })
        
        cookie_jar = parse_cookie_file("resources/apis.naver.com_cookies.txt")
        self.session.cookies.update(cookie_jar)
        
    def get_post_list(self, name):
        cafe_id = self.ids[name]
        self.session.headers.update({
            "Referer": f"https://cafe.naver.com/ca-fe/cafes/27842958/members/{cafe_id}"
        })
        res = self.session.get(self.board_api(cafe_id), verify=False)
        data = json.loads(res.text)
        
        if res.status_code == 500:
            if data["message"]["error"]["code"] == "004":
                return print("please login!")
            else:
                return print("returned 500!")
        posts = data["message"]["result"]["articleList"]
        
        stmt = select(Streamer.id).where(Streamer.name == name).limit(1)
        streamer_id = self.db.session.execute(stmt).scalar()
        stmt = select(CafePost.post_id).join(Post.cafe_post).where(Post.streamer_id == streamer_id).order_by(CafePost.created_at.desc()).limit(1)
        latest_post_id = self.db.session.execute(stmt).scalar()
        
        new_posts = []
        for post in posts:
            if post["articleid"] == latest_post_id:
                break;
            new_posts.append(post)
        return new_posts
    
    def save_img_and_return_file(self, url, post_id):
        res = self.session.get(url, stream=True)
        raw_img = res.content
        raw_img_size = len(raw_img)
        try:
            mime_type = res.headers['Content-Type']
        except:
            print(f"Header Error!!! url:{url}, post_id:{post_id}")
            return None
        new_file = File(
                id = uuid.uuid4(),
                mime_type = mime_type,
                size = raw_img_size,
                post_id = post_id,
                file_type=FileType.local
            )
        # self.azure_blob.container_client.upload_blob(name = str(new_file.id), data=raw_img)
        print(f"\t\timg was registered to azure blob! [{new_file.id}]")
        return new_file
    
    def update_post(self, name, post, transaction):
        post_id = str(post["articleid"])
        post_title = post["subject"]
        stmt = select(CafePost.title).where(CafePost.post_id==post_id)
        old_post_title = transaction.execute(stmt).scalar()
        if old_post_title != None:
            if old_post_title != post_title:
                stmt = update(CafePost).where(CafePost.post_id == post_id).values(title = post_title)
                transaction.execute(stmt)
                print(f"\ttitle updated! [{post_id}]: {old_post_title} -> {post_title}")
            else:
                # stmt = select(CafePost).where(CafePost.post_id==post_id)
                # cafe_post = db.execute(stmt).scalar()
                # # 중복 업데이트
                # print(f"\talready exists mate! [{post_id}]")
                pass
        else:
            res = self.session.get(self.post_api(post_id))
            data = json.loads(res.text)
            if res.status_code == 500:
                return print("Error!")
            parsed = BeautifulSoup(data["result"]["article"]["contentHtml"], "html.parser")
            content_element = parsed.find("div", {"class":"se-module-text"})
            content_text = content_element.get_text(separator="\n", strip=True).strip()
            stmt = select(Streamer).where(Streamer.name==name)
            streamer = transaction.execute(stmt).scalar()
            new_detail = CafePost(
                id = uuid.uuid4(),
                post_id = post_id,
                url = f"https://cafe.naver.com/steamindiegame/{post_id}",
                category = post["clubMenu"]["menuname"],
                title = post_title,
                content = content_text,
                uploaded_at = datetime.strptime(post["writedt"], "%b %d, %Y %I:%M:%S %p"), # Nov 10, 2024 7:15:51 PM
                # streamer_id = streamer.id
            )
            transaction.add(new_detail)
            new_post = Post(
                id = uuid.uuid4(),
                type = PostType.Cafe,
                uploaded_at = new_detail.uploaded_at,
                streamer_id = streamer.id,
                cafe_post_id = new_detail.id
            )
            transaction.add(new_post)
            img_elements = parsed.find_all("img")
            for img_element in img_elements:
                new_file = self.save_img_and_return_file(img_element["src"], new_post.id)
                if new_file != None:
                    transaction.add(new_file)
            delay = random.random() + random.randrange(0, 3)
            print(f"\tpost added! [{post_id}]\n\twait for {delay:.2f}s...")
            time.sleep(delay)
    
    def update_post_by_list(self, name, posts):
        with self.db.session as transaction:
            for post in posts:
                self.update_post(name, post, transaction)
            transaction.commit()
            print("\t[transaction committed!]")

    def crawl(self):
        for name in self.names:
            print(f"Crawling cafe posts of [{name}]")
            posts = self.get_post_list(name)
            self.update_post_by_list(name, posts)
            delay = random.random() + random.randrange(5, 10)
            print(f"Crawled cafe posts of [{name}]\nwait for {delay:.2f}s...\n")
        time.sleep(60)
    
    def crawl_loop(self):
        while True:
            self.crawl()