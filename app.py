import streamlit as st
import json, uuid, datetime, random
from pathlib import Path

"""
Tareas 📚 AlgoMind 🧠 
============================================
Tareas por hacer
------------
* ILQ ✅
* SLQ ✅
* TLQ ✅
* DIDM
* IA
"""

ROOT = Path(__file__).parent
DATA_FILE = ROOT / "data.json"
POSTS_FILE = ROOT / "posts.json"
DEFAULT_STATE_TAGS = ["Revisada", "No revisada", "Comentario pendiente"]

# Helpers ---------------------------

def load_json(p: Path, default):
    return json.loads(p.read_text("utf-8")) if p.exists() else default

def save_json(p: Path, obj):
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2), "utf-8")

# State -----------------------------

def init_state():
    st.session_state.setdefault("page", "Feed")
    st.session_state.setdefault("selected_tags", [])
    st.session_state.setdefault("detail_id", None)
    st.session_state.setdefault("current_quiz_post", None)
    st.session_state.setdefault("quiz_feedback", "")

# Data ------------------------------

def load_posts(): return load_json(POSTS_FILE, [])

def save_posts(ps): save_json(POSTS_FILE, ps)

def load_lib(): return load_json(DATA_FILE, {})

def save_lib(lb): save_json(DATA_FILE, lb)

# Tags ------------------------------

def all_tags(posts, lib):
    tags = set()
    for src in (posts,):
        for p in src:
            tags.update(p["tags"])
    for fd in lib.values():
        for t in fd.values():
            tags.update(t.get("tags", []))
    return sorted(tags)

# Sidebar ---------------------------

def sidebar(posts, lib):
    st.sidebar.title("Menú")
    options = ["Feed", "Biblioteca", "Estudio", "Detalle"]
    st.sidebar.radio("Vista", options, key="page", index=options.index(st.session_state.page))
    st.sidebar.markdown("### Filtro etiquetas")
    st.sidebar.multiselect("", all_tags(posts, lib), key="selected_tags")

# Feed ------------------------------

def form_new_post(posts):
    with st.expander("➕ Nueva publicación", expanded=False):
        with st.form("new_post", clear_on_submit=True):
            url = st.text_input("URL imagen (obligatorio)")
            title = st.text_input("Título")
            notes = st.text_area("Notas")
            tags = st.text_input("Etiquetas (separadas por coma)")
            if st.form_submit_button("Publicar") and url.strip():
                tag_list = [t.strip() for t in tags.split(",") if t.strip()]
                posts.append(dict(id=str(uuid.uuid4()), created_at=datetime.datetime.utcnow().isoformat(), image=url.strip(), gallery=[], title=title or "Sin título", notes=notes, tags=tag_list, comments=[], private=False))
                save_posts(posts); st.success("Publicada ✔️")

def open_detail(pid):
    st.session_state.update({"page": "Detalle", "detail_id": pid})

def render_feed(posts):
    st.markdown("## Tareas - Ejemplos")
    form_new_post(posts)
    sel = set(st.session_state.selected_tags)
    for p in sorted(posts, key=lambda x: x["created_at"], reverse=True):
        if sel and not (set(p["tags"]) & sel):
            continue
        st.image(p["image"], width=550)
        st.markdown(f"**{p['title']}** • {' '.join('['+t+']' for t in p['tags'])}")
        st.button("Ver detalles", key=p["id"], on_click=lambda pid=p["id"]: open_detail(pid))
        st.divider()

# Detail ----------------------------

def render_detail(posts):
    post = next((x for x in posts if x["id"] == st.session_state.detail_id), None)
    if not post:
        st.error("Post no encontrado"); return

    if st.button("← Volver al feed"):
        st.session_state.detail_id = None; st.experimental_rerun()

    st.header(post["title"])
    st.image(post["image"], width=650)
    st.markdown("*Etiquetas:* " + ", ".join(post["tags"]) if post["tags"] else "*Sin etiquetas*")
    st.write(post.get("notes", "—"))

    # ----- Comentarios -----
    st.markdown("#### Comentarios")
    if post["comments"]:
        for c in post["comments"]:
            st.markdown(f"- *{c['author']}* ({c['ts']}): {c['text']}")
    else:
        st.write("*Sin comentarios aún*")

    new_c = st.text_input("Nuevo comentario", key="new_comment")
    if st.button("Publicar comentario") and new_c.strip():
        post["comments"].append({
            "author": "you",
            "text": new_c.strip(),
            "ts": datetime.datetime.utcnow().isoformat(),
        })
        save_posts(posts)
        st.experimental_rerun()

# Biblioteca ------------------------ ------------------------

def render_library(lib, posts):
    st.markdown("## Mi biblioteca (solo lectura)")
    for fn, folder in lib.items():
        st.subheader(fn)
        for tn, t in folder.items():
            st.markdown(f"### {tn}")
            if t["images"]:
                url=t["images"][0]; st.image(url, width=300); st.markdown(f"[🔗 Abrir imagen]({url})", unsafe_allow_html=True)
            st.write(t.get("comments", "—"))
            st.button("Compartir", key=f"share_{fn}_{tn}", on_click=lambda f=fn,n=tn: share_to_feed(f,n,t,posts))

def share_to_feed(fn, tn, t, posts):
    posts.append(dict(id=str(uuid.uuid4()), created_at=datetime.datetime.utcnow().isoformat(), image=t["images"][0] if t["images"] else "", gallery=t["images"][1:], title=f"{fn}/{tn}", notes=t.get("comments", ""), tags=t.get("tags", []), comments=[], private=False))
    save_posts(posts); st.success("Compartido ✔️")

# Estudio (quiz) --------------------

def render_study(posts):
    st.markdown("## Modo Estudio – ¿Qué categoría es?")
    # Filtrar solo por etiquetas que no sean de estado
    quiz_posts = [p for p in posts if any(t not in DEFAULT_STATE_TAGS for t in p["tags"])]
    if not quiz_posts:
        st.info("No hay publicaciones con etiquetas de categoría."); return

    # Seleccionar post
    if st.session_state.current_quiz_post is None:
        st.session_state.current_quiz_post = random.choice(quiz_posts)["id"]
    post = next(x for x in posts if x["id"] == st.session_state.current_quiz_post)

    st.image(post["image"], width=600)
    # Posibles etiquetas (excluir de estado)
    tag_pool = sorted({t for p in quiz_posts for t in p["tags"] if t not in DEFAULT_STATE_TAGS})
    guess = st.selectbox("Selecciona la categoría", tag_pool)
    if st.button("Comprobar"):
        correct = guess in [t for t in post["tags"] if t not in DEFAULT_STATE_TAGS]
        st.session_state.quiz_feedback = "✅ Correcto" if correct else f"❌ Incorrecto. Era: {', '.join(post['tags'])}"
    st.write(st.session_state.quiz_feedback)
    if st.button("Siguiente"):
        st.session_state.current_quiz_post = random.choice(quiz_posts)["id"]
        st.session_state.quiz_feedback = ""
        st.experimental_rerun()

# Main ------------------------------

def main():
    init_state()
    posts = load_posts(); lib = load_lib()
    if st.session_state.page == "Detalle" and not st.session_state.detail_id:
        st.session_state.page = "Feed"
    sidebar(posts, lib)
    page = st.session_state.page
    if page == "Feed":
        render_feed(posts)
    elif page == "Biblioteca":
        render_library(lib, posts)
    elif page == "Estudio":
        render_study(posts)
    elif page == "Detalle":
        render_detail(posts)

if __name__ == "__main__":
    main()
