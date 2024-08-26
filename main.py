import os
import datetime
from pytz import timezone

import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors
from googleapiclient.http import MediaFileUpload

scopes = ["https://www.googleapis.com/auth/youtube"]
CHANNEL_ID = os.getenv("CHANNEL_ID")
FILE_PATH = os.getenv("FILE_PATH")
TITLE = os.getenv("TITLE")


def get_publish_datetime(
    channel_id: str,
    youtube: googleapiclient.discovery.Resource,
    title: str = "Company of Heroes 3",
) -> datetime.datetime:
    # Retrieve the channel's upload playlist ID
    request = youtube.channels().list(part="contentDetails", id=channel_id)
    response = request.execute()
    upload_playlist_id = response["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]

    # Retrieve all playlist items (without sorting)
    playlist_items_request = youtube.playlistItems().list(
        part="snippet,contentDetails,status",
        playlistId=upload_playlist_id,
    )
    playlist_items_response = playlist_items_request.execute()
    all_videos = playlist_items_response["items"]

    private_videos = [
        video
        for video in all_videos
        if title in video["snippet"]["title"] and video["status"]["privacyStatus"] == "private"
    ]
    public_videos = [
        video
        for video in all_videos
        if title in video["snippet"]["title"] and video["status"]["privacyStatus"] == "public"
    ]

    # Sort the videos locally by published date
    sorted_public_videos = sorted(
        public_videos, key=lambda x: x["snippet"]["publishedAt"], reverse=True
    )
    private_video_count = len(private_videos)
    latest_public_date = sorted_public_videos[0]["snippet"]["publishedAt"]

    public_datetime = datetime.datetime.fromisoformat(latest_public_date)
    new_upload_datetime = public_datetime + datetime.timedelta(days=private_video_count + 1)

    new_publish_datetime = datetime.datetime.combine(
        new_upload_datetime.date(),
        datetime.time(0, 0, 0, 0, tzinfo=timezone("America/Los_Angeles")),
        tzinfo=timezone("America/Los_Angeles"),
    )

    print(f"Found {private_video_count} private videos")
    print(f"Found {latest_public_date} as the latest public video date")
    print(f"Calculated {new_publish_datetime} as new publish datetime")
    return new_publish_datetime


def upload_video(
    video_file: str,
    title: str,
    publish_time: datetime.datetime,
    youtube: googleapiclient.discovery.Resource,
    mimetype: str = "video/mkv",
) -> None:
    request_body = {
        "snippet": {
            "title": title,
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

    response = input(f"Start upload of '{title}' using '{video_file}', proceed? (y/n)").lower()
    if response == "y":
        print("Continuing...")
    else:
        print("Aborting!")

    response = (
        youtube.videos()
        .insert(part="snippet,status", body=request_body, media_body=media_body)
        .execute()
    )

    video_id = response["id"]

    print(
        f"'{title}' uploaded successfully with video id {video_id}. It will be published at {publish_time.date()}"
    )


def main():
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

    publish_datetime = get_publish_datetime(CHANNEL_ID, youtube)
    upload_video(FILE_PATH, TITLE, publish_datetime, youtube)


if __name__ == "__main__":
    main()
