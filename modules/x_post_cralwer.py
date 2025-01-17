from modules.base_crawler import BaseCrawler
import os
from requests import Session
import json
from sqlalchemy import exists, select
from models.x_post import XPost, RefType
from models.streamer import Streamer
from models.file import File, FileType
from models.post import Post, PostType
import time
from datetime import datetime
import uuid

original_print = print
def print(content):
    original_print("\t[XCrawler]: ", end="")
    original_print(content)

class TooManyRequestsException(Exception):
    pass

class XPostCrawler(BaseCrawler):
    
    def __init__(self, db):
        super().__init__(db)
        
        self.max_result = 5 # 5~100
        
        bearer_token = os.getenv("X_BEARER_TOKEN")
        
        self.ids = {}
        self.ids["woowakgood"] = os.getenv("X_WOOWAKGOOD_ID")
        self.ids["jingburger"] = os.getenv("X_JINGBURGER_ID")
        self.ids["lilpa"] = os.getenv("X_LILPA_ID")
        self.ids["jururu"] = os.getenv("X_JURURU_ID")
        self.ids["gosegu"] = os.getenv("X_GOSEGU_ID")
        self.ids["viichan"] = os.getenv("X_VIICHAN_ID")
        self.names = ["woowakgood", "jingburger", "lilpa", "jururu", "gosegu", "viichan"]
        
        self.session = Session()
        self.session.headers.update({
            "Authorization": f"Bearer {bearer_token}"
        })
        
    def board_api(self, x_id, max_results_count, since_id):
        if since_id == None:
            return os.getenv("X_BOARD_API").replace("{x_id}", x_id).replace("{max_results_count}", str(max_results_count)).replace("since_id={since_id}&", "")
        else:
            return os.getenv("X_BOARD_API").replace("{x_id}", x_id).replace("{max_results_count}", str(max_results_count)).replace("{since_id}", since_id)
        
    def filter_fields(self, dict_list, fields_to_keep):
        return [{key: d[key] for key in fields_to_keep if key in d} for d in dict_list]
        
    def  remove_duplicates_from_list(self, dict_list):
        seen = set()
        unique_dicts = []
        for d in dict_list:
            serialized = json.dumps(d, sort_keys=True)  # 딕셔너리를 정렬된 문자열로 변환
            if serialized not in seen:
                seen.add(serialized)
                unique_dicts.append(d)
        return unique_dicts
        
    def format_content(self, text, entities):
        expand_length = 0
        if "mentions" in entities:
            mentions = self.filter_fields(entities["mentions"], ["start", "end", "username"])
            mentions = self. remove_duplicates_from_list(mentions)
            for mention in mentions:
                start_idx = mention["start"] + expand_length
                end_idx = mention["end"] + expand_length
                before = "" if start_idx-1 <= 0 else text[:start_idx-1]
                after = text[end_idx:]
                mention_text = text[start_idx:end_idx]
                mention_text = f"{before}<a class='link' href='https://x.com/{mention['username']}'>{mention_text}</a>{after}"
                expand_length = expand_length + len(f"<a class='link' href='https://x.com/{mention['username']}'>"+"</a>")
                text = before + mention_text + after
        elif "urls" in entities:
            urls = self.filter_fields(entities["urls"], ["start", "end", "expanded_url"])
            urls = self. remove_duplicates_from_list(urls)
            for url in urls:
                start_idx = url["start"] + expand_length
                end_idx = url["end"] + expand_length
                before = "" if start_idx-1 <= 0 else text[:start_idx-1]
                after = text[end_idx:]
                url_text = text[start_idx:end_idx]
                url_text = f"{before}<a class='link' href='{url['expanded_url']}'>{url_text}</a>{after}"
                expand_length = expand_length + len(f"<a class='link' href='{url['expanded_url']}'>"+"</a>")
                text = before + url_text + after
        return text
                
    def format_post_to_model(self, streamer, post, includes):
        x_id = self.ids[streamer.name]
        post_id = post["id"]
        ref_type = None
        ref_profile_json = None
        content = self.format_content(post["text"], post["entities"] if "entities" in post else {})
        uploaded_at = datetime.strptime(post["created_at"], "%Y-%m-%dT%H:%M:%S.%fZ")
        
        if "referenced_tweets" in post:
            users = includes["users"]
            if post["referenced_tweets"][0]["type"] == "retweeted":    # 리트윗
                ref_type = RefType.Retweeted
                for user in users:
                    if user["id"] == post["author_id"]:
                        ref_profile_json = user
                        break
            elif post["referenced_tweets"][0]["type"] == "quoted":     # 인용
                ref_type = RefType.Quoted
            elif post["referenced_tweets"][0]["type"] == "replied_to": # 답변
                ref_type = RefType.Replied_to
        
        x_post_id = uuid.uuid4()
        files = []
        if "attachments" in post:
            if "media_keys" in post["attachments"]:
                media_keys = post["attachments"]["media_keys"]
                medias = includes["media"]
                for media_key in media_keys:
                    for media in medias:
                        if media_key == media["media_key"]:
                            if media["type"] in ["animated_gif", "video"]:
                                variants = media["variants"]
                                file_type = variants[-1]["content_type"]    # last one == highest quality
                                url = variants[-1]["url"]
                            elif media["type"] == "photo":
                                url = media["url"]
                                file_ext = url.split(".")[-1]
                                file_type = f"image/{file_ext}"
                            if "file_type" in locals() or "file_type" in globals():
                                files.append(File(
                                    name = media_key,
                                    mime_type = file_type,
                                    url = url,
                                    file_type = FileType.external,
                                ))
                            else:
                                print(f"\tI've never heard of [{media['type']}] file type...")
                            break
            elif "poll_dis" in post["attachments"]:
                # 투표가 존재
                content = "게시글에 투표가 존재합니다! 눌러서 보러가기...\n\n" + content
            
        return XPost(
            id = x_post_id,
            url = f"https://x.com/{x_id}/status/{post_id}",
            uploaded_at = uploaded_at,
            post_id = post_id,
            content = content,
            ref_type = ref_type,
            ref_profile_json = ref_profile_json
        ), files
            
        
    def update_post(self, name, post, includes, transaction):
        post_id = post["id"]
        stmt = exists().where(XPost.post_id==post_id)
        is_exists = transaction.query(stmt).scalar()
        if is_exists:
            return # print(f"\talready exists mate! [{post_id}]")
        stmt = select(Streamer).where(Streamer.name==name)
        streamer = transaction.execute(stmt).scalar()
        new_detail, new_files = self.format_post_to_model(streamer, post, includes)
        transaction.add(new_detail)
        new_post = Post(
            id = uuid.uuid4(),
            type = PostType.X,
            uploaded_at = new_detail.uploaded_at,
            streamer_id = streamer.id,
            x_post_id = new_detail.id
        )
        transaction.add(new_post)
        print(f"\tpost added! [{post_id}]")
        for new_file in new_files:
            new_file.post_id = new_post.id
            transaction.add(new_file)
            print(f"\t\tfile added! [{new_file.id}]")
        
    def update_post_by_list(self, name, posts, includes):
        with self.db.session as transaction:
            for post in posts:
                self.update_post(name, post, includes, transaction)
            transaction.commit()
            print("\t[transaction committed!]")
    
    def get_post_list_test(self ,name):
        x_id = self.ids[name]
        stmt = select(Streamer.id).where(Streamer.name == name).limit(1)
        streamer_id = self.db.session.execute(stmt).scalar()
        stmt = select(XPost.post_id).join(Post.x_post).where(Post.streamer_id == streamer_id).order_by(XPost.created_at.desc()).limit(1)
        latest_post_id = self.db.session.execute(stmt).scalar()
        
        f = open(f"test/x_data_{name}.json", "r", encoding="utf-8")
        dt = f.read()
        
        data = json.loads(dt)
        posts = data["data"]
        includes = None
        try:
            includes = data["includes"]
        except:
            includes = None
        return posts, includes
    
    def get_post_list(self, name):
        x_id = self.ids[name]
        stmt = select(Streamer.id).where(Streamer.name == name).limit(1)
        streamer_id = self.db.session.execute(stmt).scalar()
        stmt = select(XPost.post_id).join(Post.x_post).where(Post.streamer_id == streamer_id).order_by(XPost.created_at.desc()).limit(1)
        latest_post_id = self.db.session.execute(stmt).scalar()
        uri = self.board_api(x_id, self.max_result, latest_post_id)
        res = self.session.get(uri, verify=False)
        if res.status_code == 429:
            raise TooManyRequestsException("too many requests")
        data = json.loads(res.text)
        file = open(f'resources/data_backup/{str(datetime.now().strftime("%Y%m%d-%H%M%S"))}_x_data_{name}.json', 'w', encoding='utf-8')
        file.write(json.dumps(data, ensure_ascii=False, indent="\t"))
        posts = data["data"]
        includes = None
        try:
            includes = data["includes"]
        except:
            includes = None
        return posts, includes
        
    def crawl(self, test=False):
        for name in self.names:
            print(f"Crawling x posts of [{name}]")
            try :
                if test:
                    posts, includes = self.get_post_list_test(name)
                else:
                    posts, includes = self.get_post_list(name)
                
            except TooManyRequestsException as tmre:
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                print(f"\tToo Many Requests! {now}")
                time.sleep(30*60)
                continue
            except Exception as e:
                print("\tError!", e)
                time.sleep(10)
                continue
            self.update_post_by_list(name, posts, includes)
            delay = 30*60 if test == False else 1
            print(f"Crawled x posts of [{name}]\nwait for {delay:.2f}s...\n")
            time.sleep(delay)
        time.sleep(15)
            
    def crawl_loop(self, test=False):
        while True:
            self.crawl(test)
        
# 한달에 100번의 요청 가능