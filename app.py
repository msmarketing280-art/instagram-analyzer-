import os
import json
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from pathlib import Path
from fpdf import FPDF

from scraper import get_profile_and_posts, parse_posts
from analyzer import analyze_profile, generate_creatives, generate_ideas_by_topic


def make_pdf(title: str, content: str) -> bytes:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, title, ln=True)
    pdf.set_font("Helvetica", "", 11)
    pdf.ln(4)
    for line in content.splitlines():
        # Remove markdown bold/italic markers for clean PDF
        clean = line.replace("**", "").replace("*", "").replace("##", "").replace("#", "")
        # Encode to latin-1, replacing unsupported chars
        safe = clean.encode("latin-1", errors="replace").decode("latin-1")
        pdf.multi_cell(0, 7, safe)
    return pdf.output()

# ── Persistent config ─────────────────────────────────────────────────────────
CONFIG_FILE = Path(__file__).parent / ".keys.json"

def load_keys() -> dict:
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text())
        except Exception:
            return {}
    return {}

def save_keys(apify: str, gemini: str):
    CONFIG_FILE.write_text(json.dumps({"APIFY_TOKEN": apify, "GEMINI_API_KEY": gemini}))

def delete_keys():
    if CONFIG_FILE.exists():
        CONFIG_FILE.unlink()

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Instagram Analyzer",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
.metric-card {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    padding: 20px; border-radius: 12px; color: white;
    text-align: center; margin: 5px 0;
}
.metric-value { font-size: 2rem; font-weight: bold; }
.metric-label { font-size: 0.9rem; opacity: 0.9; margin-top: 4px; }
.reel-badge    { background:#ff6b6b; color:white; padding:2px 8px; border-radius:10px; font-size:.75rem; }
.image-badge   { background:#4ecdc4; color:white; padding:2px 8px; border-radius:10px; font-size:.75rem; }
.carrossel-badge { background:#45b7d1; color:white; padding:2px 8px; border-radius:10px; font-size:.75rem; }
</style>
""", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────
_saved = load_keys()

with st.sidebar:
    st.title("⚙️ Configurações")
    st.markdown("---")

    if _saved.get("APIFY_TOKEN") and _saved.get("GEMINI_API_KEY"):
        st.success("🔐 Chaves salvas")

    apify_token = st.text_input(
        "Apify API Token", type="password",
        value=_saved.get("APIFY_TOKEN", ""),
        placeholder="Cole sua chave aqui",
        help="apify.com → Settings → Integrations",
    )
    gemini_key = st.text_input(
        "Gemini API Key", type="password",
        value=_saved.get("GEMINI_API_KEY", ""),
        placeholder="Cole sua chave aqui",
        help="aistudio.google.com → Get API key (gratuito)",
    )

    col_save, col_del = st.columns(2)
    with col_save:
        if st.button("💾 Salvar", use_container_width=True):
            if apify_token and gemini_key:
                save_keys(apify_token, gemini_key)
                st.success("Salvo!")
                st.rerun()
            else:
                st.warning("Preencha as duas chaves.")
    with col_del:
        if st.button("🗑️ Remover", use_container_width=True):
            delete_keys()
            st.rerun()

    st.markdown("---")
    max_posts = st.slider("Posts a analisar", 10, 50, 30, 5)
    st.markdown("---")
    st.markdown("[Criar conta Apify](https://apify.com) · [Chave Gemini](https://aistudio.google.com)")

# ── Main ──────────────────────────────────────────────────────────────────────
st.title("📊 Instagram Analyzer")
st.markdown("Análise completa de perfil com IA — métricas, engajamento e criativos com roteiro.")

col_input, col_btn = st.columns([4, 1])
with col_input:
    username_input = st.text_input(
        "Perfil", placeholder="@username ou username",
        label_visibility="collapsed",
    )
with col_btn:
    analyze_btn = st.button("🔍 Analisar", use_container_width=True, type="primary")

# Botão para reanalisar sem buscar Apify de novo (útil quando Gemini deu erro)
if "profile" in st.session_state and not (st.session_state.get("analysis") and st.session_state.get("creatives")):
    retry_btn = st.button("🔄 Gerar análise IA (sem buscar Instagram novamente)", use_container_width=True)
else:
    retry_btn = False

# ── Executar análise ──────────────────────────────────────────────────────────
def _run_ai(profile, posts, gemini_key):
    with st.spinner("🧠 Analisando perfil com Gemini..."):
        try:
            st.session_state["analysis"] = analyze_profile(profile, posts, gemini_key)
        except Exception as e:
            st.warning(f"⚠️ Análise: {str(e).replace(gemini_key, '***')}")

    with st.spinner("✍️ Gerando criativos com roteiro..."):
        try:
            st.session_state["creatives"] = generate_creatives(profile, posts, gemini_key)
        except Exception as e:
            st.warning(f"⚠️ Criativos: {str(e).replace(gemini_key, '***')}")

    if st.session_state.get("analysis") or st.session_state.get("creatives"):
        st.success("✅ Concluído!")
    else:
        st.error("Não foi possível gerar. Aguarde 1 minuto e tente novamente (limite do Gemini grátis).")

if analyze_btn:
    if not apify_token or not gemini_key:
        st.error("Insira as API keys no painel lateral e clique em 💾 Salvar.")
        st.stop()
    if not username_input.strip():
        st.error("Digite um nome de usuário.")
        st.stop()

    with st.spinner("🔄 Coletando dados do Instagram via Apify..."):
        try:
            raw     = get_profile_and_posts(username_input, apify_token, max_posts)
            profile = raw["profile"]
            posts   = parse_posts(raw["posts"])
            st.session_state.update({
                "profile": profile, "posts": posts,
                "analysis": None, "creatives": None,
                "gemini_key": gemini_key,
                "username": profile.get("username", username_input.lstrip("@")),
            })
        except Exception as e:
            st.error(f"Erro ao coletar dados: {e}")
            st.stop()

    _run_ai(profile, posts, gemini_key)

if retry_btn:
    _run_ai(
        st.session_state["profile"],
        st.session_state["posts"],
        st.session_state.get("gemini_key", gemini_key),
    )

# ── Exibir resultados ─────────────────────────────────────────────────────────
if "profile" not in st.session_state:
    st.stop()

profile   = st.session_state["profile"]
posts     = st.session_state["posts"]
analysis  = st.session_state.get("analysis") or ""
creatives = st.session_state.get("creatives") or ""
username  = st.session_state.get("username", "")
_gkey     = st.session_state.get("gemini_key", gemini_key)

# Cabeçalho do perfil
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

# Métricas
st.markdown("### Métricas Principais")
m1, m2, m3, m4, m5 = st.columns(5)
for col, value, label in [
    (m1, profile.get("followersCount", 0), "Seguidores"),
    (m2, profile.get("followingCount", 0), "Seguindo"),
    (m3, profile.get("postsCount", len(posts)), "Posts"),
    (m4, f"{sum(p['likes'] for p in posts)/len(posts):.0f}" if posts else "0", "Média Curtidas"),
    (m5, f"{sum(p['comments'] for p in posts)/len(posts):.1f}" if posts else "0", "Média Comentários"),
]:
    with col:
        fmt = f"{value:,}" if isinstance(value, int) else str(value)
        st.markdown(
            f'<div class="metric-card"><div class="metric-value">{fmt}</div>'
            f'<div class="metric-label">{label}</div></div>',
            unsafe_allow_html=True,
        )

# ── Download completo — aparece logo após as métricas ────────────────────────
if analysis or creatives:
    st.markdown("### ⬇️ Download Completo")
    full_text = ""
    if analysis:
        full_text += f"{'='*60}\nANÁLISE DO PERFIL @{username}\n{'='*60}\n\n{analysis}\n\n"
    if creatives:
        full_text += f"{'='*60}\nCRIATIVOS + ROTEIROS @{username}\n{'='*60}\n\n{creatives}\n\n"

    stamp = datetime.now().strftime('%Y%m%d_%H%M')
    dc1, dc2 = st.columns(2)
    with dc1:
        st.download_button(
            "⬇️ Baixar tudo (.txt)",
            data=full_text,
            file_name=f"analise_completa_{username}_{stamp}.txt",
            mime="text/plain",
            use_container_width=True,
            type="primary",
        )
    with dc2:
        pdf_bytes = make_pdf(f"Análise Completa @{username}", full_text)
        st.download_button(
            "⬇️ Baixar tudo (.pdf)",
            data=bytes(pdf_bytes),
            file_name=f"analise_completa_{username}_{stamp}.pdf",
            mime="application/pdf",
            use_container_width=True,
            type="primary",
        )
    st.markdown("---")

# ── Abas ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📈 Análise do Perfil",
    "🎬 Criativos + Roteiros",
    "🏆 Top Posts",
    "📊 Gráficos",
    "💡 Ideias por Tema",
])

# ── Tab 1: Análise ────────────────────────────────────────────────────────────
with tab1:
    if analysis:
        stamp = datetime.now().strftime('%Y%m%d_%H%M')
        d1, d2 = st.columns(2)
        with d1:
            st.download_button(
                "⬇️ Baixar análise (.txt)",
                data=analysis,
                file_name=f"analise_{username}_{stamp}.txt",
                mime="text/plain",
                use_container_width=True,
            )
        with d2:
            pdf_bytes = make_pdf(f"Análise do Perfil @{username}", analysis)
            st.download_button(
                "⬇️ Baixar análise (.pdf)",
                data=bytes(pdf_bytes),
                file_name=f"analise_{username}_{stamp}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        st.markdown("---")
        st.markdown(analysis)
    else:
        st.info("Clique em Analisar para gerar a análise.")

# ── Tab 2: Criativos com roteiro ──────────────────────────────────────────────
with tab2:
    if creatives:
        stamp = datetime.now().strftime('%Y%m%d_%H%M')
        d1, d2 = st.columns(2)
        with d1:
            st.download_button(
                "⬇️ Baixar criativos (.txt)",
                data=creatives,
                file_name=f"criativos_{username}_{stamp}.txt",
                mime="text/plain",
                use_container_width=True,
            )
        with d2:
            pdf_bytes = make_pdf(f"Criativos + Roteiros @{username}", creatives)
            st.download_button(
                "⬇️ Baixar criativos (.pdf)",
                data=bytes(pdf_bytes),
                file_name=f"criativos_{username}_{stamp}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        st.markdown("---")
        st.markdown(creatives)
    else:
        st.info("Clique em Analisar para gerar os criativos.")

# ── Tab 3: Top Posts ──────────────────────────────────────────────────────────
with tab3:
    if not posts:
        st.info("Nenhum post encontrado.")
    else:
        for p in posts:
            p["engagement_score"] = p["likes"] + p["comments"] * 3 + (p["views"] or 0) * 0.1
        sorted_posts = sorted(posts, key=lambda x: x["engagement_score"], reverse=True)

        for i, p in enumerate(sorted_posts[:10], 1):
            pc1, pc2 = st.columns([3, 1])
            with pc1:
                badge = {"Reel": "reel", "Imagem": "image", "Carrossel": "carrossel"}.get(p["type"], "image")
                st.markdown(
                    f'<span class="{badge}-badge">{p["type"]}</span> **#{i}** · {(p["timestamp"] or "")[:10]}',
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

# ── Tab 4: Gráficos ───────────────────────────────────────────────────────────
with tab4:
    if not posts:
        st.info("Sem dados para gráficos.")
    else:
        df = pd.DataFrame(posts)
        gc1, gc2 = st.columns(2)

        with gc1:
            type_df = df.groupby("type").agg(curtidas=("likes","mean"), quantidade=("id","count")).reset_index()
            fig = px.bar(type_df, x="type", y="curtidas", color="type",
                         title="Média de Curtidas por Tipo", text="quantidade",
                         labels={"type":"Tipo","curtidas":"Média Curtidas"})
            fig.update_traces(texttemplate="%{text} posts", textposition="outside")
            st.plotly_chart(fig, use_container_width=True)

        with gc2:
            fig2 = px.scatter(df, x="likes", y="comments", color="type",
                              size="views" if df["views"].sum() > 0 else None,
                              hover_data=["caption"],
                              title="Curtidas vs Comentários",
                              labels={"likes":"Curtidas","comments":"Comentários","type":"Tipo"})
            st.plotly_chart(fig2, use_container_width=True)

        df_time = df.copy()
        df_time["timestamp"] = pd.to_datetime(df_time["timestamp"], errors="coerce")
        df_time = df_time.dropna(subset=["timestamp"]).sort_values("timestamp")
        if not df_time.empty:
            fig3 = px.line(df_time, x="timestamp", y="likes", color="type", markers=True,
                           title="Curtidas ao Longo do Tempo",
                           labels={"timestamp":"Data","likes":"Curtidas","type":"Tipo"})
            st.plotly_chart(fig3, use_container_width=True)

        all_tags: dict = {}
        for p in posts:
            for tag in p.get("hashtags", []):
                all_tags[tag] = all_tags.get(tag, 0) + 1
        if all_tags:
            top_tags = sorted(all_tags.items(), key=lambda x: x[1], reverse=True)[:15]
            tag_df = pd.DataFrame(top_tags, columns=["hashtag","frequência"])
            fig4 = px.bar(tag_df, x="frequência", y="hashtag", orientation="h",
                          title="Hashtags Mais Usadas", color="frequência",
                          color_continuous_scale="Purples")
            fig4.update_layout(yaxis={"categoryorder":"total ascending"})
            st.plotly_chart(fig4, use_container_width=True)

# ── Tab 5: Ideias por tema ────────────────────────────────────────────────────
with tab5:
    st.markdown("### Criativos por Tema Específico")
    st.markdown("Digite um tema e a IA gera roteiros completos baseados no estilo deste perfil.")

    topic = st.text_input("Tema", placeholder="Ex: saúde mental, emagrecimento, moda plus size...")

    if st.button("✨ Gerar Roteiros por Tema", type="primary"):
        if not topic.strip():
            st.warning("Digite um tema.")
        else:
            with st.spinner("Gerando roteiros com Gemini..."):
                try:
                    result = generate_ideas_by_topic(profile, posts, topic, _gkey)
                    st.session_state["topic_ideas"] = result
                    st.session_state["topic_name"] = topic
                except Exception as e:
                    st.error(f"Erro: {e}")

    if st.session_state.get("topic_ideas"):
        topic_name = st.session_state.get("topic_name", "tema")[:20]
        stamp = datetime.now().strftime('%Y%m%d')
        d1, d2 = st.columns(2)
        with d1:
            st.download_button(
                "⬇️ Baixar roteiros (.txt)",
                data=st.session_state["topic_ideas"],
                file_name=f"roteiros_{username}_{topic_name}_{stamp}.txt",
                mime="text/plain",
                use_container_width=True,
            )
        with d2:
            pdf_bytes = make_pdf(f"Roteiros: {topic_name} — @{username}", st.session_state["topic_ideas"])
            st.download_button(
                "⬇️ Baixar roteiros (.pdf)",
                data=bytes(pdf_bytes),
                file_name=f"roteiros_{username}_{topic_name}_{stamp}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        st.markdown("---")
        st.markdown(st.session_state["topic_ideas"])
