import time
import requests
import pandas as pd
 
from src.settings import load_settings, get_youtube_api_key
 
BASE_URL = "https://www.googleapis.com/youtube/v3"
 
 
def call_youtube_api(endpoint, params, api_key):
    """
    Sends one request to the YouTube API and returns the response as a
    dictionary. If something goes wrong (bad request, quota used up, etc.)
    we raise a clear error instead of letting the program crash confusingly.
    This is the same try/except pattern from Day 16.
    """
    params["key"] = api_key
    url = f"{BASE_URL}/{endpoint}"
 
    response = requests.get(url, params=params, timeout=20)
 
    if response.status_code != 200:
        raise RuntimeError(f"{endpoint} call failed (status {response.status_code}): {response.text[:200]}")
 
    return response.json()
 
 
def search_channels(query, region_code, api_key, max_results):
    """
    Searches YouTube for channels matching a keyword (e.g. "Fitness").
    Returns a list of channel IDs (just strings, like a list of names).
    """
    params = {
        "part": "snippet",
        "q": query,
        "type": "channel",
        "maxResults": max_results,
    }
    if region_code is not None:
        params["regionCode"] = region_code
 
    try:
        result = call_youtube_api("search", params, api_key)
    except RuntimeError as error:
        print(f"  Search failed for '{query}' ({region_code}): {error}")
        return []  # return an empty list so the rest of the program keeps going
 
    channel_ids = []
    for item in result.get("items", []):
        channel_id = item["snippet"]["channelId"]
        channel_ids.append(channel_id)
 
    return channel_ids
 
 
def get_channel_details(channel_ids, api_key):
    """
    Given a list of channel IDs, fetches their real stats: subscriber count,
    view count, video count, description, etc.
 
    The API only allows 50 channel IDs per request, so we split the list
    into chunks of 50 using a for loop with a step (like range(start, stop, step)
    from Day 5) and combine the results into one list.
    """
    all_channels = []
 
    for start in range(0, len(channel_ids), 50):
        batch = channel_ids[start:start + 50]
        params = {
            "part": "snippet,statistics,contentDetails",
            "id": ",".join(batch),
        }
 
        try:
            result = call_youtube_api("channels", params, api_key)
        except RuntimeError as error:
            print(f"  Failed to fetch channel details: {error}")
            continue
 
        for item in result.get("items", []):
            snippet = item.get("snippet", {})
            stats = item.get("statistics", {})
            uploads_playlist_id = (
                item.get("contentDetails", {})
                    .get("relatedPlaylists", {})
                    .get("uploads")
            )
 
            # hiddenSubscriberCount means the channel chose to hide this number
            if stats.get("hiddenSubscriberCount"):
                subscriber_count = None
            else:
                subscriber_count = int(stats.get("subscriberCount", 0))
 
            channel_record = {
                "channel_id": item["id"],
                "channel_title": snippet.get("title"),
                "description": (snippet.get("description") or "")[:300],
                "country": snippet.get("country", ""),
                "published_at": snippet.get("publishedAt"),
                "subscriber_count": subscriber_count,
                "view_count": int(stats.get("viewCount", 0)),
                "video_count": int(stats.get("videoCount", 0)),
                "uploads_playlist_id": uploads_playlist_id,
            }
            all_channels.append(channel_record)
 
        time.sleep(0.05)  # small pause so we don't hammer the API too fast
 
    return all_channels
 
 
def get_recent_video_ids(uploads_playlist_id, how_many, api_key):
    """Gets the IDs of a channel's most recent uploaded videos."""
    params = {
        "part": "contentDetails",
        "playlistId": uploads_playlist_id,
        "maxResults": how_many,
    }
    try:
        result = call_youtube_api("playlistItems", params, api_key)
    except RuntimeError:
        return []
 
    video_ids = []
    for item in result.get("items", []):
        video_ids.append(item["contentDetails"]["videoId"])
    return video_ids
 
 
def get_video_stats(video_ids, api_key):
    """Gets real view/like/comment counts for a list of video IDs."""
    if len(video_ids) == 0:
        return []
 
    params = {"part": "statistics", "id": ",".join(video_ids)}
    try:
        result = call_youtube_api("videos", params, api_key)
    except RuntimeError:
        return []
 
    video_stats = []
    for item in result.get("items", []):
        stats = item.get("statistics", {})
        video_stats.append({
            "views": int(stats.get("viewCount", 0)),
            "likes": int(stats.get("likeCount", 0)) if "likeCount" in stats else None,
            "comments": int(stats.get("commentCount", 0)) if "commentCount" in stats else None,
        })
    return video_stats
 
 
def calculate_engagement_rate(channel_row, video_ids_count, api_key):
    """
    Works out a real engagement rate for one channel by looking at its
    most recent videos: (average likes + average comments) / subscribers.
 
    channel_row is one row from the pandas DataFrame, so we can access
    values like channel_row.subscriber_count (similar to how we'd access
    a dictionary's values, but pandas lets us use dot notation too).
    """
    video_ids = get_recent_video_ids(channel_row.uploads_playlist_id, video_ids_count, api_key)
    stats_list = get_video_stats(video_ids, api_key)
 
    if len(stats_list) == 0:
        return None  # not enough data to calculate anything
 
    likes_list = [s["likes"] for s in stats_list if s["likes"] is not None]
    comments_list = [s["comments"] for s in stats_list if s["comments"] is not None]
    views_list = [s["views"] for s in stats_list if s["views"] is not None]
 
    if len(likes_list) == 0 or len(comments_list) == 0:
        return None
 
    avg_likes = sum(likes_list) / len(likes_list)
    avg_comments = sum(comments_list) / len(comments_list)
    avg_views = sum(views_list) / len(views_list) if len(views_list) > 0 else None
 
    subscribers = channel_row.subscriber_count
    if subscribers is None or subscribers == 0:
        engagement_rate = None
    else:
        engagement_rate = round((avg_likes + avg_comments) / subscribers, 5)
 
    return {
        "avg_recent_views": avg_views,
        "avg_recent_likes": avg_likes,
        "avg_recent_comments": avg_comments,
        "engagement_rate": engagement_rate,
        "videos_sampled": len(stats_list),
    }
 
 
def add_engagement_column(channels_df, video_ids_count, max_channels, api_key):
    """
    Loops through channels (up to max_channels, to stay within API quota)
    and adds engagement-rate columns to the DataFrame.
    """
    print(f"Calculating engagement rate for up to {max_channels} channels...")
 
    # only channels that actually have an uploads playlist can be checked
    channels_with_uploads = channels_df.dropna(subset=["uploads_playlist_id"])
    channels_to_check = channels_with_uploads.head(max_channels)
 
    results_by_channel_id = {}
    count = 0
    for row in channels_to_check.itertuples():
        count += 1
        engagement_info = calculate_engagement_rate(row, video_ids_count, api_key)
        if engagement_info is not None:
            results_by_channel_id[row.channel_id] = engagement_info
 
        if count % 50 == 0:
            print(f"  ...checked {count}/{len(channels_to_check)} channels")
        time.sleep(0.05)
 
    # turn the dictionary-of-dictionaries into a DataFrame, then merge it
    # onto the original channels_df using channel_id as the matching key
    engagement_df = pd.DataFrame.from_dict(results_by_channel_id, orient="index")
    engagement_df = engagement_df.reset_index().rename(columns={"index": "channel_id"})
 
    merged_df = channels_df.merge(engagement_df, on="channel_id", how="left")
    return merged_df
 
 
def fetch_all_youtube_data():
    """
    The main function that runs the whole Phase 1 pipeline:
      1. Load settings from config/settings.yaml
      2. Search for channels across every niche and region
      3. Fetch real stats for every channel found
      4. Calculate real engagement rates
      5. Return everything as one pandas DataFrame
    """
    settings = load_settings()
    youtube_settings = settings["youtube"]
    api_key = get_youtube_api_key()
 
    niches = youtube_settings["niches"]
    regions = youtube_settings["regions"]
    max_results = youtube_settings["max_results_per_search"]
    video_sample_count = youtube_settings["engagement_sample_videos"]
    max_channels_for_engagement = youtube_settings["max_channels_for_engagement"]
 
    print(f"Searching {len(niches)} niches across {len(regions)} region(s)...")
 
    # a dictionary to remember which niche/region found each channel first,
    # and a list to collect all channel IDs without duplicates
    channel_ids_found = []
    channel_source = {}  # channel_id -> (niche, region) - like Day 8 dictionary usage
 
    for niche in niches:
        for region in regions:
            ids = search_channels(niche, region, api_key, max_results)
            region_label = region if region is not None else "global"
            print(f"  {niche} / {region_label}: found {len(ids)} channels")
 
            for channel_id in ids:
                if channel_id not in channel_source:
                    channel_ids_found.append(channel_id)
                    channel_source[channel_id] = (niche, region_label)
            time.sleep(0.05)
 
    print(f"\nTotal unique channels found: {len(channel_ids_found)}")
 
    print("Fetching channel statistics...")
    channel_records = get_channel_details(channel_ids_found, api_key)
 
    # build the DataFrame from our list of dictionaries (Day 22 concept)
    channels_df = pd.DataFrame(channel_records)
 
    # add the niche/region columns using the dictionary we built earlier
    channels_df["niche_query"] = channels_df["channel_id"].map(lambda cid: channel_source[cid][0])
    channels_df["search_region"] = channels_df["channel_id"].map(lambda cid: channel_source[cid][1])
 
    channels_df = add_engagement_column(channels_df, video_sample_count, max_channels_for_engagement, api_key)
 
    return channels_df
 