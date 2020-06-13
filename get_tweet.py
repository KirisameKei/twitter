import datetime
import json
import os
import time

import requests
import schedule
import urllib
from requests_oauthlib import OAuth1

os.chdir(os.path.dirname(os.path.abspath(__file__)))

# APIの秘密鍵
try:
    import tokens_ConoHa
except ModuleNotFoundError:
    consumer_key = os.getenv("consumer_key")
    consumer_secret = os.getenv("consumer_secret")
    twitter_token = os.getenv("twitter_token")
    token_secret = os.getenv("token_secret")
else:
    consumer_key = tokens_ConoHa.consumer_key
    consumer_secret = tokens_ConoHa.consumer_secret
    twitter_token = tokens_ConoHa.twitter_token
    token_secret = tokens_ConoHa.token_secret

def main_thread():
    # 検索時のパラメーター
    yesterday = (datetime.date.today() - datetime.timedelta(days=1)).strftime(r"%Y-%m-%d")
    word = f"(from:kei__3104) since:{yesterday}" # 検索ワード

    # 文字列設定
    word = urllib.parse.quote_plus(word)
    # リクエスト
    url = f"https://api.twitter.com/1.1/search/tweets.json?lang=ja&q={word}&count=100" #絶対100も要らないと思います。20くらいで十分
    auth = OAuth1(consumer_key, consumer_secret, twitter_token, token_secret)
    response = requests.get(url, auth=auth)

    data_list = response.json()["statuses"]

    with open("tweet_id.txt", mode="r") as f:
        last_record_tweet_id = int(f.read())

    send_list = []
    for data in data_list:
        if data["id"] == last_record_tweet_id:
            break

        else:
            if data_list.index(data) == 0:
                new_id = data["id"]
            #各月の英語がわからない(バカ)
            #月が変わってKeyErrorが出れば英語で表示されるのでその時直す
            month_dict = {
                "Jun": "6"
            }
            tweeted_time = data["created_at"].split()
            year = tweeted_time[5]
            try:
                month = month_dict[tweeted_time[1]]
            except KeyError:
                month = tweeted_time[1]
            day = tweeted_time[2]
            h_m_s_UTC = datetime.datetime.strptime(tweeted_time[3], r"%H:%M:%S")
            h_m_s_JST = (h_m_s_UTC + datetime.timedelta(hours=9)).strftime(r"%H:%M:%S")
            time_format = f"{year}/{month}/{day}-{h_m_s_JST}"
            
            content = {
                "username": data["user"]["name"],
                "userid": data["user"]["screen_name"],
                "icon_url": data["user"]["profile_image_url"],
                "created_at": time_format,
                "tweet_id": data["id"],
                "text": data["text"],
                "hashtags": data["entities"]["hashtags"],
                "user_mentions": data["entities"]["user_mentions"]
            }
            try:
                content["image"] = data["extended_entities"]["media"]
            except KeyError:
                content["image"] = []
            send_list.append(content)

    with open("tweet_id.txt", mode="w") as f:
        try:
            f.write(f"{new_id}")
        except NameError:
            f.write(f"{last_record_tweet_id}")

    for tweet in reversed(send_list):
        text = tweet["text"]
        for hashtag in tweet["hashtags"]:
            hashtag = hashtag["text"]
            hashtag_persent = urllib.parse.quote(f"#{hashtag}")
            text = text.replace(f"#{hashtag}", f"[#{hashtag}](https://twitter.com/search?q={hashtag_persent}&src=typed_query&f=live)")

        for user in tweet["user_mentions"]:
            user = user["screen_name"]
            text = text.replace(f"@{user}", f"[@{user}](https://twitter.com/{user})")

        user_id = tweet["userid"]
        tweet_id = tweet["tweet_id"]
        images = tweet["image"]

        image_url_list = []
        for image in images:
            image_url_list.append({"url": image["media_url"]})

        #今思ったけどcontent全部書くんじゃなくてmain_content["embeds"][0].append(image: {"url": "hogehoge"})でもいいかもしれない
        if len(image_url_list) == 0:
            main_content = {
                "username": tweet["username"],
                "avatar_url": tweet["icon_url"],
                "embeds": [
                    {
                        "author": {
                            "name": tweet["username"] + " @" + tweet["userid"],
                            "icon_url": tweet["icon_url"],
                            "url": f"http://twitter.com/{user_id}/status/{tweet_id}"
                        },
                        "description": text,
                        "color": 0x00aaff,
                        "footer": {
                            "text": tweet["created_at"]
                        }
                    }
                ]
            }
        else:
            main_content = {
                "username": tweet["username"],
                "avatar_url": tweet["icon_url"],
                "embeds": [
                    {
                        "author": {
                            "name": tweet["username"] + " @" + tweet["userid"],
                            "icon_url": tweet["icon_url"],
                            "url": f"http://twitter.com/{user_id}/status/{tweet_id}"
                        },
                        "description": text,
                        "image": {
                            "url": image_url_list[0]["url"]
                        },
                        "color": 0x00aaff,
                        "footer": {
                            "text": tweet["created_at"]
                        }
                    }
                ]
            }
        twitter_webhook_url = "https://discordapp.com/api/webhooks/ID/TOKEN"
        requests.post(twitter_webhook_url, json.dumps(main_content), headers={"Content-Type": "application/json"})
        time.sleep(0.3)

        try:
            del image_url_list[0]
        except IndexError:
            pass
        else:
            for image_url_dict in image_url_list:
                content = {
                    "username": tweet["username"],
                    "avatar_url": tweet["icon_url"],
                    "embeds": [
                        {
                            "image": {
                                "url": image_url_dict["url"]
                            },
                            "color": 0x00aaff,
                            "footer": {
                                "text": tweet["created_at"]
                            }
                        }
                    ]
                }
                requests.post(twitter_webhook_url, json.dumps(content), headers={"Content-Type": "application/json"})
                time.sleep(0.3)

schedule.every(1).minute.do(main_thread)
while True:
    schedule.run_pending()
    time.sleep(1)