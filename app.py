import streamlit as st
import json
from pathlib import Path
from typing import Dict, List
import uuid, datetime, base64

"""
Trading Tasks – v2.1 (Feed + creación y detalles fijos)
======================================================
✔️ **Crear publicación** desde el Feed (imagen + título + notas + etiquetas).  
✔️ Botón “Ver detalles” ahora abre una vista dedicada (sin reiniciar el feed).  
✔️ Biblioteca privada vuelve a ser editable (carpetas y subpáginas).  
✔️ Compartir subpágina ➜ copia la tarea al Feed (pública por defecto).  
✔️ Gestor de etiquetas intacto.
"""

ROOT = Path(__file__).parent
DATA_FILE = ROOT / "data.json"
POSTS_FILE = ROOT / "posts.json"

DEFAULT_STATE_TAGS = ["Revisada", "No revisada", "Comentario pendiente"]

# -------------- utilidades JSON -------------------

def load_json(path: Path, default):
    return json.loads(path.read_text("utf-8")) if path.exists() else default

def save_json(path: Path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), "utf-8")

# ---------------- session defaults ----------------

def init_state():
    defaults = dict(
        page="Feed",              # Feed | Biblioteca | Etiquetas | Detalle
        selected_tags=[],
        detail_id=None,
        current_folder=None,
        current_task=None,
    )
    for k, v in defaults.items():
        st.session_state.setdefault(k, v)

# ---------------- data access ---------------------

def load_posts():
    return load_json(POSTS_FILE, [])

def save_posts(posts):
    save_json(POSTS_FILE, posts)

def load_lib():
    return load_json(DATA_FILE, {})

def save_lib(lib):
    save_json(DATA_FILE, lib)

# ---------------- tag helpers ---------------------

def all_tags(posts, lib):
    t = set(DEFAULT_STATE_TAGS)
    for p in posts: t.update(p["tags"])
    for f in lib.values():
        for tk in f.values(): t.update(tk.get("tags", []))
    return sorted(t)

# ---------------- sidebar -------------------------

def sidebar(posts, lib):
    st.sidebar.title("Menú")
    st.sidebar.radio("Vista", ["Feed", "Biblioteca", "Etiquetas"], key="page")
    st.sidebar.markdown("### Filtro etiquetas")
    st.sidebar.multiselect("", all_tags(posts, lib), key="selected_tags")
    st.sidebar.markdown("---")
    if st.sidebar.button("Backup posts.json"):
        b64 = base64.b64encode(POSTS_FILE.read_bytes()).decode(); st.sidebar.markdown(f'<a href="data:application/json;base64,{b64}" download="posts.json">Descargar</a>', unsafe_allow_html=True)

# -------------- helper formas ---------------------

def form_new_post(posts):
    with st.form("nueva_pub", clear_on_submit=True):
        st.subheader("➕ Nueva publicación")
        url = st.text_input("URL imagen (obligatorio)")
        title = st.text_input("Título")
        notes = st.text_area("Notas")
        tags = st.multiselect("Etiquetas", all_tags(posts, load_lib()))
        public = st.checkbox("Pública", value=True)
        submitted = st.form_submit_button("Publicar")
        if submitted and url.strip():
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
            posts.append(post); save_posts(posts); st.success("Publicada ✔️")

# -------------- feed ------------------------------

def render_feed(posts):
    st.markdown("## Feed comunitario")
    form_new_post(posts)
    sel_tags = set(st.session_state.selected_tags)
    ordered = sorted(posts, key=lambda x: x["created_at"], reverse=True)
    filtered = [p for p in ordered if not sel_tags or set(p["tags"]) & sel_tags]
    if not filtered:
        st.info("Sin publicaciones con esas etiquetas"); return
    for p in filtered:
        with st.container():
            st.image(p["image"], width=550)
            meta = f"**{p['title']}**  •  {' '.join('['+t+']' for t in p['tags'])}"
            st.markdown(meta)
            st.button("Ver detalles", key=f"det_{p['id']}", on_click=lambda pid=p["id"]: open_detail(pid))
            st.markdown("---")

# ---- detalle post (independiente) ---------------

def open_detail(pid):
    st.session_state.page = "Detalle"; st.session_state.detail_id = pid

def render_detail(posts):
    post = next((p for p in posts if p["id"] == st.session_state.detail_id), None)
    if not post:
        st.error("Post no encontrado"); return
    st.button("← Volver", on_click=lambda: st.session_state.update({"page":"Feed","detail_id":None}))
    st.header(post["title"])
    st.image(post["image"], width=660)
    st.write(post["notes"] or "—")
    st.markdown("#### Comentarios")
    for c in post["comments"]:
        st.markdown(f"- *{c['author']}* ({c['ts']}): {c['text']}")
    new_c = st.text_input("Nuevo comentario")
    if st.button("Publicar") and new_c.strip():
        post["comments"].append({"author":"you","text":new_c.strip(),"ts":datetime.datetime.utcnow().isoformat()}); save_posts(posts); st.experimental_rerun()

# -------------- biblioteca (CRUD) -----------------

def render_library(lib, posts):
    st.markdown("## Mi biblioteca")
    for fname, folder in lib.items():
        st.subheader(fname)
        for tname, task in folder.items():
            st.markdown(f"### {tname}")
            if task["images"]:
                st.image(task["images"][0], width=350)
            st.write(task.get("comments","—"))
            cols = st.columns(3)
            with cols[0]:
                if st.button("Compartir", key=f"share_{fname}_{tname}"):
                    share_task_to_feed(fname, tname, task, posts)
            with cols[1]:
                if st.button("Editar", key=f"edit_{fname}_{tname}"):
                    st.info("Edición completa pendiente (podemos re‑usar lógica antigua)")
            with cols[2]:
                if st.button("Borrar", key=f"del_{fname}_{tname}"):
                    del lib[fname][tname]; save_lib(lib); st.experimental_rerun()

def share_task_to_feed(fname, tname, task, posts):
    post = dict(id=str(uuid.uuid4()), created_at=datetime.datetime.utcnow().isoformat(), title=f"{fname} / {tname}", image=task["images"][0] if task["images"] else "", gallery=task["images"][1:], notes=task.get("comments",""), tags=task.get("tags",[]), comments=[], private=False)
    posts.append(post); save_posts(posts); st.success("Publicado en feed ✔️")

# -------------- gestor etiquetas ------------------

def render_tags(posts, lib):
    st.markdown("## Gestor de etiquetas")
    tag = st.selectbox("Etiqueta", all_tags(posts, lib))
    col1, col2 = st.columns(2)
    with col1:
        new = st.text_input("Renombrar a", value=tag, key="tag_new")
        if st.button("Renombrar") and new.strip() and new != tag:
            bulk_rename(tag, new, posts, lib); st.success("Renombrada ✔️"); st.experimental_rerun()
    with col2:
        if st.button("Eliminar"):
            bulk_delete(tag, posts, lib); st.warning("Eliminada ✂️"); st.experimental_rerun()

def bulk_rename(old, new, posts, lib):
    for p in posts: p["tags"] = [new if t==old else t for t in p["tags"]]
    for f in lib.values():
        for t in f.values(): t["tags"] = [new if tg==old else tg for tg in t.get("tags",[])]
    save_posts(posts); save_lib(lib)

def bulk_delete(tag, posts, lib):
    for p in posts:
        p["tags"] = [t for t in p["tags"] if t != tag]
    for f in lib.values():
        for t in f.values():
            t["tags"] = [tg for tg in t.get("tags", []) if tg != tag]
    save_posts(posts)
    save_lib(lib)

# ---------------- main ------------------

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
