import streamlit as st
import json
from pathlib import Path
from typing import Dict, List
import uuid, datetime, base64

"""
Trading Tasks – v2.1.3 (bug fix + link en biblioteca)
====================================================
* **Arregla** excepción al volver al feed y elimina advertencia del widget `page` sincronizando el `radio` con `session_state.page` mediante `index` calculado.  
* **Biblioteca**: ahora muestra un enlace "🔗 Abrir imagen" debajo de la miniatura principal.
"""

ROOT = Path(__file__).parent
DATA_FILE = ROOT / "data.json"
POSTS_FILE = ROOT / "posts.json"
DEFAULT_STATE_TAGS = ["Revisada", "No revisada", "Comentario pendiente"]

# ---------- JSON helpers ----------

def load_json(path: Path, default):
    return json.loads(path.read_text("utf-8")) if path.exists() else default

def save_json(path: Path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), "utf-8")

# ---------- Session defaults ------

def init_state():
    defaults = dict(page="Feed", selected_tags=[], detail_id=None)
    for k, v in defaults.items():
        st.session_state.setdefault(k, v)

# ---------- Data access -----------

def load_posts():
    return load_json(POSTS_FILE, [])

def save_posts(p):
    save_json(POSTS_FILE, p)

def load_lib():
    return load_json(DATA_FILE, {})

def save_lib(l):
    save_json(DATA_FILE, l)

# ---------- Tags ------------------

def all_tags(posts, lib):
    tags = set(DEFAULT_STATE_TAGS)
    for p in posts:
        tags.update(p["tags"])
    for f in lib.values():
        for t in f.values():
            tags.update(t.get("tags", []))
    return sorted(tags)

# ---------- Sidebar ---------------

def sidebar(posts, lib):
    st.sidebar.title("Menú")
    options = ["Feed", "Biblioteca", "Etiquetas", "Detalle"]
    st.sidebar.radio("Vista", options, key="page", index=options.index(st.session_state.page) if st.session_state.page in options else 0)
    st.sidebar.markdown("### Filtro etiquetas")
    st.sidebar.multiselect("", all_tags(posts, lib), key="selected_tags")

# ---------- New post form ---------

def form_new_post(posts):
    with st.expander("➕ Nueva publicación", expanded=False):
        with st.form("_new_post", clear_on_submit=True):
            url = st.text_input("URL imagen (obligatorio)")
            title = st.text_input("Título")
            notes = st.text_area("Notas")
            tags = st.multiselect("Etiquetas", all_tags(posts, load_lib()))
            public = st.checkbox("Pública", value=True)
            if st.form_submit_button("Publicar") and url.strip():
                post = dict(
                    id=str(uuid.uuid4()),
                    created_at=datetime.datetime.utcnow().isoformat(),
                    image=url.strip(),
                    gallery=[],
                    title=title or "Sin título",
                    notes=notes,
                    tags=tags,
                    comments=[],
                    private=not public,
                )
                posts.append(post)
                save_posts(posts)
                st.success("Publicada ✔️")

# ---------- Feed ------------------

def open_detail(pid):
    st.session_state.update({"page": "Detalle", "detail_id": pid})


def render_feed(posts):
    st.markdown("## Feed comunitario")
    form_new_post(posts)
    sel = set(st.session_state.selected_tags)
    for p in sorted(posts, key=lambda x: x["created_at"], reverse=True):
        if sel and not (set(p["tags"]) & sel):
            continue
        st.image(p["image"], width=550)
        st.markdown(f"**{p['title']}** • {' '.join('['+t+']' for t in p['tags'])}")
        st.button("Ver detalles", key=p["id"], on_click=lambda pid=p["id"]: open_detail(pid))
        st.divider()

# ---------- Detail ----------------

def render_detail(posts):
    post = next((x for x in posts if x["id"] == st.session_state.detail_id), None)
    if not post:
        st.error("Post no encontrado")
        return
    if st.button("← Volver al feed"):
        st.session_state.detail_id = None
        st.session_state.page = "Feed"
        st.experimental_rerun()
    st.header(post["title"])
    st.image(post["image"], width=660)
    st.write(post["notes"] or "—")

    st.markdown("#### Comentarios")
    for c in post["comments"]:
        st.markdown(f"- *{c['author']}* ({c['ts']}): {c['text']}")
    new_c = st.text_input("Nuevo comentario", key="comment_input")
    if st.button("Publicar comentario") and new_c.strip():
        post["comments"].append({
            "author": "you",
            "text": new_c.strip(),
            "ts": datetime.datetime.utcnow().isoformat(),
        })
        save_posts(posts)
        st.experimental_rerun()

# ---------- Biblioteca (read‑only) ---------------

def render_library(lib, posts):
    st.markdown("## Mi biblioteca (solo lectura)")
    for fn, folder in lib.items():
        st.subheader(fn)
        for tn, t in folder.items():
            st.markdown(f"### {tn}")
            if t["images"]:
                st.image(t["images"][0], width=300)
                st.markdown(f"[🔗 Abrir imagen]({t['images'][0]})", unsafe_allow_html=True)
            st.write(t.get("comments", "—"))
            if st.button("Compartir", key=f"share_{fn}_{tn}"):
                share_to_feed(fn, tn, t, posts)


def share_to_feed(fn, tn, t, posts):
    post = dict(
        id=str(uuid.uuid4()),
        created_at=datetime.datetime.utcnow().isoformat(),
        image=t["images"][0] if t["images"] else "",
        gallery=t["images"][1:],
        title=f"{fn}/{tn}",
        notes=t.get("comments", ""),
        tags=t.get("tags", []),
        comments=[],
        private=False,
    )
    posts.append(post)
    save_posts(posts)
    st.success("Compartido ✔️")

# ---------- Tag manager -----------

def render_tags(posts, lib):
    st.markdown("## Gestor de etiquetas")
    tag = st.selectbox("Etiqueta", all_tags(posts, lib))
    new = st.text_input("Renombrar", value=tag, key="tag_new")
    col1, col2 = st.columns(2)
    if col1.button("Renombrar") and new.strip() and new != tag:
        for p in posts:
            p["tags"] = [new if t == tag else t for t in p["tags"]]
        for f in lib.values():
            for t in f.values():
                t["tags"] = [new if tg == tag else tg for tg in t.get("tags", [])]
        save_posts(posts)
        save_lib(lib)
        st.experimental_rerun()
    if col2.button("Eliminar"):
        for p in posts:
            p["tags"] = [t for t in p["tags"] if t != tag]
        for f in lib.values():
            for t in f.values():
                t["tags"] = [tg for tg in t.get("tags", []) if tg != tag]
        save_posts(posts)
        save_lib(lib)
        st.experimental_rerun()

# ---------- Main ------------------

def main():
    init_state()
    posts = load_posts()
    lib = load_lib()
    sidebar(posts, lib)

    page = st.session_state.page
    if page == "Feed":
        render_feed(posts)
    elif page == "Biblioteca":
        render_library(lib, posts)
    elif page == "Etiquetas":
        render_tags(posts, lib)
    elif page == "Detalle":
        render_detail(posts)

if __name__ == "__main__":
    main()
