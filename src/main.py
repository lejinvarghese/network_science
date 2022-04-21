"""
Extracts Twitter API v2.0 to extract forward one hop neighbors of followed users
"""

import os
from dotenv import load_dotenv
import time
from multiprocessing import cpu_count
from multiprocessing.pool import ThreadPool
import pandas as pd
import dask.dataframe as dd
import tweepy
from datetime import datetime

load_dotenv()

n_threads = cpu_count() - 1
run_time = datetime.today().strftime("%Y_%m_%d_%H_%M_%S")
TWITTER_USERNAME = os.getenv("TWITTER_USERNAME")
TWITTER_API_KEY = os.getenv("TWITTER_API_KEY")
TWITTER_API_SECRET = os.getenv("TWITTER_API_SECRET")
TWITTER_API_BEARER_TOKEN = os.getenv("TWITTER_API_BEARER_TOKEN")
CLOUD_STORAGE_BUCKET = "gs://graph_data_science/twitter"

client = tweepy.Client(TWITTER_API_BEARER_TOKEN, wait_on_rate_limit=True)


def get_user_following(user):
    following_users = []
    for i in tweepy.Paginator(
        client.get_users_following, id=user, max_results=1000
    ).flatten(limit=5000):
        time.sleep(0.1)
        following_users.append(i.id)  # username
    print(f"User: {user}, Following: {len(following_users)}")
    return {"user": user, "following": following_users}


def get_user_description(users):
    data = client.get_users(
        ids=users, user_fields=["profile_image_url", "username"]
    ).data
    return [x.name + ":" + x.username for x in data]


def get_user_ids(usernames):
    data = client.get_users(usernames=usernames, user_fields=["id"]).data
    return [x.id for x in data]


def main():
    user = client.get_user(
        username=TWITTER_USERNAME,
        user_fields=["id"],
    ).data.id

    existing_users = list(
        dd.read_csv(f"{CLOUD_STORAGE_BUCKET}/data/users_following*.csv")
        .compute()
        .user.unique()
    )

    print(f"Previously following: {len(existing_users)}")

    following_users = get_user_following(user).get("following")

    print(f"Currently following: {len(following_users)}")

    r_following_users = list(set(following_users) - set(existing_users))

    print(f"New following: {len(r_following_users)}")

    with ThreadPool(n_threads) as t_pool:
        data = t_pool.map_async(get_user_following, r_following_users).get()

    data = pd.json_normalize(data)
    data.to_csv(
        f"{CLOUD_STORAGE_BUCKET}/data/users_following_{run_time}.csv", index=False
    )


if __name__ == "__main__":
    main()