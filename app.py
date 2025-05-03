import streamlit as st
import json, uuid, datetime, base64
from pathlib import Path

"""
Trading Tasks – v2.1.5 (indentación limpia)
===========================================
* Elimina líneas duplicadas e indentación inválida en `render_detail`.
* Mantiene arreglo de retorno seguro y enlace en biblioteca.
"""

ROOT = Path(__file__).parent
DATA_FILE = ROOT / "data.json"
POSTS_FILE = ROOT / "posts.json"
DEFAULT_STATE_TAGS = ["Revisada", "No revisada", "Comentario pendiente"]

# ---------- helpers -----------------

def load_json(p, d):
    return json.loads(p.read_text("utf-8")) if p.exists() else d

def save_json(p, obj):
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2), "utf-8")

# ---------- session -----------------

def init_state():
    st.session_state.setdefault("page", "Feed")
    st.session_state.setdefault("selected_tags", [])
    st.session_state.setdefault("detail_id", None)

# ---------- data --------------------

def load_posts():
    return load_json(POSTS_FILE, [])

def save_posts(ps):
    save_json(POSTS_FILE, ps)

def load_lib():
    return load_json(DATA_FILE, {})

def save_lib(lb):
    save_json(DATA_FILE, lb)

# ---------- tags --------------------

def all_tags(posts, lib):
    tags = set(DEFAULT_STATE_TAGS)
    for p in posts:
        tags.update(p["tags"])
    for fd in lib.values():
        for t in fd.values():
            tags.update(t.get("tags", []))
    return sorted(tags)

# ---------- sidebar -----------------

def sidebar(posts, lib):
    st.sidebar.title("Menú")
    opts = ["Feed", "Biblioteca", "Etiquetas", "Detalle"]
    st.sidebar.radio("Vista", opts, index=opts.index(st.session_state.page), key="page")
    st.sidebar.markdown("### Filtro etiquetas")
    st.sidebar.multiselect("", all_tags(posts, lib), key="selected_tags")

# ---------- new post ----------------

def new_post_form(posts):
    with st.expander("➕ Nueva publicación", expanded=False):
        with st.form("new_post", clear_on_submit=True):
            url = st.text_input("URL imagen (obligatorio)")
            title = st.text_input("Título")
            notes = st.text_area("Notas")
            tags = st.multiselect("Etiquetas", all_tags(posts, load_lib()))
            if st.form_submit_button("Publicar") and url.strip():
                posts.append(dict(id=str(uuid.uuid4()), created_at=datetime.datetime.utcnow().isoformat(), image=url.strip(), gallery=[], title=title or "Sin título", notes=notes, tags=tags, comments=[], private=False))
                save_posts(posts); st.success("Publicada ✔️")

# ---------- feed --------------------

def open_detail(pid):
    st.session_state.update({"page": "Detalle", "detail_id": pid})

def render_feed(posts):
    st.markdown("## Feed comunitario")
    new_post_form(posts)
    sel = set(st.session_state.selected_tags)
    for p in sorted(posts, key=lambda x: x["created_at"], reverse=True):
        if sel and not (set(p["tags"]) & sel):
            continue
        st.image(p["image"], width=550)
        st.markdown(f"**{p['title']}** • {' '.join('['+t+']' for t in p['tags'])}")
        st.button("Ver detalles", key=p["id"], on_click=lambda pid=p["id"]: open_detail(pid))
        st.divider()

# ---------- detail ------------------

def render_detail(posts):
    post = next((x for x in posts if x["id"] == st.session_state.detail_id), None)
    if not post:
        st.error("Post no encontrado"); return
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
    new_c = st.text_input("Nuevo comentario")
    if st.button("Publicar comentario") and new_c.strip():
        post["comments"].append({"author":"you","text":new_c.strip(),"ts":datetime.datetime.utcnow().isoformat()})
        save_posts(posts); st.experimental_rerun()

# ---------- library -----------------

def render_library(lib, posts):
    st.markdown("## Mi biblioteca (solo lectura)")
    for fn, folder in lib.items():
        st.subheader(fn)
        for tn, t in folder.items():
            st.markdown(f"### {tn}")
            if t["images"]:
                url = t["images"][0]
                st.image(url, width=300)
                st.markdown(f"[🔗 Abrir imagen]({url})", unsafe_allow_html=True)
            st.write(t.get("comments", "—"))
            if st.button("Compartir", key=f"share_{fn}_{tn}"):
                share_to_feed(fn, tn, t, posts)

def share_to_feed(fn, tn, t, posts):
    posts.append(dict(id=str(uuid.uuid4()), created_at=datetime.datetime.utcnow().isoformat(), image=t["images"][0] if t["images"] else "", gallery=t["images"][1:], title=f"{fn}/{tn}", notes=t.get("comments", ""), tags=t.get("tags", []), comments=[], private=False))
    save_posts(posts); st.success("Compartido ✔️")

# ---------- tag manager ------------

def render_tags(posts, lib):
    st.markdown("## Gestor de etiquetas")
    tag = st.selectbox("Etiqueta", all_tags(posts, lib))
    new = st.text_input("Renombrar", value=tag)
    c1, c2 = st.columns(2)
    if c1.button("Renombrar") and new.strip() and new != tag:
        for p in posts: p["tags"] = [new if t == tag else t for t in p["tags"]]
        for f in lib.values():
            for t in f.values(): t["tags"] = [new if tg == tag else tg for tg in t.get("tags", [])]
        save_posts(posts); save_lib(lib); st.experimental_rerun()
    if c2.button("Eliminar"):
        for p in posts: p["tags"] = [t for t in p["tags"] if t != tag]
        for f in lib.values():
            for t in f.values(): t["tags"] = [tg for tg in t.get("tags", []) if tg != tag]
        save_posts(posts); save_lib(lib); st.experimental_rerun()

# ---------- main -------------------

def main():
    init_state()
    posts = load_posts()
    lib = load_lib()
    # Si está en detalle sin id válido, vuelve al feed
    if st.session_state.page == "Detalle" and not st.session_state.detail_id:
        st.session_state.page = "Feed"
    sidebar(posts, lib)
    pg = st.session_state.page
    if pg == "Feed":
        render_feed(posts)
    elif pg == "Biblioteca":
        render_library(lib, posts)
    elif pg == "Etiquetas":
        render_tags(posts, lib)
    elif pg == "Detalle":
        render_detail(posts)

if __name__ == "__main__":
    main()
import streamlit as st
import json, uuid, datetime, base64
from pathlib import Path

"""
Trading Tasks – v2.1.5 (indentación limpia)
===========================================
* Elimina líneas duplicadas e indentación inválida en `render_detail`.
* Mantiene arreglo de retorno seguro y enlace en biblioteca.
"""

ROOT = Path(__file__).parent
DATA_FILE = ROOT / "data.json"
POSTS_FILE = ROOT / "posts.json"
DEFAULT_STATE_TAGS = ["Revisada", "No revisada", "Comentario pendiente"]

# ---------- helpers -----------------

def load_json(p, d):
    return json.loads(p.read_text("utf-8")) if p.exists() else d

def save_json(p, obj):
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2), "utf-8")

# ---------- session -----------------

def init_state():
    st.session_state.setdefault("page", "Feed")
    st.session_state.setdefault("selected_tags", [])
    st.session_state.setdefault("detail_id", None)

# ---------- data --------------------

def load_posts():
    return load_json(POSTS_FILE, [])

def save_posts(ps):
    save_json(POSTS_FILE, ps)

def load_lib():
    return load_json(DATA_FILE, {})

def save_lib(lb):
    save_json(DATA_FILE, lb)

# ---------- tags --------------------

def all_tags(posts, lib):
    tags = set(DEFAULT_STATE_TAGS)
    for p in posts:
        tags.update(p["tags"])
    for fd in lib.values():
        for t in fd.values():
            tags.update(t.get("tags", []))
    return sorted(tags)

# ---------- sidebar -----------------

def sidebar(posts, lib):
    st.sidebar.title("Menú")
    opts = ["Feed", "Biblioteca", "Etiquetas", "Detalle"]
    st.sidebar.radio("Vista", opts, index=opts.index(st.session_state.page), key="page")
    st.sidebar.markdown("### Filtro etiquetas")
    st.sidebar.multiselect("", all_tags(posts, lib), key="selected_tags")

# ---------- new post ----------------

def new_post_form(posts):
    with st.expander("➕ Nueva publicación", expanded=False):
        with st.form("new_post", clear_on_submit=True):
            url = st.text_input("URL imagen (obligatorio)")
            title = st.text_input("Título")
            notes = st.text_area("Notas")
            tags = st.multiselect("Etiquetas", all_tags(posts, load_lib()))
            if st.form_submit_button("Publicar") and url.strip():
                posts.append(dict(id=str(uuid.uuid4()), created_at=datetime.datetime.utcnow().isoformat(), image=url.strip(), gallery=[], title=title or "Sin título", notes=notes, tags=tags, comments=[], private=False))
                save_posts(posts); st.success("Publicada ✔️")

# ---------- feed --------------------

def open_detail(pid):
    st.session_state.update({"page": "Detalle", "detail_id": pid})

def render_feed(posts):
    st.markdown("## Feed comunitario")
    new_post_form(posts)
    sel = set(st.session_state.selected_tags)
    for p in sorted(posts, key=lambda x: x["created_at"], reverse=True):
        if sel and not (set(p["tags"]) & sel):
            continue
        st.image(p["image"], width=550)
        st.markdown(f"**{p['title']}** • {' '.join('['+t+']' for t in p['tags'])}")
        st.button("Ver detalles", key=p["id"], on_click=lambda pid=p["id"]: open_detail(pid))
        st.divider()

# ---------- detail ------------------

def render_detail(posts):
    post = next((x for x in posts if x["id"] == st.session_state.detail_id), None)
    if not post:
        st.error("Post no encontrado"); return
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
    new_c = st.text_input("Nuevo comentario")
    if st.button("Publicar comentario") and new_c.strip():
        post["comments"].append({"author":"you","text":new_c.strip(),"ts":datetime.datetime.utcnow().isoformat()})
        save_posts(posts); st.experimental_rerun()

# ---------- library -----------------

def render_library(lib, posts):
    st.markdown("## Mi biblioteca (solo lectura)")
    for fn, folder in lib.items():
        st.subheader(fn)
        for tn, t in folder.items():
            st.markdown(f"### {tn}")
            if t["images"]:
                url = t["images"][0]
                st.image(url, width=300)
                st.markdown(f"[🔗 Abrir imagen]({url})", unsafe_allow_html=True)
            st.write(t.get("comments", "—"))
            if st.button("Compartir", key=f"share_{fn}_{tn}"):
                share_to_feed(fn, tn, t, posts)

def share_to_feed(fn, tn, t, posts):
    posts.append(dict(id=str(uuid.uuid4()), created_at=datetime.datetime.utcnow().isoformat(), image=t["images"][0] if t["images"] else "", gallery=t["images"][1:], title=f"{fn}/{tn}", notes=t.get("comments", ""), tags=t.get("tags", []), comments=[], private=False))
    save_posts(posts); st.success("Compartido ✔️")

# ---------- tag manager ------------

def render_tags(posts, lib):
    st.markdown("## Gestor de etiquetas")
    tag = st.selectbox("Etiqueta", all_tags(posts, lib))
    new = st.text_input("Renombrar", value=tag)
    c1, c2 = st.columns(2)
    if c1.button("Renombrar") and new.strip() and new != tag:
        for p in posts: p["tags"] = [new if t == tag else t for t in p["tags"]]
        for f in lib.values():
            for t in f.values(): t["tags"] = [new if tg == tag else tg for tg in t.get("tags", [])]
        save_posts(posts); save_lib(lib); st.experimental_rerun()
    if c2.button("Eliminar"):
        for p in posts: p["tags"] = [t for t in p["tags"] if t != tag]
        for f in lib.values():
            for t in f.values(): t["tags"] = [tg for tg in t.get("tags", []) if tg != tag]
        save_posts(posts); save_lib(lib); st.experimental_rerun()

# ---------- main -------------------

def main():
    init_state()
    posts = load_posts()
    lib = load_lib()
    # Si está en detalle sin id válido, vuelve al feed
    if st.session_state.page == "Detalle" and not st.session_state.detail_id:
        st.session_state.page = "Feed"
    sidebar(posts, lib)
    pg = st.session_state.page
    if pg == "Feed":
        render_feed(posts)
    elif pg == "Biblioteca":
        render_library(lib, posts)
    elif pg == "Etiquetas":
        render_tags(posts, lib)
    elif pg == "Detalle":
        render_detail(posts)

if __name__ == "__main__":
    main()
