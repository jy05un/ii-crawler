from modules.base_crawler import BaseCrawler
import os
from requests import Session
import json
from sqlalchemy import exists, select
from models.ig_post import IgPost
from models.streamer import Streamer
from models.file import File, FileType
from models.post import Post, PostType
import time
import random
from datetime import datetime
import uuid
import re

original_print = print
def print(content):
    original_print("\t[IgCrawler]: ", end="")
    original_print(content)

class IgPostCrawler(BaseCrawler):
    
    def __init__(self, db, azure_blob):
        super().__init__(db)
        self.azure_blob = azure_blob       
        self.ids = {}
        self.ids["woowakgood"] = os.getenv("IG_WOOWAKGOOD_ID")
        self.ids["ine"] = os.getenv("IG_INE_ID")
        self.ids["jingburger"] = os.getenv("IG_JINGBURGER_ID")
        self.ids["lilpa"] = os.getenv("IG_LILPA_ID")
        self.ids["jururu"] = os.getenv("IG_JURURU_ID")
        self.ids["gosegu"] = os.getenv("IG_GOSEGU_ID")
        self.ids["viichan"] = os.getenv("IG_VIICHAN_ID")
        self.nicknames = {}
        self.nicknames["woowakgood"] = os.getenv("IG_WOOWAKGOOD_NICKNAME")
        self.nicknames["ine"] = os.getenv("IG_INE_NICKNAME")
        self.nicknames["jingburger"] = os.getenv("IG_JINGBURGER_NICKNAME")
        self.nicknames["lilpa"] = os.getenv("IG_LILPA_NICKNAME")
        self.nicknames["jururu"] = os.getenv("IG_JURURU_NICKNAME")
        self.nicknames["gosegu"] = os.getenv("IG_GOSEGU_NICKNAME")
        self.nicknames["viichan"] = os.getenv("IG_VIICHAN_NICKNAME")
        self.names = ["woowakgood", "ine", "jingburger", "lilpa", "jururu", "gosegu", "viichan"]
        
        self.board_api = lambda ig_nickname : os.getenv("IG_BOARD_API").replace("{ig_nickname}", ig_nickname)
        self.board_api_next = lambda variables : os.getenv("IG_BOARD_API_NEXT").replace("{variables}", variables)
        
        self.session = Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Accept": "*/*",
            "Accept-Language": "ko-KR,ko;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "sec-ch-ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
            "sec-ch-ua-full-version-list": '"Google Chrome";v="131.0.6778.265", "Chromium";v="131.0.6778.265", "Not_A Brand";v="24.0.0.0"',
            "sec-ch-ua-platform": '"Windows"',
            "sec-ch-ua-mobile": "?0",
            "x-ig-app-id": os.getenv("IG_APP_ID")
        })
        # Referer : https://www.instagram.com/{id}/
        
    def get_post_list_next(self, name, end_cursor, latest_post_id, posts=[]):
        delay = random.random() + random.randrange(30, 40)
        print(f"\t다음 페이지 읽기 전 대기... {delay:.2f}s")
        time.sleep(delay)
        
        variables = f"{{\"id\":\"{self.ids[name]}\",\"after\": \"{end_cursor}\",\"first\":12}}"
        variables = str(variables)
        url = self.board_api_next(variables)
        res = self.session.get(url)
        try:
            data = res.json()["data"]
        except:
            print("Error!!!!!!!!!!!!!: " + str(res.json()))
            return posts
        timeline = data["user"]["edge_owner_to_timeline_media"]
        next_posts = timeline["edges"]
        new_posts = []
        for post in next_posts:
            if post["node"]["id"] == latest_post_id:
                break;
            new_posts.append(post)
        next_posts = new_posts
        posts = posts + next_posts
        if "page_info" in timeline and "has_next_page" in timeline["page_info"]:
            if timeline["page_info"]["has_next_page"] == True:
                return self.get_post_list_next(name, timeline["page_info"]["end_cursor"], latest_post_id, posts)
        return posts
        
    def get_post_list(self, name):
        self.session.headers.update({
            "referer": f"https://www.instagram.com/{self.nicknames[name]}/"
        })
        url = self.board_api(self.nicknames[name])
        # print(url)
        res = self.session.get(url, verify=False)
        if res.status_code != 200:
            # print(res.text)
            raise Exception(f"Requests Error! status: {res.status_code}")
                
        data = res.json()["data"]
        timeline = data["user"]["edge_owner_to_timeline_media"]
        if "edges" not in timeline:
            posts = []
        else:
            posts = timeline["edges"]
        stmt = select(Streamer.id).where(Streamer.name == name).limit(1)
        streamer_id = self.db.session.execute(stmt).scalar()
        stmt = select(IgPost.post_id).join(Post.ig_post).where(Post.streamer_id == streamer_id).order_by(IgPost.created_at.desc()).limit(1)
        latest_post_id = self.db.session.execute(stmt).scalar()
        
        new_posts = []
        for post in posts:
            if post["node"]["id"] == latest_post_id:
                break;
            new_posts.append(post)
        posts = new_posts
        if "page_info" in timeline and "has_next_page" in timeline["page_info"]:
            if timeline["page_info"]["has_next_page"] == True:
                next_posts = self.get_post_list_next(name, timeline["page_info"]["end_cursor"], latest_post_id)
                posts = posts + next_posts
        
        return posts
        
        #print("함수 잘 작동하는지 테스트... " + str(len(posts)), timeline["count"])
        
        # print(res.text)
        # data = json.loads(res.text)
        # f = open("test/ig.json", "w", encoding="utf-8")
        # f.write(json.dumps(data, indent="\t", ensure_ascii=False))
        # f.close()
    
    def save_rsrc_and_return_file(self, name, url, post_id):
        res = self.session.get(url, stream=True)
        raw_rsrc = res.content
        raw_rsrc_size = len(raw_rsrc)
        mime_type = res.headers['Content-Type']
        new_file = File(
                id = uuid.uuid4(),
                name=name,
                mime_type = mime_type,
                size = raw_rsrc_size,
                post_id = post_id,
                file_type=FileType.local
            )
        # self.azure_blob.container_client.upload_blob(name = str(new_file.id), data=raw_rsrc)
        print(f"\t\traw_rsrc was registered to azure blob! [{new_file.id}]")
        return new_file
    
    def update_post(self, name, post, transaction):
        post = post["node"]
        content = post["edge_media_to_caption"]["edges"][0]["node"]["text"]
        tags = re.findall(r"@[\w](?!.*?\.{2})[\w.]{1,28}[\w]", content)
        for tag in tags:
            content = content.replace(tag, f"<a class='link' href='https://www.instagram.com/{tag[1:]}/'>{tag}</a>")
        hashtags = re.findall(r"#[a-zA-Z0-9\u00A0-\uFFFF]+", content)
        for hashtag in hashtags:
            content = content.replace(hashtag, f"<a class='link' href='https://www.instagram.com/{hashtag[1:].lower()}/'>{hashtag}</a>")
        post_type = post["__typename"]
        post_id = post["id"]
        uploaded_at = datetime.fromtimestamp(int(post["taken_at_timestamp"]))
        url_code = post["shortcode"]
        
        stmt = select(Streamer).where(Streamer.name==name)
        streamer = transaction.execute(stmt).scalar()
        
        new_detail = IgPost(
            id = uuid.uuid4(),
            post_id=post_id,
            url=f"https://www.instagram.com/p/{url_code}/",
            content=content,
            uploaded_at=uploaded_at
        )
        transaction.add(new_detail)
        
        new_post = Post(
                id = uuid.uuid4(),
                type = PostType.Instagram,
                uploaded_at = new_detail.uploaded_at,
                streamer_id = streamer.id,
                ig_post_id = new_detail.id
            )
        transaction.add(new_post)
        
        resource_index = 1
        if post_type == "GraphVideo":
            new_video = self.save_rsrc_and_return_file(
                name=post_id+"_"+str(resource_index),
                url=post["video_url"],
                post_id=new_post.id
            )
            resource_index += 1
            transaction.add(new_video)
        elif post_type == "GraphImage":
            new_image = self.save_rsrc_and_return_file(
                name=post_id+"_"+str(resource_index),
                url=post["display_url"],
                post_id=new_post.id
            )
            resource_index += 1
            transaction.add(new_image)
        elif post_type == "GraphSidecar":
            childrens = post["edge_sidecar_to_children"]["edges"]
            for children in childrens:
                children = children["node"]
                children_type = children["__typename"]
                if children_type == "GraphVideo":
                    new_video = self.save_rsrc_and_return_file(
                        name=post_id+"_"+str(resource_index),
                        url=children["video_url"],
                        post_id=new_post.id
                    )
                    resource_index += 1
                    transaction.add(new_video)
                elif children_type == "GraphImage":
                    new_image = self.save_rsrc_and_return_file(
                        name=post_id+"_"+str(resource_index),
                        url=children["display_url"],
                        post_id=new_post.id
                    )
                    resource_index += 1
                    transaction.add(new_image)
                    
    def update_post_by_list(self, name, posts):
        with self.db.session as transaction:
            for post in posts:
                self.update_post(name, post, transaction)
            transaction.commit()
            print("\t[transaction committed!]")
    
    def crawl(self):
        for name in self.names:
            print(f"Crawling ig posts of [{name}]")
            posts = self.get_post_list(name)
            self.update_post_by_list(name, posts)
            delay = random.random() + random.randrange(60, 90)
            print(f"Crawled ig posts of [{name}]\nwait for {delay:.2f}s...\n")
            time.sleep(delay)
        # name = "jururu"
        # print(f"Crawling ig posts of [{name}]")
        # posts = self.get_post_list(name)
        # self.update_post_by_list(name, posts)
        # delay = random.random() + random.randrange(60, 90)
        # print(f"Crawled ig posts of [{name}]\nwait for {delay:.2f}s...\n")
        # time.sleep(delay)
        
    def crawl_loop(self):
        while True:
            self.crawl()