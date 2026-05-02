import os
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

from scraper import get_profile_and_posts, parse_posts
from analyzer import analyze_profile, generate_content_ideas

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Instagram Analyzer",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 12px;
        color: white;
        text-align: center;
        margin: 5px 0;
    }
    .metric-value { font-size: 2rem; font-weight: bold; }
    .metric-label { font-size: 0.9rem; opacity: 0.9; margin-top: 4px; }
    .post-card {
        border: 1px solid #e0e0e0;
        border-radius: 10px;
        padding: 15px;
        margin: 8px 0;
        background: #fafafa;
    }
    .reel-badge { background: #ff6b6b; color: white; padding: 2px 8px; border-radius: 10px; font-size: 0.75rem; }
    .image-badge { background: #4ecdc4; color: white; padding: 2px 8px; border-radius: 10px; font-size: 0.75rem; }
    .carrossel-badge { background: #45b7d1; color: white; padding: 2px 8px; border-radius: 10px; font-size: 0.75rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Sidebar: credentials ──────────────────────────────────────────────────────
with st.sidebar:
    st.title("⚙️ Configurações")
    st.markdown("---")

    def _secret(key: str) -> str:
        """Reads from Streamlit secrets (cloud) or env vars (local)."""
        try:
            return st.secrets.get(key, os.getenv(key, ""))
        except Exception:
            return os.getenv(key, "")

    apify_token = st.text_input(
        "Apify API Token",
        type="password",
        value=_secret("APIFY_TOKEN"),
        help="Encontre em apify.com → Settings → Integrations",
    )
    gemini_key = st.text_input(
        "Gemini API Key",
        type="password",
        value=_secret("GEMINI_API_KEY"),
        help="Encontre em aistudio.google.com → Get API key (gratuito)",
    )
    max_posts = st.slider("Máximo de posts a analisar", 10, 50, 30, 5)

    st.markdown("---")
    st.markdown(
        "**Como usar:**\n"
        "1. Insira suas API keys\n"
        "2. Digite o @ do perfil\n"
        "3. Clique em Analisar\n\n"
        "[Criar conta Apify](https://apify.com) · "
        "[Pegar chave Gemini](https://aistudio.google.com)"
    )

# ── Main UI ───────────────────────────────────────────────────────────────────
st.title("📊 Instagram Profile Analyzer")
st.markdown("Análise completa de perfil com IA — métricas, engajamento e ideias de conteúdo.")

col_input, col_btn = st.columns([4, 1])
with col_input:
    username_input = st.text_input(
        "Perfil do Instagram",
        placeholder="@username ou username",
        label_visibility="collapsed",
    )
with col_btn:
    analyze_btn = st.button("🔍 Analisar", use_container_width=True, type="primary")

# ── Run analysis ──────────────────────────────────────────────────────────────
if analyze_btn:
    if not apify_token or not gemini_key:
        st.error("Por favor, insira as API keys no painel lateral.")
        st.stop()
    if not username_input.strip():
        st.error("Digite um nome de usuário.")
        st.stop()

    with st.spinner("Coletando dados do Instagram via Apify..."):
        try:
            raw = get_profile_and_posts(username_input, apify_token, max_posts)
            profile = raw["profile"]
            posts = parse_posts(raw["posts"])
            st.session_state["profile"] = profile
            st.session_state["posts"] = posts
        except Exception as e:
            st.error(f"Erro ao coletar dados: {e}")
            st.stop()

    with st.spinner("Analisando com Gemini IA..."):
        try:
            analysis = analyze_profile(profile, posts, gemini_key)
            st.session_state["analysis"] = analysis
            st.session_state["gemini_key"] = gemini_key
        except Exception as e:
            st.error(f"Erro na análise com Gemini: {e}")
            st.stop()

# ── Display results if available ──────────────────────────────────────────────
if "profile" in st.session_state:
    profile = st.session_state["profile"]
    posts: list = st.session_state["posts"]
    analysis: str = st.session_state.get("analysis", "")

    username = profile.get("username", username_input.lstrip("@"))

    # ── Profile header ────────────────────────────────────────────────────────
    st.markdown("---")
    hcol1, hcol2 = st.columns([1, 3])
    with hcol1:
        if profile.get("profilePicUrl"):
            st.image(profile["profilePicUrl"], width=120)
    with hcol2:
        st.subheader(f"@{username}")
        if profile.get("fullName"):
            st.markdown(f"**{profile['fullName']}**")
        if profile.get("biography"):
            st.markdown(profile["biography"])
        if profile.get("externalUrl"):
            st.markdown(f"[{profile['externalUrl']}]({profile['externalUrl']})")

    # ── Key metrics ───────────────────────────────────────────────────────────
    st.markdown("### Métricas Principais")
    m1, m2, m3, m4, m5 = st.columns(5)
    metrics = [
        (m1, profile.get("followersCount", 0), "Seguidores"),
        (m2, profile.get("followingCount", 0), "Seguindo"),
        (m3, profile.get("postsCount", len(posts)), "Posts"),
        (m4, f"{sum(p['likes'] for p in posts) / len(posts):.0f}" if posts else "0", "Média Curtidas"),
        (m5, f"{sum(p['comments'] for p in posts) / len(posts):.1f}" if posts else "0", "Média Comentários"),
    ]
    for col, value, label in metrics:
        with col:
            formatted = f"{value:,}" if isinstance(value, int) else str(value)
            st.markdown(
                f'<div class="metric-card"><div class="metric-value">{formatted}</div>'
                f'<div class="metric-label">{label}</div></div>',
                unsafe_allow_html=True,
            )

    # ── Tabs ──────────────────────────────────────────────────────────────────
    tab1, tab2, tab3, tab4 = st.tabs(["📈 Análise IA + Ideias", "🏆 Top Posts", "📊 Gráficos", "💡 Ideias por Tema"])

    # ── Tab 1: AI Analysis ────────────────────────────────────────────────────
    with tab1:
        if analysis:
            # Botão de download
            st.download_button(
                label="⬇️ Baixar análise completa (.txt)",
                data=analysis,
                file_name=f"analise_{username}_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
                mime="text/plain",
                use_container_width=False,
            )
            st.markdown("---")
            st.markdown(analysis)
        else:
            st.info("Análise não disponível.")

    # ── Tab 2: Top Posts ──────────────────────────────────────────────────────
    with tab2:
        if not posts:
            st.info("Nenhum post encontrado.")
        else:
            for p in posts:
                p["engagement_score"] = p["likes"] + p["comments"] * 3 + (p["views"] or 0) * 0.1

            sorted_posts = sorted(posts, key=lambda x: x["engagement_score"], reverse=True)

            for i, p in enumerate(sorted_posts[:10], 1):
                with st.container():
                    pc1, pc2 = st.columns([3, 1])
                    with pc1:
                        badge_color = {"Reel": "reel", "Imagem": "image", "Carrossel": "carrossel"}.get(p["type"], "image")
                        st.markdown(
                            f'<span class="{badge_color}-badge">{p["type"]}</span> '
                            f'**#{i}** · {p["timestamp"][:10] if p["timestamp"] else ""}',
                            unsafe_allow_html=True,
                        )
                        caption = p["caption"] or "_sem legenda_"
                        st.markdown(f"> {caption[:200]}{'...' if len(p['caption'] or '') > 200 else ''}")
                        if p["shortcode"]:
                            st.markdown(f"[Ver no Instagram](https://www.instagram.com/p/{p['shortcode']}/)")
                    with pc2:
                        st.metric("Curtidas", f"{p['likes']:,}")
                        st.metric("Comentários", f"{p['comments']:,}")
                        if p["views"]:
                            st.metric("Visualizações", f"{p['views']:,}")
                    st.markdown("---")

    # ── Tab 3: Charts ─────────────────────────────────────────────────────────
    with tab3:
        if not posts:
            st.info("Sem dados para exibir gráficos.")
        else:
            df = pd.DataFrame(posts)

            gcol1, gcol2 = st.columns(2)

            # Engagement by type
            with gcol1:
                type_df = df.groupby("type").agg(
                    curtidas=("likes", "mean"),
                    comentarios=("comments", "mean"),
                    quantidade=("id", "count"),
                ).reset_index()
                fig_type = px.bar(
                    type_df,
                    x="type",
                    y="curtidas",
                    color="type",
                    title="Média de Curtidas por Tipo de Conteúdo",
                    text="quantidade",
                    labels={"type": "Tipo", "curtidas": "Média de Curtidas"},
                )
                fig_type.update_traces(texttemplate="%{text} posts", textposition="outside")
                st.plotly_chart(fig_type, use_container_width=True)

            # Likes vs Comments scatter
            with gcol2:
                fig_scatter = px.scatter(
                    df,
                    x="likes",
                    y="comments",
                    color="type",
                    size="views" if df["views"].sum() > 0 else None,
                    hover_data=["caption"],
                    title="Curtidas vs Comentários",
                    labels={"likes": "Curtidas", "comments": "Comentários", "type": "Tipo"},
                )
                st.plotly_chart(fig_scatter, use_container_width=True)

            # Timeline
            df_time = df.copy()
            df_time["timestamp"] = pd.to_datetime(df_time["timestamp"], errors="coerce")
            df_time = df_time.dropna(subset=["timestamp"]).sort_values("timestamp")
            if not df_time.empty:
                fig_line = px.line(
                    df_time,
                    x="timestamp",
                    y="likes",
                    color="type",
                    markers=True,
                    title="Evolução de Curtidas ao Longo do Tempo",
                    labels={"timestamp": "Data", "likes": "Curtidas", "type": "Tipo"},
                )
                st.plotly_chart(fig_line, use_container_width=True)

            # Top hashtags
            all_hashtags: dict = {}
            for p in posts:
                for tag in p.get("hashtags", []):
                    all_hashtags[tag] = all_hashtags.get(tag, 0) + 1
            if all_hashtags:
                top_tags = sorted(all_hashtags.items(), key=lambda x: x[1], reverse=True)[:15]
                tag_df = pd.DataFrame(top_tags, columns=["hashtag", "frequência"])
                fig_tags = px.bar(
                    tag_df,
                    x="frequência",
                    y="hashtag",
                    orientation="h",
                    title="Hashtags Mais Usadas",
                    color="frequência",
                    color_continuous_scale="Purples",
                )
                fig_tags.update_layout(yaxis={"categoryorder": "total ascending"})
                st.plotly_chart(fig_tags, use_container_width=True)

    # ── Tab 4: Content Ideas by Topic ────────────────────────────────────────
    with tab4:
        st.markdown("### Ideias de Conteúdo por Tema Específico")
        st.markdown("Quer explorar um tema em particular? A IA cria ideias personalizadas para este perfil.")

        topic = st.text_input("Tema do conteúdo", placeholder="Ex: receitas saudáveis, dicas de produtividade, moda verão...")

        if st.button("✨ Gerar Ideias por Tema", type="primary"):
            if not topic.strip():
                st.warning("Digite um tema.")
            else:
                _gkey = st.session_state.get("gemini_key", gemini_key)
                with st.spinner("Gerando ideias com Gemini..."):
                    try:
                        ideas = generate_content_ideas(profile, posts, topic, _gkey)
                        st.download_button(
                            label="⬇️ Baixar ideias (.txt)",
                            data=ideas,
                            file_name=f"ideias_{username}_{topic[:20]}_{datetime.now().strftime('%Y%m%d')}.txt",
                            mime="text/plain",
                        )
                        st.markdown(ideas)
                    except Exception as e:
                        st.error(f"Erro ao gerar ideias: {e}")
