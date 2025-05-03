import streamlit as st
import json, uuid, datetime, random
from pathlib import Path

"""
Biblioteca - AlgoMind 
============================================
Tareas por hacer
------------
* ILQ ✅
* SLQ ✅
* TLQ ✅
* DIDM ✅
* IA
"""
ROOT = Path(__file__).parent
DATA_FILE = ROOT / "data.json"
POSTS_FILE = ROOT / "posts.json"
DEFAULT_STATE_TAGS = ["Revisada", "No revisada", "Comentario pendiente"]

# --- Ajusta aquí el ancho de imágenes ---
IMG_FEED_W = 550       # ancho en el feed
IMG_DETAIL_W = 800     # ancho en vista detalle
IMG_STUDY_W = 600      # ancho en modo estudio

# -------------- helpers -----------------

def load_json(p: Path, default):
    return json.loads(p.read_text("utf-8")) if p.exists() else default

def save_json(p: Path, obj):
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2), "utf-8")

# -------------- sesión -------------------

def init_state():
    st.session_state.setdefault("page", "Feed")
    st.session_state.setdefault("selected_tags", [])
    st.session_state.setdefault("detail_id", None)
    st.session_state.setdefault("current_quiz_post", None)
    st.session_state.setdefault("quiz_feedback", "")

# -------------- data ---------------------

def load_posts(): return load_json(POSTS_FILE, [])

def save_posts(ps): save_json(POSTS_FILE, ps)

# -------------- tags ---------------------

def all_tags(posts):
    tag_set = set()
    for p in posts: tag_set.update(p["tags"])
    return sorted(tag_set)

# -------------- sidebar ------------------

def sidebar(posts):
    st.sidebar.title("Menú")
    opts = ["Feed", "Biblioteca", "Estudio", "Detalle"]
    st.sidebar.radio("Vista", opts, index=opts.index(st.session_state.page), key="page")
    st.sidebar.markdown("### Filtro etiquetas")
    st.sidebar.multiselect("", all_tags(posts), key="selected_tags")

# -------------- Feed ---------------------

def form_new_post(posts):
    with st.expander("➕ Nueva publicación", expanded=False):
        with st.form("new_post", clear_on_submit=True):
            url = st.text_input("URL imagen (obligatorio)")
            title = st.text_input("Título")
            notes = st.text_area("Notas")
            tag_txt = st.text_input("Etiquetas (coma)")
            if st.form_submit_button("Publicar") and url.strip():
                tags = [t.strip() for t in tag_txt.split(",") if t.strip()]
                posts.append(dict(id=str(uuid.uuid4()), created_at=datetime.datetime.utcnow().isoformat(), image=url.strip(), gallery=[], title=title or "Sin título", notes=notes, tags=tags, comments=[]))
                save_posts(posts); st.success("Publicada ✔️")


def open_detail(pid):
    st.session_state.update({"page": "Detalle", "detail_id": pid})


def render_feed(posts):
    st.markdown("## Tareas, Ejemplos, Casos de Estudio")
    form_new_post(posts)
    sel = set(st.session_state.selected_tags)
    for p in sorted(posts, key=lambda x: x["created_at"], reverse=True):
        if sel and not (set(p["tags"]) & sel):
            continue
        st.image(p["image"], width=IMG_FEED_W)
        st.markdown(f"**{p['title']}** • {' '.join('['+t+']' for t in p['tags'])}")
        st.button("Ver detalles", key=p["id"], on_click=lambda pid=p["id"]: open_detail(pid))
        st.divider()

# -------------- Detalle ------------------

def render_detail(posts):
    post = next((x for x in posts if x["id"] == st.session_state.detail_id), None)
    if not post:
        st.error("Post no encontrado"); return

    if st.button("← Volver al feed"):
        st.session_state.detail_id = None; st.experimental_rerun()

    st.header(post["title"])
    st.image(post["image"], width=IMG_DETAIL_W)

    if post["tags"]:
        st.markdown("*Etiquetas:* " + ", ".join(post["tags"]))
    st.write(post.get("notes", "—"))

    # --- Formulario de edición ---
    with st.expander("✏️ Editar", expanded=False):
        with st.form("edit_post"):
            e_title = st.text_input("Título", value=post["title"])
            e_notes = st.text_area("Notas", value=post.get("notes", ""))
            e_tags_txt = st.text_input("Etiquetas (coma)", value=", ".join([t for t in post["tags"] if t not in DEFAULT_STATE_TAGS]))
            current_state = next((t for t in post["tags"] if t in DEFAULT_STATE_TAGS), "No revisada")
            e_state = st.radio("Estado", DEFAULT_STATE_TAGS, index=DEFAULT_STATE_TAGS.index(current_state))
            if st.form_submit_button("Guardar"):
                post["title"] = e_title or post["title"]
                post["notes"] = e_notes
                new_tags = [t.strip() for t in e_tags_txt.split(",") if t.strip()]
                post["tags"] = new_tags + [e_state]
                save_posts(posts); st.success("Actualizado ✔️"); st.experimental_rerun()

    # --- Comentarios ---
    st.markdown("#### Comentarios")
    if post["comments"]:
        for c in post["comments"]:
            st.markdown(f"- *{c['author']}* ({c['ts']}): {c['text']}")
    else:
        st.write("*Sin comentarios aún*")
    new_c = st.text_input("Nuevo comentario")
    if st.button("Publicar comentario") and new_c.strip():
        post["comments"].append({"author":"you","text":new_c.strip(),"ts":datetime.datetime.utcnow().isoformat()})
        save_posts(posts); st.experimental_rerun()

# -------------- Biblioteca ----------

def render_library(posts):
    st.markdown("## Biblioteca (solo lectura)")
    # agrupamos por primera parte del título (carpeta)
    by_folder = {}
    for p in posts:
        if "/" in p["title"]:
            folder, rest = p["title"].split("/", 1)
            by_folder.setdefault(folder.strip(), []).append((rest.strip(), p))
    for folder, lst in by_folder.items():
        st.subheader(folder)
        for name, p in lst:
            st.markdown(f"### {name}")
            st.image(p["image"], width=300)
            st.markdown(f"[🔗 Abrir imagen]({p['image']})", unsafe_allow_html=True)

# -------------- Estudio -------------

def render_study(posts):
    st.markdown("## Estudio – ¿Qué categoría ves?")
    quiz_posts = [p for p in posts if any(t not in DEFAULT_STATE_TAGS for t in p["tags"])]
    if not quiz_posts:
        st.info("No hay posts con categorías."); return
    if st.session_state.current_quiz_post is None:
        st.session_state.current_quiz_post = random.choice(quiz_posts)["id"]
    post = next(x for x in posts if x["id"] == st.session_state.current_quiz_post)
    st.image(post["image"], width=IMG_STUDY_W)
    pool = sorted({t for q in quiz_posts for t in q["tags"] if t not in DEFAULT_STATE_TAGS})
    guess = st.selectbox("Selecciona la categoría", pool)
    if st.button("Comprobar"):
        correct = guess in [t for t in post["tags"] if t not in DEFAULT_STATE_TAGS]
        st.session_state.quiz_feedback = "✅ Correcto" if correct else "❌ Incorrecto. Era: " + ", ".join(post["tags"])
    st.write(st.session_state.quiz_feedback)
    if st.button("Siguiente"):
        st.session_state.current_quiz_post = random.choice(quiz_posts)["id"]
        st.session_state.quiz_feedback = ""
        st.experimental_rerun()

# -------------- Main ----------------

def main():
    init_state()
    posts = load_posts()
    if st.session_state.page == "Detalle" and not st.session_state.detail_id:
        st.session_state.page = "Feed"
    sidebar(posts)
    pg = st.session_state.page
    if pg == "Feed":
        render_feed(posts)
    elif pg == "Biblioteca":
        render_library(posts)
    elif pg == "Estudio":
        render_study(posts)
    elif pg == "Detalle":
        render_detail(posts)

if __name__ == "__main__":
    main()
