import time
from apify_client import ApifyClient


def get_profile_and_posts(username: str, apify_token: str, max_posts: int = 30) -> dict:
    """
    Scrapes Instagram profile info and recent posts/reels using Apify.
    Returns a dict with 'profile' and 'posts' keys.
    """
    client = ApifyClient(apify_token)
    clean_username = username.lstrip("@").strip()

    # ── 1. Profile info ──────────────────────────────────────────────────────
    profile_run = client.actor("apify/instagram-profile-scraper").call(
        run_input={"usernames": [clean_username]}
    )
    profile_items = list(
        client.dataset(profile_run["defaultDatasetId"]).iterate_items()
    )
    profile = profile_items[0] if profile_items else {}

    # ── 2. Posts + Reels ─────────────────────────────────────────────────────
    posts_run = client.actor("apify/instagram-scraper").call(
        run_input={
            "directUrls": [f"https://www.instagram.com/{clean_username}/"],
            "resultsType": "posts",
            "resultsLimit": max_posts,
            "addParentData": False,
        }
    )
    posts = list(
        client.dataset(posts_run["defaultDatasetId"]).iterate_items()
    )

    return {"profile": profile, "posts": posts}


def parse_posts(raw_posts: list) -> list:
    """Normalises raw Apify post records into a clean list of dicts."""
    cleaned = []
    for p in raw_posts:
        post_type = p.get("type", "").lower()  # "Video", "Image", "Sidecar"
        is_reel = post_type == "video" or p.get("isVideo", False)

        cleaned.append(
            {
                "id": p.get("id", ""),
                "url": p.get("url", p.get("shortCode", "")),
                "shortcode": p.get("shortCode", ""),
                "type": "Reel" if is_reel else ("Carrossel" if post_type == "sidecar" else "Imagem"),
                "caption": (p.get("caption") or "")[:300],
                "timestamp": p.get("timestamp", ""),
                "likes": p.get("likesCount", 0) or 0,
                "comments": p.get("commentsCount", 0) or 0,
                "views": p.get("videoViewCount", 0) or p.get("videoPlayCount", 0) or 0,
                "thumbnail": p.get("displayUrl", ""),
                "hashtags": p.get("hashtags", []),
            }
        )
    return cleaned
