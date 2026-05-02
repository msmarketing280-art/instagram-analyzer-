import json
from google import genai


def _client(gemini_key: str):
    return genai.Client(api_key=gemini_key)


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

    n = len(posts) or 1
    avg_likes    = sum(p["likes"] for p in posts) / n
    avg_comments = sum(p["comments"] for p in posts) / n
    total_views  = sum(p["views"] for p in posts if p["views"])

    type_counts: dict     = {}
    type_engagement: dict = {}
    for p in posts:
        t = p["type"]
        score = p["likes"] + p["comments"] * 3 + (p["views"] or 0) * 0.1
        type_counts[t]      = type_counts.get(t, 0) + 1
        type_engagement[t]  = type_engagement.get(t, 0) + score

    top5 = _top_posts(posts, 5)
    top5_summary = [
        {
            "tipo": p["type"],
            "curtidas": p["likes"],
            "comentarios": p["comments"],
            "visualizacoes": p["views"],
            "engajamento_score": p["engagement_score"],
            "legenda": (p["caption"] or "")[:200],
            "url": f"https://www.instagram.com/p/{p['shortcode']}/" if p["shortcode"] else "",
        }
        for p in top5
    ]

    all_posts_summary = [
        {
            "tipo": p["type"],
            "curtidas": p["likes"],
            "comentarios": p["comments"],
            "visualizacoes": p["views"],
            "legenda": (p["caption"] or "")[:120],
            "hashtags": p["hashtags"][:8],
            "data": (p["timestamp"] or "")[:10],
        }
        for p in posts
    ]

    prompt = f"""Você é um analista sênior de marketing digital especializado em Instagram.
Analise os dados abaixo e produza um relatório completo em português do Brasil.
Seja específico, cite números reais, não seja genérico.

# Perfil @{username} — {full_name}
Bio: {bio}
Seguidores: {followers:,} | Seguindo: {following:,}
Posts analisados: {len(posts)}

## Médias
- Curtidas/post: {avg_likes:.0f}
- Comentários/post: {avg_comments:.1f}
- Total de views em vídeos: {total_views:,}

## Quantidade por tipo
{json.dumps(type_counts, ensure_ascii=False)}

## Engajamento total por tipo
{json.dumps({k: round(v) for k, v in type_engagement.items()}, ensure_ascii=False)}

## Top 5 posts (maior engajamento)
{json.dumps(top5_summary, ensure_ascii=False, indent=2)}

## Todos os posts
{json.dumps(all_posts_summary, ensure_ascii=False, indent=2)}

---

Produza o relatório com EXATAMENTE estas seções:

## 📊 Resumo do Perfil
[Quem é esse perfil, nicho, posicionamento — 3 frases objetivas]

## 🏆 Top 5 Posts com Maior Engajamento
[Para cada um: URL, tipo, curtidas, comentários, views e análise do POR QUE performou bem]

## 📈 Padrões de Engajamento
[O que os posts de sucesso têm em comum: formato, horário, estilo de legenda, tom, assuntos]

## 🎯 Formato que Mais Engaja
[Reel vs Carrossel vs Foto: qual performa melhor neste perfil e por quê, com dados]

## 📅 Recomendações Estratégicas
[5 recomendações práticas e específicas para este perfil crescer]

## #️⃣ Hashtags
[Hashtags mais usadas nos top posts + 15 sugestões de novas hashtags para testar]
"""

    resp = _client(gemini_key).models.generate_content(model="gemini-2.0-flash", contents=prompt)
    return resp.text


# ── 2. Criativos com roteiro completo ────────────────────────────────────────

def generate_creatives(profile: dict, posts: list, gemini_key: str) -> str:
    username  = profile.get("username", "")
    followers = profile.get("followersCount", 0)
    bio       = profile.get("biography", "")

    top5 = _top_posts(posts, 5)
    top5_summary = [
        {
            "tipo": p["type"],
            "curtidas": p["likes"],
            "comentarios": p["comments"],
            "views": p["views"],
            "legenda": (p["caption"] or "")[:250],
        }
        for p in top5
    ]

    type_engagement: dict = {}
    for p in posts:
        t = p["type"]
        type_engagement[t] = type_engagement.get(t, 0) + p["likes"] + p["comments"] * 3

    best_format = max(type_engagement, key=type_engagement.get) if type_engagement else "Reel"

    prompt = f"""Você é um roteirista e estrategista de conteúdo para Instagram.
Crie 8 ideias de criativos COMPLETOS para o perfil @{username} ({followers:,} seguidores).
Bio: {bio}
Formato com melhor engajamento: {best_format}

Posts que mais engajaram (inspire-se neles):
{json.dumps(top5_summary, ensure_ascii=False, indent=2)}

---

Para CADA UMA das 8 ideias, siga EXATAMENTE esta estrutura:

---
### 💡 Ideia [número]: [Título chamativo]

**Inspirado em:** [cite qual post do top 5 inspirou e por quê]
**Formato:** [Reel / Carrossel / Foto]
**Objetivo:** [engajamento / alcance / conversão]

**🎬 ROTEIRO COMPLETO**

**Hook (primeiros 3 segundos):**
[Frase ou cena exata de abertura que prende atenção]

**Desenvolvimento:**
[Descreva cena a cena ou slide a slide o que acontece, o que é falado/escrito]

**CTA (call to action):**
[O que pedir para o seguidor fazer: comentar, salvar, compartilhar, etc.]

**📝 Legenda sugerida:**
[Legenda completa pronta para publicar, com emojis e CTA]

**#️⃣ Hashtags:**
[10 hashtags relevantes]

---

Seja criativo, específico para o nicho deste perfil. Roteiros de Reels devem ter narração palavra por palavra.
"""

    resp = _client(gemini_key).models.generate_content(model="gemini-2.0-flash", contents=prompt)
    return resp.text


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
Tema solicitado: "{topic}"

Crie 5 criativos COMPLETOS sobre este tema para este perfil.

Para CADA ideia use esta estrutura:

---
### 💡 Ideia [número]: [Título]

**Formato:** [Reel / Carrossel / Foto]

**🎬 ROTEIRO COMPLETO**

**Hook (primeiros 3 segundos):**
[Frase/cena exata de abertura]

**Desenvolvimento:**
[Cena a cena / slide a slide — o que é dito e mostrado]

**CTA:**
[O que pedir ao seguidor]

**📝 Legenda completa:**
[Legenda pronta com emojis e CTA]

**#️⃣ Hashtags:**
[10 hashtags]

---
"""
    resp = _client(gemini_key).models.generate_content(model="gemini-2.0-flash", contents=prompt)
    return resp.text
