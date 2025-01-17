from modules.base_crawler import BaseCrawler
import os
from requests import Session
from sqlalchemy import select
from models.soop_post import SoopPost
from models.streamer import Streamer
from models.file import File, FileType
from models.post import Post, PostType
import time
import random
from datetime import datetime
import uuid
from bs4 import BeautifulSoup

original_print = print
def print(content):
    original_print("\t[SoopCrawler]: ", end="")
    original_print(content)

class SoopPostCrawler(BaseCrawler):
    
    def __init__(self, db):
        super().__init__(db)        
        self.ids = {}
        self.ids["woowakgood"] = os.getenv("SOOP_WOOWAKGOOD_ID")
        self.ids["ine"] = os.getenv("SOOP_INE_ID")
        self.ids["jingburger"] = os.getenv("SOOP_JINGBURGER_ID")
        self.ids["lilpa"] = os.getenv("SOOP_LILPA_ID")
        self.ids["jururu"] = os.getenv("SOOP_JURURU_ID")
        self.ids["gosegu"] = os.getenv("SOOP_GOSEGU_ID")
        self.ids["viichan"] = os.getenv("SOOP_VIICHAN_ID")
        self.names = ["woowakgood", "ine", "jingburger", "lilpa", "jururu", "gosegu", "viichan"]
        
        self.board_api = lambda soop_id : os.getenv("SOOP_BOARD_API").replace("{soop_id}", soop_id)
        
        self.session = Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "ko-KR,ko;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "sec-ch-ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
            "sec-ch-ua-platform": '"Windows"',
            "sec-ch-ua-mobile": "?0",
            "Origin": "https://ch.sooplive.co.kr"
        })
        
    def get_post_list(self, name):
        self.session.headers.update({
            "referer": f"https://ch.sooplive.co.kr/{self.ids[name]}/posts?page=1&type=post/"
        })
        url = self.board_api(self.ids[name])
        res = self.session.get(url, verify=False)
        if res.status_code != 200:
            # print(res.text)
            raise Exception(f"Requests Error! status: {res.status_code}")
        posts = res.json()["data"]
        stmt = select(Streamer.id).where(Streamer.name == name).limit(1)
        streamer_id = self.db.session.execute(stmt).scalar()
        stmt = select(SoopPost.post_id).join(Post.soop_post).where(Post.streamer_id == streamer_id).order_by(SoopPost.created_at.desc()).limit(1)
        latest_post_id = self.db.session.execute(stmt).scalar()
        
        new_posts = []
        for post in posts:
            if post["title_no"] == latest_post_id:
                break;
            new_posts.append(post)
        posts = new_posts
        return posts
    
    def extract_text_with_links(self, html):
        soup = BeautifulSoup(html, 'html.parser')

        def process_element(element):
            # <a> 태그는 내부를 단순화
            if element.name == 'a':
                element["class"] = ["link"]
                inner_text = ''.join(element.stripped_strings)
                element.clear()
                element.append(inner_text)
                return element
            # 텍스트 노드는 바로 반환
            if isinstance(element, str):
                return element
            # 자식 요소들을 순회하며 처리
            if hasattr(element, 'contents'):
                new_contents = []
                for child in element.contents:
                    processed_child = process_element(child)
                    if isinstance(processed_child, str):  # 텍스트인 경우
                        new_contents.append(processed_child)
                    else:  # 태그인 경우
                        new_contents.append(str(processed_child))  # 태그를 문자열로 변환하여 추가
                element.clear()
                element.extend(new_contents)
                return ''.join(new_contents)
            # 최종적으로 텍스트만 반환
            return element.get_text()

        # 루트 요소에 대해 처리
        for element in soup.find_all(True, recursive=False):
            processed = process_element(element)
            element.replace_with(processed)

        return soup.text
        
        
    def format_content(self, text):
        content_html = text.replace("%\"", "\"").replace("%n", "")
        content = self.extract_text_with_links(content_html)
        return content
    
    def update_post(self, name, post, transaction):
        post_id = post["title_no"]
        title = post["title_name"]
        url = f"https://ch.sooplive.co.kr/{self.ids[name]}/post/{post_id}"
        content = self.format_content(post["content"]["content"])
        uploaded_at = datetime.strptime(post["reg_date"], "%Y-%m-%d %H:%M:%S")
        stmt = select(Streamer).where(Streamer.name==name)
        streamer = transaction.execute(stmt).scalar()
        new_detail = SoopPost(
            id = uuid.uuid4(),
            post_id=post_id,
            url=url,
            title=title,
            content=content,
            uploaded_at=uploaded_at
        )
        transaction.add(new_detail)
        new_post = Post(
            id = uuid.uuid4(),
            type = PostType.Soop,
            uploaded_at = new_detail.uploaded_at,
            streamer_id = streamer.id,
            soop_post_id = new_detail.id
        )
        transaction.add(new_post)
        for photo in post["photos"]:
            new_file = File(
                name=photo["key"],
                mime_type="image/"+photo["file_name"].split(".")[-1],
                url="https:"+photo["url"],
                size=photo["file_size"],
                file_type=FileType.external,
                post_id=new_post.id
            )
            transaction.add(new_file)
        if post["ucc"] != None:
            for video in post["ucc"]:
                new_file = File(
                    name=video["thumb"],
                    mime_type="image/jfif",
                    url="https:"+video["thumb"],
                    file_type=FileType.external,
                    post_id=new_post.id
                )
                transaction.add(new_file)
    
    def update_post_by_list(self, name, posts):
        with self.db.session as transaction:
            for post in posts:
                if post["user_id"] != self.ids[name]:
                    continue
                self.update_post(name, post, transaction)
            transaction.commit()
    
    def crawl(self):
        for name in self.names:
            print(f"Crawling soop posts of [{name}]")
            posts = self.get_post_list(name)
            self.update_post_by_list(name, posts)
            delay = random.random() + random.randrange(10, 15)
            print(f"Crawled soop posts of [{name}]\nwait for {delay:.2f}s...\n")
            time.sleep(delay)
            
    def crawl_loop(self):
        while True:
            self.crawl()