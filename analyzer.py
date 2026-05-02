import json
import requests


GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"


def _ask(prompt: str, api_key: str) -> str:
    resp = requests.post(
        GEMINI_URL,
        params={"key": api_key},
        json={"contents": [{"parts": [{"text": prompt}]}]},
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json()["candidates"][0]["content"]["parts"][0]["text"]


def _top_posts(posts: list, n: int = 5) -> list:
    scored = []
    for p in posts:
        score = p["likes"] + p["comments"] * 3 + (p["views"] or 0) * 0.1
        scored.append({**p, "engagement_score": round(score)})
    return sorted(scored, key=lambda x: x["engagement_score"], reverse=True)[:n]


# ── 1. Análise do perfil ──────────────────────────────────────────────────────

def analyze_profile(profile: dict, posts: list, gemini_key: str) -> str:
    followers  = profile.get("followersCount", 0)
    following  = profile.get("followingCount", 0)
    bio        = profile.get("biography", "")
    full_name  = profile.get("fullName", "")
    username   = profile.get("username", "")

    n            = len(posts) or 1
    avg_likes    = sum(p["likes"] for p in posts) / n
    avg_comments = sum(p["comments"] for p in posts) / n
    total_views  = sum(p["views"] for p in posts if p["views"])

    type_counts: dict     = {}
    type_engagement: dict = {}
    for p in posts:
        t     = p["type"]
        score = p["likes"] + p["comments"] * 3 + (p["views"] or 0) * 0.1
        type_counts[t]     = type_counts.get(t, 0) + 1
        type_engagement[t] = type_engagement.get(t, 0) + score

    top5 = _top_posts(posts, 5)
    top5_json = json.dumps([
        {"tipo": p["type"], "curtidas": p["likes"], "comentarios": p["comments"],
         "views": p["views"], "score": p["engagement_score"],
         "legenda": (p["caption"] or "")[:200],
         "url": f"https://www.instagram.com/p/{p['shortcode']}/" if p["shortcode"] else ""}
        for p in top5
    ], ensure_ascii=False, indent=2)

    all_json = json.dumps([
        {"tipo": p["type"], "curtidas": p["likes"], "comentarios": p["comments"],
         "views": p["views"], "legenda": (p["caption"] or "")[:120],
         "hashtags": p["hashtags"][:8], "data": (p["timestamp"] or "")[:10]}
        for p in posts
    ], ensure_ascii=False, indent=2)

    prompt = f"""Você é um analista sênior de marketing digital especializado em Instagram.
Analise os dados abaixo e produza um relatório completo em português do Brasil.
Seja específico, cite números reais, não seja genérico.

# Perfil @{username} — {full_name}
Bio: {bio}
Seguidores: {followers:,} | Seguindo: {following:,} | Posts analisados: {len(posts)}

## Médias
- Curtidas/post: {avg_likes:.0f}
- Comentários/post: {avg_comments:.1f}
- Total de views em vídeos: {total_views:,}

## Quantidade por tipo: {json.dumps(type_counts, ensure_ascii=False)}
## Engajamento por tipo: {json.dumps({k: round(v) for k, v in type_engagement.items()}, ensure_ascii=False)}

## Top 5 posts
{top5_json}

## Todos os posts
{all_json}

---
Produza o relatório com EXATAMENTE estas seções:

## 📊 Resumo do Perfil
[Quem é, nicho, posicionamento — 3 frases objetivas]

## 🏆 Top 5 Posts com Maior Engajamento
[Para cada: URL, tipo, métricas e POR QUE performou bem]

## 📈 Padrões de Engajamento
[O que os posts de sucesso têm em comum: formato, horário, tom, assuntos]

## 🎯 Formato que Mais Engaja
[Reel vs Carrossel vs Foto — dados reais deste perfil]

## 📅 5 Recomendações Estratégicas
[Práticas e específicas para este perfil crescer]

## #️⃣ Hashtags
[Mais usadas nos top posts + 15 sugestões novas para testar]
"""
    return _ask(prompt, gemini_key)


# ── 2. Criativos com roteiro completo ────────────────────────────────────────

def generate_creatives(profile: dict, posts: list, gemini_key: str) -> str:
    username  = profile.get("username", "")
    followers = profile.get("followersCount", 0)
    bio       = profile.get("biography", "")

    top5 = _top_posts(posts, 5)
    top5_json = json.dumps([
        {"tipo": p["type"], "curtidas": p["likes"], "views": p["views"],
         "legenda": (p["caption"] or "")[:250]}
        for p in top5
    ], ensure_ascii=False, indent=2)

    type_engagement: dict = {}
    for p in posts:
        t = p["type"]
        type_engagement[t] = type_engagement.get(t, 0) + p["likes"] + p["comments"] * 3
    best_format = max(type_engagement, key=type_engagement.get) if type_engagement else "Reel"

    prompt = f"""Você é um roteirista e estrategista de conteúdo para Instagram.
Perfil: @{username} | {followers:,} seguidores | Bio: {bio}
Formato com melhor engajamento: {best_format}

Posts que mais engajaram (inspire-se):
{top5_json}

Crie 8 criativos COMPLETOS. Para CADA UM use EXATAMENTE esta estrutura:

---
### IDEIA [número]: [Título chamativo]

INSPIRADO EM: [qual post do top 5 inspirou e por quê]
FORMATO: [Reel / Carrossel / Foto]
OBJETIVO: [engajamento / alcance / conversão]

ROTEIRO COMPLETO:

Hook (primeiros 3 segundos):
[Frase ou cena exata de abertura que prende atenção]

Desenvolvimento:
[Descreva cena a cena ou slide a slide — o que é falado e mostrado, palavra por palavra para Reels]

CTA:
[O que pedir ao seguidor: comentar, salvar, compartilhar etc.]

LEGENDA PRONTA:
[Legenda completa com emojis e CTA, pronta para publicar]

HASHTAGS:
[10 hashtags relevantes]

---

Roteiros de Reels devem ter narração palavra por palavra. Seja criativo e específico para este nicho.
"""
    return _ask(prompt, gemini_key)


# ── 3. Ideias por tema específico ─────────────────────────────────────────────

def generate_ideas_by_topic(profile: dict, posts: list, topic: str, gemini_key: str) -> str:
    username  = profile.get("username", "")
    followers = profile.get("followersCount", 0)

    type_engagement: dict = {}
    for p in posts:
        t = p["type"]
        type_engagement[t] = type_engagement.get(t, 0) + p["likes"] + p["comments"] * 3
    best_format = max(type_engagement, key=type_engagement.get) if type_engagement else "Reel"

    prompt = f"""Você é um roteirista de conteúdo para Instagram.
Perfil: @{username} | {followers:,} seguidores | Formato que mais engaja: {best_format}
Tema: "{topic}"

Crie 5 criativos COMPLETOS sobre este tema. Para CADA UM use EXATAMENTE esta estrutura:

---
### IDEIA [número]: [Título]

FORMATO: [Reel / Carrossel / Foto]

ROTEIRO COMPLETO:

Hook (primeiros 3 segundos):
[Frase/cena exata de abertura]

Desenvolvimento:
[Cena a cena / slide a slide — o que é dito e mostrado, palavra por palavra para Reels]

CTA:
[O que pedir ao seguidor]

LEGENDA PRONTA:
[Legenda completa com emojis e CTA]

HASHTAGS:
[10 hashtags]

---
"""
    return _ask(prompt, gemini_key)
