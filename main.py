import os
import datetime
import sys

import click
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors
from googleapiclient.http import MediaFileUpload

scopes = ["https://www.googleapis.com/auth/youtube"]
FILE_PATH = os.getenv("FILE_PATH")
TITLE = os.getenv("TITLE")


def get_publish_datetime(
    youtube: googleapiclient.discovery.Resource,
    search_title: str = "Company of Heroes 3 ",
    private_video_count: int = -1,
) -> datetime.datetime:
    # Retrieve the channel's upload playlist ID
    request = youtube.channels().list(part="contentDetails", mine=True)
    response = request.execute()
    upload_playlist_id = response["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]

    # Retrieve all playlist items (without sorting)
    playlist_items_request = youtube.playlistItems().list(
        part="snippet,contentDetails,status",
        playlistId=upload_playlist_id,
    )
    playlist_items_response = playlist_items_request.execute()
    all_videos = playlist_items_response["items"]
    next_page_token = playlist_items_response.get("nextPageToken")

    while next_page_token:
        playlist_items_request = youtube.playlistItems().list(
            part="snippet,contentDetails,status",
            playlistId=upload_playlist_id,
            pageToken=next_page_token,
        )
        playlist_items_response = playlist_items_request.execute()
        all_videos.extend(playlist_items_response["items"])
        next_page_token = playlist_items_response.get("nextPageToken")

    if private_video_count == -1:
        private_videos = [
            video
            for video in all_videos
            if search_title in video["snippet"]["title"]
            and video["status"]["privacyStatus"] == "private"
        ]
        private_video_count = len(private_videos)

    public_videos = [
        video
        for video in all_videos
        if search_title in video["snippet"]["title"]
        and video["status"]["privacyStatus"] == "public"
    ]

    # Sort the videos locally by published date
    sorted_public_videos = sorted(
        public_videos, key=lambda x: x["snippet"]["publishedAt"], reverse=True
    )

    latest_public_date = sorted_public_videos[0]["snippet"]["publishedAt"]

    public_datetime = datetime.datetime.fromisoformat(latest_public_date)
    new_upload_datetime = public_datetime + datetime.timedelta(days=private_video_count + 1)

    new_publish_datetime = datetime.datetime.combine(
        new_upload_datetime.date(),
        datetime.time(7, 0, 0, 0),
    )

    print(f"Found {private_video_count} private videos")
    print(f"Found {latest_public_date} as the latest public video date")
    print(f"Calculated {new_publish_datetime} as new publish datetime")
    return new_publish_datetime


def upload_video(
    video_file: str,
    video_title: str,
    publish_time: datetime.datetime,
    youtube: googleapiclient.discovery.Resource,
    mimetype: str = "video/mkv",
) -> None:
    request_body = {
        "snippet": {
            "title": video_title,
            "categoryId": "1",
        },
        "status": {
            "privacyStatus": "private",
            "publishAt": publish_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
    }

    chunk_size = 1024 * 1024 * 5  # 5 MB chunks
    media_body = MediaFileUpload(
        video_file, chunksize=chunk_size, mimetype=mimetype, resumable=True
    )

    response = input(
        f"Start upload of '{video_title}' using '{video_file}', proceed? (y/n)"
    ).lower()
    if response == "y":
        print("Continuing...")
    else:
        print("Aborting!")
        sys.exit()

    response = (
        youtube.videos()
        .insert(part="snippet,status", body=request_body, media_body=media_body)
        .execute()
    )

    video_id = response["id"]

    print(
        f"'{video_title}' uploaded successfully with video id {video_id}. It will be published at {publish_time.date()}"
    )


def google_yt_oauth() -> googleapiclient.discovery.Resource:
    # Disable OAuthlib's HTTPS verification when running locally.
    # *DO NOT* leave this option enabled in production.
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

    api_service_name = "youtube"
    api_version = "v3"
    client_secrets_file = "desktop_client_secrets.json"

    # Get credentials and create an API client
    flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
        client_secrets_file, scopes
    )
    credentials = flow.run_local_server(port=0)
    youtube = googleapiclient.discovery.build(
        api_service_name, api_version, credentials=credentials
    )
    return youtube


@click.command()
@click.option("--private-video-count", required=False, default=-1, type=int)
def main(private_video_count: int):
    youtube = google_yt_oauth()
    publish_datetime = get_publish_datetime(youtube, private_video_count=private_video_count)
    upload_video(FILE_PATH, TITLE, publish_datetime, youtube)


if __name__ == "__main__":
    main()
