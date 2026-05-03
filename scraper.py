import requests


def get_profile_and_posts(username: str, surge_token: str, max_posts: int = 30,
                          base_url: str = "http://localhost:3000") -> dict:
    """
    Busca perfil + posts via SurgeIG API.
    Retorna dict com chaves 'profile' e 'posts'.
    """
    clean = username.lstrip("@").strip()
    url   = f"{base_url.rstrip('/')}/api/v1/profile/{clean}"

    resp = requests.get(
        url,
        params={"token": surge_token},
        headers={"Authorization": f"Bearer {surge_token}"},
        timeout=60,
    )

    if not resp.ok:
        raise Exception(f"SurgeIG API erro {resp.status_code}: {resp.text[:300]}")

    data = resp.json()

    # A API pode retornar { profile: {...}, posts: [...] }
    # ou um objeto flat com os campos do perfil + posts embutidos
    if "profile" in data and "posts" in data:
        profile = data["profile"]
        posts   = data["posts"][:max_posts]
    elif "data" in data:
        inner   = data["data"]
        profile = inner.get("profile", inner)
        posts   = inner.get("posts", [])[:max_posts]
    else:
        # Tenta extrair direto do objeto raiz
        profile = {k: v for k, v in data.items() if not isinstance(v, list)}
        posts   = next((v for v in data.values() if isinstance(v, list)), [])[:max_posts]

    return {"profile": profile, "posts": posts}


def parse_posts(raw_posts: list) -> list:
    """Normaliza posts da SurgeIG para o formato padrão do app."""
    cleaned = []
    for p in raw_posts:
        # Suporte a diferentes convenções de campo
        post_type = (
            p.get("type") or p.get("mediaType") or p.get("media_type") or ""
        ).lower()

        is_reel = (
            post_type in ("video", "reel")
            or p.get("isVideo", False)
            or p.get("is_video", False)
        )
        is_carousel = post_type in ("sidecar", "carousel", "carrossel")

        shortcode = (
            p.get("shortCode") or p.get("shortcode") or
            p.get("code") or p.get("id", "")
        )

        likes = (
            p.get("likesCount") or p.get("likes_count") or
            p.get("likes") or p.get("likeCount") or 0
        )
        comments = (
            p.get("commentsCount") or p.get("comments_count") or
            p.get("comments") or p.get("commentCount") or 0
        )
        views = (
            p.get("videoViewCount") or p.get("video_view_count") or
            p.get("videoPlayCount") or p.get("views") or
            p.get("playCount") or 0
        )
        caption = (
            p.get("caption") or p.get("text") or
            p.get("description") or ""
        )
        timestamp = (
            p.get("timestamp") or p.get("takenAt") or
            p.get("taken_at") or p.get("date") or ""
        )
        thumbnail = (
            p.get("displayUrl") or p.get("thumbnail") or
            p.get("image_url") or p.get("imageUrl") or ""
        )
        hashtags = (
            p.get("hashtags") or p.get("tags") or []
        )

        cleaned.append({
            "id":        str(p.get("id", shortcode)),
            "url":       p.get("url", ""),
            "shortcode": str(shortcode),
            "type":      "Reel" if is_reel else ("Carrossel" if is_carousel else "Imagem"),
            "caption":   str(caption)[:300],
            "timestamp": str(timestamp),
            "likes":     int(likes or 0),
            "comments":  int(comments or 0),
            "views":     int(views or 0),
            "thumbnail": thumbnail,
            "hashtags":  hashtags if isinstance(hashtags, list) else [],
        })
    return cleaned
