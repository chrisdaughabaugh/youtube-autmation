"""
upload_short.py — StoicElderWisdom
Uploads output/short.mp4 as a YouTube Short, posts a comment linking to the full video.
"""
import json
import os
import socket
import sys
import time as _time
from pathlib import Path

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

CLIENT_SECRETS = Path("client_secrets.json")
TOKEN_FILE     = Path("token.json")
SHORT_PATH     = Path("output/short.mp4")
META_FILE      = Path("output/video_meta.json")
SCOPES         = ["https://www.googleapis.com/auth/youtube.force-ssl"]


def _restore_credentials_from_env():
    token_json = os.environ.get("YOUTUBE_TOKEN_JSON")
    client_secrets_json = os.environ.get("YOUTUBE_CLIENT_SECRETS")
    if token_json and not TOKEN_FILE.exists():
        TOKEN_FILE.write_text(token_json)
    if client_secrets_json and not CLIENT_SECRETS.exists():
        CLIENT_SECRETS.write_text(client_secrets_json)


_restore_credentials_from_env()


def get_authenticated_service():
    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow  = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRETS), SCOPES)
            creds = flow.run_local_server(port=0)
        TOKEN_FILE.write_text(creds.to_json())
    return build("youtube", "v3", credentials=creds)


def upload_short(youtube, main_video_id: str, main_title: str) -> str:
    short_title_base = main_title.split(" — ")[0].split(" (")[0]
    short_title      = f"{short_title_base} #Shorts"[:100]

    description = (
        f"FREE CHAPTER: stoicelderwisdom.kit.com/free-chapter\n\n"
        f"Watch the full video: https://www.youtube.com/watch?v={main_video_id}\n\n"
        f"Subscribe for weekly stoic wisdom for men.\n\n"
        f"#Stoicism #MarcusAurelius #StoicWisdom #Shorts #StoicElderWisdom"
    )

    print(f"Uploading Short: {SHORT_PATH}")
    print(f"Title: {short_title}")

    body = {
        "snippet": {
            "title":       short_title,
            "description": description,
            "tags":        ["shorts", "stoicism", "marcus aurelius", "stoic wisdom",
                            "wisdom for men", "men over 50", "stoic elder wisdom"],
            "categoryId":  "27",
        },
        "status": {
            "privacyStatus":           "public",
            "selfDeclaredMadeForKids": False,
        },
    }

    media       = MediaFileUpload(str(SHORT_PATH), mimetype="video/mp4",
                                  resumable=True, chunksize=8 * 1024 * 1024)
    request     = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    response    = None
    retries     = 0
    MAX_RETRIES = 10
    while response is None:
        try:
            status, response = request.next_chunk()
            retries = 0
            if status:
                print(f"  Upload progress: {int(status.progress() * 100)}%", end="\r")
        except (TimeoutError, socket.timeout, ConnectionError, OSError) as e:
            retries += 1
            if retries > MAX_RETRIES:
                raise
            wait = min(2 ** retries, 120)
            print(f"\n  Network error ({type(e).__name__}), retry {retries}/{MAX_RETRIES} in {wait}s...")
            _time.sleep(wait)

    short_id = response["id"]
    print(f"\n  Uploaded! Short ID: {short_id}")
    print(f"  URL: https://www.youtube.com/shorts/{short_id}")
    return short_id


def post_comment(youtube, short_id: str, main_video_id: str) -> None:
    text = (
        f"Watch the full video here 👉 https://www.youtube.com/watch?v={main_video_id}\n\n"
        f"📖 FREE CHAPTER — \"What the Stoics Knew About Getting Old\"\n"
        f"The Stoics didn't write for young men chasing success. They wrote for men trying to live and die well.\n"
        f"Get Chapter 5 free → stoicelderwisdom.kit.com/free-chapter\n\n"
        f"Subscribe for weekly stoic wisdom 🔔"
    )
    try:
        youtube.commentThreads().insert(
            part="snippet",
            body={
                "snippet": {
                    "videoId": short_id,
                    "topLevelComment": {"snippet": {"textOriginal": text}},
                }
            },
        ).execute()
        print("  Comment posted: full video link.")
    except Exception as e:
        print(f"  Comment post failed: {e}")


def main():
    if not SHORT_PATH.exists():
        print(f"ERROR: {SHORT_PATH} not found. Run generate_short.py first.")
        sys.exit(1)
    if not META_FILE.exists():
        print(f"ERROR: {META_FILE} not found. Run upload_to_youtube.py first.")
        sys.exit(1)

    meta          = json.loads(META_FILE.read_text())
    main_video_id = meta["video_id"]
    main_title    = meta["title"]

    print("Authenticating with YouTube (StoicElderWisdom channel)...")
    youtube  = get_authenticated_service()
    short_id = upload_short(youtube, main_video_id, main_title)
    post_comment(youtube, short_id, main_video_id)
    print("Short is live.")


if __name__ == "__main__":
    main()
