"""
upload_to_youtube.py — StoicElderWisdom
Uploads final_with_subs.mp4 to YouTube and posts a pinned comment.
Credentials: client_secrets.json + token.json (StoicElderWisdom channel).
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
VIDEO_PATH     = Path("output/final_with_subs.mp4")
THUMBNAIL_PATH = Path("output/thumbnails/01_main.jpg")

VIDEO_TITLE       = "StoicElderWisdom — Ancient Wisdom for Men"
VIDEO_DESCRIPTION = (
    "Subscribe to StoicElderWisdom — ancient principles for men who've earned their perspective.\n\n"
    "📖 FREE CHAPTER — Get Chapter 5 free → stoicelderwisdom.kit.com/free-chapter"
)
VIDEO_TAGS        = ["stoicism", "marcus aurelius", "stoic wisdom", "wisdom for men", "men over 50"]
CATEGORY_ID       = "27"
PRIVACY           = "public"
SCOPES            = ["https://www.googleapis.com/auth/youtube.force-ssl"]


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


def upload_video(youtube) -> str:
    print(f"Uploading: {VIDEO_PATH}")
    body = {
        "snippet": {
            "title":       VIDEO_TITLE,
            "description": VIDEO_DESCRIPTION.strip(),
            "tags":        VIDEO_TAGS,
            "categoryId":  CATEGORY_ID,
        },
        "status": {
            "privacyStatus":          PRIVACY,
            "selfDeclaredMadeForKids": False,
        },
    }
    media       = MediaFileUpload(str(VIDEO_PATH), mimetype="video/mp4",
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
                pct = int(status.progress() * 100)
                print(f"  Upload progress: {pct}%", end="\r")
        except (TimeoutError, socket.timeout, ConnectionError, OSError) as e:
            retries += 1
            if retries > MAX_RETRIES:
                raise
            wait = min(2 ** retries, 120)
            print(f"\n  Network error ({type(e).__name__}), retry {retries}/{MAX_RETRIES} in {wait}s...")
            _time.sleep(wait)

    video_id = response["id"]
    print(f"\n  Uploaded! Video ID: {video_id}")
    print(f"  URL: https://www.youtube.com/watch?v={video_id}")
    return video_id


def set_thumbnail(youtube, video_id: str) -> None:
    if not THUMBNAIL_PATH.exists():
        print(f"  Thumbnail not found: {THUMBNAIL_PATH} — skipping")
        return
    print(f"Setting thumbnail: {THUMBNAIL_PATH}")
    youtube.thumbnails().set(
        videoId=video_id,
        media_body=MediaFileUpload(str(THUMBNAIL_PATH), mimetype="image/jpeg"),
    ).execute()
    print("  Thumbnail set.")


PINNED_CTA = (
    "\n\n📖 FREE CHAPTER — \"What the Stoics Knew About Getting Old\"\n"
    "The Stoics didn't write for young men chasing success. They wrote for men trying to live and die well.\n"
    "Get Chapter 5 free → stoicelderwisdom.kit.com/free-chapter"
)


PLAYLISTS_FILE = Path("playlists.json")

SERIES_DESCRIPTIONS = {
    "Letting Go":      "Stoic wisdom for men who are ready to release regret, grief, and the weight of the past.",
    "Who Am I Now":    "Stoic guidance for men navigating identity, purpose, and meaning after major life transitions.",
    "The Long Marriage": "Ancient wisdom for men facing the complexity of long relationships, family, and love over time.",
    "Making Peace":    "Stoic principles for men learning to accept aging, mortality, and the life they've lived.",
    "What Remains":    "Stoic reflections on legacy, what matters, and how a man's life echoes beyond his years.",
}


def ensure_playlist(youtube, series_name: str) -> str:
    """Return playlist ID for the given series — create it if it doesn't exist."""
    playlists = {}
    if PLAYLISTS_FILE.exists():
        playlists = json.loads(PLAYLISTS_FILE.read_text(encoding="utf-8"))

    if series_name in playlists:
        print(f"  Playlist found: '{series_name}' → {playlists[series_name]}")
        return playlists[series_name]

    # Create the playlist
    print(f"  Creating playlist: '{series_name}'...")
    description = SERIES_DESCRIPTIONS.get(series_name, f"StoicElderWisdom — {series_name} series.")
    resp = youtube.playlists().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title":       f"StoicElderWisdom: {series_name}",
                "description": description,
                "tags":        ["stoicism", "wisdom for men", "men over 50", series_name.lower()],
            },
            "status": {"privacyStatus": "public"},
        },
    ).execute()
    playlist_id = resp["id"]
    playlists[series_name] = playlist_id
    PLAYLISTS_FILE.write_text(json.dumps(playlists, indent=2), encoding="utf-8")
    print(f"  Playlist created: {playlist_id}")
    return playlist_id


def add_to_playlist(youtube, video_id: str, playlist_id: str) -> None:
    try:
        youtube.playlistItems().insert(
            part="snippet",
            body={
                "snippet": {
                    "playlistId": playlist_id,
                    "resourceId": {"kind": "youtube#video", "videoId": video_id},
                }
            },
        ).execute()
        print(f"  Added to playlist: https://www.youtube.com/playlist?list={playlist_id}")
    except Exception as e:
        print(f"  Playlist add failed: {e}")


def post_comment(youtube, video_id: str) -> None:
    comment_file = Path("output/pinned_comment.txt")
    if not comment_file.exists():
        print("  No pinned_comment.txt — skipping comment.")
        return
    text = comment_file.read_text(encoding="utf-8").strip()
    if not text:
        return
    text = text + PINNED_CTA
    try:
        youtube.commentThreads().insert(
            part="snippet",
            body={
                "snippet": {
                    "videoId": video_id,
                    "topLevelComment": {
                        "snippet": {"textOriginal": text}
                    },
                }
            },
        ).execute()
        print("  Comment posted. (Pin it in YouTube Studio to make it sticky.)")
    except Exception as e:
        print(f"  Comment post failed: {e}")


def main():
    global VIDEO_TITLE, VIDEO_DESCRIPTION, VIDEO_TAGS, THUMBNAIL_PATH

    series_name = "Making Peace"   # default
    meta_file   = Path("output/youtube_meta.json")
    if meta_file.exists():
        m = json.loads(meta_file.read_text(encoding="utf-8"))
        VIDEO_TITLE  = m.get("title",       VIDEO_TITLE)
        VIDEO_TAGS   = m.get("tags",         VIDEO_TAGS)
        series_name  = m.get("series",       series_name)
        thumb_id     = m.get("thumbnail_id")
        if thumb_id:
            THUMBNAIL_PATH = Path(f"output/thumbnails/{thumb_id}.jpg")
        print(f"Loaded metadata from output/youtube_meta.json")
        print(f"Title:  {VIDEO_TITLE}")
        print(f"Series: {series_name}")

    if not CLIENT_SECRETS.exists():
        print(f"ERROR: {CLIENT_SECRETS} not found.")
        sys.exit(1)
    if not VIDEO_PATH.exists():
        print(f"ERROR: {VIDEO_PATH} not found. Run generate_subtitles.py first.")
        sys.exit(1)

    print("Authenticating with YouTube (StoicElderWisdom channel)...")
    youtube = get_authenticated_service()

    # Ensure series playlist exists before building description
    playlist_id  = ensure_playlist(youtube, series_name)
    playlist_url = f"https://www.youtube.com/playlist?list={playlist_id}"

    # Build description — free chapter FIRST (shows without clicking "more"), then body
    if meta_file.exists():
        m = json.loads(meta_file.read_text(encoding="utf-8"))
        base_desc = m.get("description", VIDEO_DESCRIPTION)
    else:
        base_desc = VIDEO_DESCRIPTION

    free_chapter_header = (
        "FREE CHAPTER: stoicelderwisdom.kit.com/free-chapter\n"
        "\"What the Stoics Knew About Getting Old\" — Chapter 5 is yours, no cost.\n\n"
    )
    series_line = f"\nPart of the '{series_name}' series: {playlist_url}\n"
    transparency = (
        "\n\nThis channel uses AI tools to research and structure ancient wisdom. "
        "The mission and the message are real.\n"
    )
    VIDEO_DESCRIPTION = free_chapter_header + base_desc + series_line + transparency

    video_id = upload_video(youtube)
    set_thumbnail(youtube, video_id)
    add_to_playlist(youtube, video_id, playlist_id)
    post_comment(youtube, video_id)

    meta = {"video_id": video_id, "title": VIDEO_TITLE,
            "series": series_name, "playlist_id": playlist_id}
    Path("output/video_meta.json").write_text(json.dumps(meta), encoding="utf-8")

    # Merge video_id into video_info.json so teaser shorts can reference it
    info_file = Path("output/video_info.json")
    if info_file.exists():
        info = json.loads(info_file.read_text(encoding="utf-8"))
        info["video_id"] = video_id
        info_file.write_text(json.dumps(info, indent=2), encoding="utf-8")
    print(f"  Saved: output/video_meta.json")
    print(f"\nDone! Watch your video: https://www.youtube.com/watch?v={video_id}")


if __name__ == "__main__":
    main()
