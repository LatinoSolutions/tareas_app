import streamlit as st
import json
from pathlib import Path
from typing import Dict, List
import base64

"""
Trading Tasks App – v1.6.3 (archivo completo)
============================================
* Gestión total de carpetas y subpáginas.
* Filtro global.
* Sin código truncado.
"""

DATA_FILE = Path("data.json")
DEFAULT_STATE_TAGS = ["Revisada", "No revisada", "Comentario pendiente"]

# -------------------- Helpers --------------------

def load_data() -> Dict:
    return json.loads(DATA_FILE.read_text("utf-8")) if DATA_FILE.exists() else {}

def save_data(data: Dict):
    DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), "utf-8")

# ------------------- Session --------------------

def init_state():
    defaults = {
        "current_folder": None,
        "current_task": None,
        "new_folder": "",
        "new_task": "",
        "new_img": "",
        "rename_task_input": "",
        "confirm_delete": False,
        "rename_folder_input": "",
        "confirm_delete_folder": False,
    }
    for k, v in defaults.items():
        st.session_state.setdefault(k, v)

# --------------- Navegación helpers -------------

def nav_folder(name: str):
    st.session_state.update({"current_folder": name, "current_task": None, "rename_folder_input": name})

def nav_task(name: str):
    st.session_state.current_task = name

def back_root():
    st.session_state.current_folder = None
    st.session_state.current_task = None

# ---------- Carpeta CRUD ----------

def add_folder():
    data = load_data(); name = st.session_state.new_folder.strip()
    if not name: st.sidebar.warning("Nombre vacío"); return
    if name in data: st.sidebar.warning("La carpeta ya existe"); return
    data[name] = {}; save_data(data); st.session_state.new_folder = ""; st.sidebar.success("Carpeta creada ✔️")

def rename_folder():
    data = load_data(); old = st.session_state.current_folder; new = st.session_state.rename_folder_input.strip()
    if not new: st.warning("Nombre vacío"); return
    if new in data and new != old: st.warning("Ya existe"); return
    data[new] = data.pop(old); save_data(data); st.session_state.current_folder = new; st.success("Carpeta renombrada ✔️")

def delete_folder():
    if not st.session_state.confirm_delete_folder: st.warning("Marca confirmación"); return
    data = load_data(); data.pop(st.session_state.current_folder, None); save_data(data)
    st.session_state.confirm_delete_folder = False; back_root(); st.success("Carpeta eliminada 🗑️")

# ---------- Tarea CRUD ----------

def add_task():
    data = load_data(); title = st.session_state.new_task.strip(); folder = data[st.session_state.current_folder]
    if not title: st.warning("Nombre vacío"); return
    if title in folder: st.warning("Ya existe"); return
    folder[title] = {"images": [], "comments": "", "tags": ["No revisada"], "stars": 0}; save_data(data)
    st.session_state.new_task = ""; nav_task(title)

def add_image():
    url = st.session_state.new_img.strip();
    if not url: st.warning("URL vacía"); return
    data = load_data(); task = data[st.session_state.current_folder][st.session_state.current_task]
    task["images"].append(url); save_data(data); st.session_state.new_img = ""

def rename_task():
    data = load_data(); new = st.session_state.rename_task_input.strip(); folder = data[st.session_state.current_folder]
    old = st.session_state.current_task
    if not new: st.warning("Nombre vacío"); return
    if new in folder and new != old: st.warning("Ya existe"); return
    folder[new] = folder.pop(old); save_data(data); nav_task(new); st.success("Subpágina renombrada ✔️")

def delete_task():
    if not st.session_state.confirm_delete: st.warning("Marca confirmación"); return
    data = load_data(); folder = data[st.session_state.current_folder]
    folder.pop(st.session_state.current_task, None); save_data(data)
    st.session_state.confirm_delete = False; st.session_state.current_task = None; st.success("Subpágina eliminada 🗑️")

# ---------------- Sidebar ----------------

def sidebar(data: Dict) -> List[str]:
    st.sidebar.title("☰ Navegación & Filtros")
    # Backup
    with st.sidebar.expander("📦 Backup"):
        if st.button("📥 Descargar backup"): b64 = base64.b64encode(json.dumps(data, ensure_ascii=False, indent=2).encode()).decode(); st.markdown(f'<a href="data:application/json;base64,{b64}" download="trading_tasks_backup.json">Descargar JSON</a>', unsafe_allow_html=True)
        up = st.file_uploader("Subir backup", type="json")
        if up: data.clear(); data.update(json.load(up)); save_data(data); st.experimental_rerun()
    st.sidebar.divider()
    st.sidebar.markdown("### Carpetas")
    for name in data: st.sidebar.button(name, key=f"side_{name}", on_click=lambda n=name: nav_folder(n))
    st.sidebar.text_input("Nueva carpeta", key="new_folder"); st.sidebar.button("➕ Crear", on_click=add_folder)
    st.sidebar.divider()
    # Filtro
    tags = {t for f in data.values() for tk in f.values() for t in tk.get("tags", [])}.union(DEFAULT_STATE_TAGS)
    return st.sidebar.multiselect("Filtrar por etiquetas", sorted(tags))

# ---------------- Main -------------------

def main():
    init_state(); data = load_data(); sel_tags = sidebar(data)
    st.title("📂 Tareas de Trading – Mentoría")
    # Root view
    if st.session_state.current_folder is None:
        if sel_tags:
            st.header("Resultados por etiqueta")
            matches = [(fn, tn, t) for fn, fl in data.items() for tn, t in fl.items() if set(t.get("tags", [])) & set(sel_tags)]
            if not matches: st.info("Sin resultados"); return
            for fn, tn, t in matches:
                label = f"{fn} / {tn} {'★'*t.get('stars',0)} {' '.join('['+x+']' for x in t.get('tags',[]))}"
                st.button(label, key=f"m_{fn}_{tn}", on_click=lambda f=fn, tt=tn: (nav_folder(f), nav_task(tt)))
            return
        st.header("Carpetas")
        for name in data: st.button(f"🗂️ {name}", key=f"home_{name}", on_click=lambda n=name: nav_folder(n))
        if not data: st.info("Añade una carpeta a la izquierda")
        return
    # Folder view
    fn = st.session_state.current_folder; folder = data[fn]
    col1, col2, col3 = st.columns([1,6,3])
    with col1: st.button("⬅️", on_click=back_root)
    with col2: st.text_input("Nombre carpeta", value=fn, key="rename_folder_input")
    with col3:
        st.checkbox("Confirmar", key="confirm_delete_folder")
        st.button("🗑️ Eliminar", on_click=delete_folder, type="secondary")
        st.button("Guardar", on_click=rename_folder)
    st.text_input("Nueva subpágina", key="new_task"); st.button("➕ Crear subpágina", on_click=add_task)
    st.markdown("---")
    for tn, tk in folder.items():
        if sel_tags and not (set(tk.get("tags", [])) & set(sel_tags)): continue
        c1, c2 = st.columns([1,5])
        if tk["images"]: c1.image(tk["images"][0], width=100)
        lbl = f"{tn} {'★'*tk.get('stars',0)} {' '.join('['+t+']' for t in tk.get('tags',[]))}"
        c2.button(lbl, key=f"open_{tn}", on_click=lambda n=tn: nav_task(n))
    # Task view
    if st.session_state.current_task:
        tn = st.session_state.current_task; tk = folder[tn]
        st.markdown("---"); st.subheader("Detalles de subpágina")
        st.text_input("Título", value=tn, key="rename_task_input"); st.button("Guardar título", on_click=rename_task)
        st.checkbox("Confirmar eliminación", key="confirm_delete"); st.button("🗑️ Eliminar subpágina", on_click=delete_task, type="secondary")
        st.text_input("URL imagen", key="new_img"); st.button("Añadir imagen", on_click=add_image)
        for i, url in enumerate(tk["images"],1): st.image(url, width=660, caption=f"Imagen {i}"); st.markdown(f"[🔗 Abrir]({url})", unsafe_allow_html=True)
        st.markdown("### Comentarios"); comment = st.text_area("", value=tk.get("comments", ""))
        if st.button("Guardar comentario"): tk["comments"] = comment; save_data(data)
        st.markdown("### Estado"); cur = next((t for t in tk["tags"] if t in DEFAULT_STATE_TAGS), "No revisada"); sel = st.radio("", DEFAULT_STATE_TAGS, index=DEFAULT_STATE_TAGS.index(cur))
        if sel != cur: tk["tags"] = [t for t in tk["tags"] if t not in DEFAULT_STATE_TAGS] + [sel]; save_data(data)
        st.markdown("### Etiquetas personalizadas"); newtg = st.text_input("Añadir (coma)")
        if st.button("Guardar etiquetas"): tk["tags"].extend([t.strip() for t in newtg.split(",") if t.strip() and t.strip() not in tk["tags"]]); save_data(data)
        st.markdown("### Valoración ⭐"); stars = st.slider("",0,5,tk.get("stars",0), key=f"s_{tn}");
        if stars != tk.get("stars",0): tk["stars"] = stars; save_data(data)

# ---------------- run ------------------
if __name__ == "__main__":
    main()
