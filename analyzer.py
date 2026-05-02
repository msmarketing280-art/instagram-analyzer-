import json
import google.generativeai as genai


SYSTEM_PROMPT = """Você é um especialista em marketing digital e criação de conteúdo para Instagram.
Analise os dados fornecidos de um perfil do Instagram e forneça insights acionáveis em português do Brasil.
Seja direto, prático e baseie todas as suas análises nos dados reais fornecidos."""


def _build_analysis_prompt(profile: dict, posts: list) -> str:
    followers = profile.get("followersCount", 0)
    following = profile.get("followingCount", 0)
    bio = profile.get("biography", "")
    full_name = profile.get("fullName", "")

    # Compute aggregate stats
    total_likes = sum(p["likes"] for p in posts)
    total_comments = sum(p["comments"] for p in posts)
    total_views = sum(p["views"] for p in posts if p["views"])
    n = len(posts) or 1
    avg_likes = total_likes / n
    avg_comments = total_comments / n

    # Top 5 posts by engagement score
    for p in posts:
        p["engagement_score"] = p["likes"] + p["comments"] * 3 + (p["views"] or 0) * 0.1
    top_posts = sorted(posts, key=lambda x: x["engagement_score"], reverse=True)[:5]

    # Type breakdown
    type_counts: dict = {}
    type_engagement: dict = {}
    for p in posts:
        t = p["type"]
        type_counts[t] = type_counts.get(t, 0) + 1
        type_engagement[t] = type_engagement.get(t, 0) + p["engagement_score"]

    posts_summary = []
    for p in posts:
        posts_summary.append(
            {
                "tipo": p["type"],
                "curtidas": p["likes"],
                "comentarios": p["comments"],
                "visualizacoes": p["views"],
                "legenda_resumo": p["caption"][:150] if p["caption"] else "",
                "hashtags": p["hashtags"][:10],
                "data": p["timestamp"],
                "url": f"https://www.instagram.com/p/{p['shortcode']}/" if p["shortcode"] else p["url"],
            }
        )

    prompt = f"""
# Dados do Perfil @{profile.get('username', '')}

**Nome:** {full_name}
**Bio:** {bio}
**Seguidores:** {followers:,}
**Seguindo:** {following:,}
**Posts analisados:** {len(posts)}

## Métricas Gerais
- Média de curtidas por post: {avg_likes:.0f}
- Média de comentários por post: {avg_comments:.1f}
- Total de visualizações (reels/vídeos): {total_views:,}

## Distribuição por tipo de conteúdo
{json.dumps(type_counts, ensure_ascii=False, indent=2)}

## Engajamento total por tipo de conteúdo
{json.dumps({k: round(v) for k, v in type_engagement.items()}, ensure_ascii=False, indent=2)}

## Top 5 posts por engajamento
{json.dumps([{"tipo": p["type"], "curtidas": p["likes"], "comentarios": p["comments"],
              "visualizacoes": p["views"], "legenda": p["caption"][:120],
              "url": f"https://www.instagram.com/p/{p['shortcode']}/"}
             for p in top_posts], ensure_ascii=False, indent=2)}

## Todos os posts (resumo)
{json.dumps(posts_summary, ensure_ascii=False, indent=2)}

---

Com base nesses dados, forneça uma análise completa estruturada EXATAMENTE assim:

## 📊 Resumo do Perfil
[2-3 frases descrevendo o perfil e posicionamento]

## 🏆 Melhores Posts
[Liste os 5 melhores posts com URL, métricas e POR QUE performaram bem]

## 📈 Padrões de Engajamento
[O que os posts de alto desempenho têm em comum? Horário, formato, estilo de legenda, hashtags, etc.]

## 🎯 Tipo de Conteúdo que Mais Engaja
[Analise qual formato (Reel, Imagem, Carrossel) traz mais resultado e por quê]

## 🎯 Tipo de Conteúdo que Mais Engaja
[Analise qual formato (Reel, Imagem, Carrossel) traz mais resultado e por quê, com base nos dados acima]

## 💡 10 Ideias de Novos Conteúdos (baseadas nos posts reais)
Para cada ideia, inspire-se DIRETAMENTE nos posts de maior engajamento listados acima.
Mencione explicitamente qual post inspirou a ideia (ex: "inspirado no reel sobre X que teve Y curtidas").
Para cada ideia inclua:
- **Formato:** Reel / Carrossel / Foto
- **Gancho de abertura:** (primeira frase que prende atenção)
- **Estrutura:** passo a passo do conteúdo
- **Legenda sugerida** com CTA
- **Hashtags:** 8 hashtags relevantes

## 📅 Recomendações Estratégicas
[3-5 recomendações práticas e específicas para crescer este perfil, baseadas nos dados]

## #️⃣ Análise de Hashtags
[Quais hashtags aparecem nos posts de maior engajamento? Sugestões de novas hashtags para testar]
"""
    return prompt


def analyze_profile(profile: dict, posts: list, gemini_key: str) -> str:
    genai.configure(api_key=gemini_key)
    model = genai.GenerativeModel("gemini-1.5-flash")
    prompt = _build_analysis_prompt(profile, posts)
    response = model.generate_content(prompt)
    return response.text


def generate_content_ideas(profile: dict, posts: list, topic: str, gemini_key: str) -> str:
    genai.configure(api_key=gemini_key)
    model = genai.GenerativeModel("gemini-1.5-flash")

    username = profile.get("username", "")
    followers = profile.get("followersCount", 0)
    top_types = {}
    for p in posts:
        top_types[p["type"]] = top_types.get(p["type"], 0) + (p["likes"] + p["comments"] * 3)

    best_format = max(top_types, key=top_types.get) if top_types else "Reel"

    prompt = f"""
{SYSTEM_PROMPT}

Perfil @{username} com {followers:,} seguidores.
Formato que mais engaja: {best_format}
Tema solicitado: "{topic}"

Crie 5 ideias detalhadas de conteúdo para Instagram sobre esse tema,
adaptadas ao estilo e audiência deste perfil específico.

Para cada ideia, inclua:
- Título/gancho de abertura
- Formato recomendado (Reel, Carrossel, Foto)
- Estrutura do conteúdo (passo a passo)
- Sugestão de legenda com CTA
- 10 hashtags relevantes
"""
    response = model.generate_content(prompt)
    return response.text
