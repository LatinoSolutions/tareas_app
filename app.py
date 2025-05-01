import streamlit as st
import json
from pathlib import Path
from typing import Dict, List
import base64


"""
AlgoMind-Tareas 🧠
============================================
Lista de tareas
------------
* ILQ
* SLQ
* TLQ
* DIDM
* IA
"""

DATA_FILE = Path("data.json")
DEFAULT_STATE_TAGS = ["Revisada", "No revisada", "Comentario pendiente"]

# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------

def load_data() -> Dict:
    if DATA_FILE.exists():
        return json.loads(DATA_FILE.read_text("utf-8"))
    return {}


def save_data(data: Dict) -> None:
    DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), "utf-8")

# ---------------------------------------------------------------------------
# Session defaults
# ---------------------------------------------------------------------------

def init_state():
    defaults = {
        "current_folder": None,
        "current_task": None,
        "new_folder": "",
        "new_task": "",
        "new_img": "",
        "rename_task_input": "",
        "confirm_delete": False,
    }
    for k, v in defaults.items():
        st.session_state.setdefault(k, v)

# ---------------------------------------------------------------------------
# Generic rerun helper
# ---------------------------------------------------------------------------

def rerun():
    if hasattr(st, "rerun"):
        st.rerun()
    else:
        st.experimental_rerun()

# ---------------------------------------------------------------------------
# Navigation helpers
# ---------------------------------------------------------------------------

def open_task(name: str):
    st.session_state.current_task = name
    rerun()


def back_to_root():
    st.session_state.current_folder = None
    st.session_state.current_task = None
    rerun()


def navigate_folder(name: str):
    st.session_state.update({"current_folder": name, "current_task": None})
    rerun()

# ---------------------------------------------------------------------------
# Folder & task actions
# ---------------------------------------------------------------------------

def add_folder():
    data = load_data()
    name = st.session_state.new_folder.strip()
    if not name:
        st.sidebar.warning("Nombre vacío")
        return
    if name in data:
        st.sidebar.warning("La carpeta ya existe")
        return
    data[name] = {}
    save_data(data)
    st.session_state.new_folder = ""
    st.sidebar.success("Carpeta creada ✔️")
    rerun()


def add_task():
    data = load_data()
    title = st.session_state.new_task.strip()
    if not title:
        st.warning("Nombre vacío")
        return
    folder = data[st.session_state.current_folder]
    if title in folder:
        st.warning("La subpágina ya existe")
        return
    folder[title] = {"images": [], "comments": "", "tags": ["No revisada"], "stars": 0}
    save_data(data)
    st.session_state.new_task = ""
    st.session_state.current_task = title
    rerun()


def add_image():
    data = load_data()
    url = st.session_state.new_img.strip()
    if not url:
        st.warning("URL vacía")
        return
    task = data[st.session_state.current_folder][st.session_state.current_task]
    task["images"].append(url)
    save_data(data)
    st.session_state.new_img = ""
    rerun()


def rename_task():
    data = load_data()
    new = st.session_state.rename_task_input.strip()
    if not new:
        st.warning("Nombre vacío")
        return
    folder = data[st.session_state.current_folder]
    old = st.session_state.current_task
    if new == old:
        return
    if new in folder:
        st.warning("Ya existe una subpágina con ese nombre")
        return
    folder[new] = folder.pop(old)
    save_data(data)
    st.session_state.current_task = new
    st.session_state.rename_task_input = new
    rerun()


def delete_task():
    if not st.session_state.confirm_delete:
        st.warning("Marca la casilla de confirmación primero")
        return
    data = load_data()
    folder = data[st.session_state.current_folder]
    folder.pop(st.session_state.current_task, None)
    save_data(data)
    st.session_state.current_task = None
    st.session_state.confirm_delete = False
    st.success("Subpágina eliminada 🗑️")
    rerun()

# ---------------------------------------------------------------------------
# Sidebar: backup, folders, filters
# ---------------------------------------------------------------------------

def sidebar(data: Dict) -> List[str]:
    st.sidebar.title("☰ Navegación & Filtros")

    # Backup
    with st.sidebar.expander("📦 Backup", expanded=False):
        if st.button("📥 Descargar backup"):
            b64 = base64.b64encode(json.dumps(data, ensure_ascii=False, indent=2).encode()).decode()
            st.markdown(
                f'<a href="data:application/json;base64,{b64}" download="trading_tasks_backup.json">Descargar JSON</a>',
                unsafe_allow_html=True,
            )
        uploaded = st.file_uploader("Subir backup (.json)", type="json")
        if uploaded:
            data.clear(); data.update(json.load(uploaded)); save_data(data); st.success("Backup restaurado"); rerun()

    st.sidebar.divider()

    # Folder tree
    st.sidebar.markdown("### Carpetas")
    if data:
        for name in data:
            st.sidebar.button(name, key=f"side_{name}", on_click=lambda n=name: navigate_folder(n))
    else:
        st.sidebar.write("*Sin carpetas aún*")

    st.sidebar.text_input("Nueva carpeta", key="new_folder", placeholder="Ej: Semana 1")
    st.sidebar.button("➕ Crear carpeta", on_click=add_folder, type="primary")

    st.sidebar.divider()

    # Tag filters
    all_tags = set(DEFAULT_STATE_TAGS)
    for folder in data.values():
        for task in folder.values():
            all_tags.update(task.get("tags", []))
    return st.sidebar.multiselect("Filtrar por etiquetas", sorted(all_tags))

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    init_state()
    data = load_data()

    selected_tags = sidebar(data)

    st.title("📂 Tareas de Trading – Mentoría")

    # Root view
    if st.session_state.current_folder is None:
        st.header("Carpetas")
        if not data:
            st.info("Añade una carpeta en la barra lateral ⬅️")
        for name in data:
            st.button(f"🗂️ {name}", key=f"home_{name}", on_click=lambda n=name: navigate_folder(n))
        return

    # Inside folder
    folder_name = st.session_state.current_folder
    folder = data[folder_name]

    col_back, col_title = st.columns([1, 8])
    with col_back:
        st.button("⬅️", help="Volver a carpetas", on_click=back_to_root)
    with col_title:
        st.header(folder_name)

    # Create subpage
    st.text_input("Nueva subpágina", key="new_task", placeholder="Ej: Patrón EURUSD 4H")
    st.button("➕ Crear subpágina", on_click=add_task)

    # Filtered listing
    task_items = folder.items()
    if selected_tags:
        task_items = [(k, v) for k, v in task_items if set(v.get("tags", [])) & set(selected_tags)]

    st.markdown("---")
    for task_name, task_data in task_items:
        col1, col2 = st.columns([1, 5])
        with col1:
            if task_data["images"]:
                url = task_data["images"][0]
                st.markdown(f"[![thumb]({url})]({url})", unsafe_allow_html=True)
        with col2:
            tags = " ".join(f"[{t}]" for t in task_data.get("tags", []))
            stars = "★" * task_data.get("stars", 0)
            st.button(f"{task_name} {stars} {tags}", key=f"open_{task_name}", on_click=lambda n=task_name: open_task(n))

    # Subpage view
    if st.session_state.current_task:
        task_name = st.session_state.current_task
        task = folder[task_name]

        st.divider()
        st.subheader("Detalles")

        st.text_input("Título", value=task_name, key="rename_task_input")
        st.button("Guardar título", on_click=rename_task)

        st.checkbox("Confirmar eliminación", key="confirm_delete")
        st.button("🗑️ Eliminar subpágina", on_click=delete_task, type="secondary")

        st.markdown("### Añadir imagen")
        st.text_input("URL (TradingView)", key="new_img", placeholder="https://...")
        st.button("Añadir imagen", on_click=add_image)

        if task["images"]:
            for i, url in enumerate(task["images"], 1):
                st.image(url, width=660, caption=f"Imagen {i}")
                st.markdown(f"[🔗 Abrir en TradingView]({url})", unsafe_allow_html=True)
        else:
            st.write("*Sin imágenes aún*")

        st.markdown("### Comentarios")
        comment = st.text_area("Área de comentarios", value=task.get("comments", ""))
        if st.button("Guardar comentario"):
            task["comments"] = comment
            save_data(data)
            st.success("Comentario guardado ✔️")

        st.markdown("### Estado")
        current_state = next((t for t in task.get("tags", []) if t in DEFAULT_STATE_TAGS), "No revisada")
        sel_state = st.radio("Etiqueta de estado", DEFAULT_STATE_TAGS, index=DEFAULT_STATE_TAGS.index(current_state))
        if sel_state != current_state:
            task["tags"] = [t for t in task["tags"] if t not in DEFAULT_STATE_TAGS] + [sel_state]
            save_data(data)

        st.markdown("### Etiquetas personalizadas")
        new_tag_str = st.text_input("Añadir etiquetas (coma)")
        if st.button("Guardar etiquetas") and new_tag_str.strip():
            new_tags = [t.strip() for t in new_tag_str.split(",") if t.strip()]
            task["tags"].extend([t for t in new_tags if t not in task["tags"]])
            save_data(data)
            rerun()

        st.markdown("### Valoración ⭐")
        stars = st.slider("0-5", 0, 5, task.get("stars", 0), key=f"star_{task_name}")
        if stars != task.get("stars", 0):
            task["stars"] = stars
            save_data(data)

# ---------------------------------------------------------------------------
if __name__ == "__main__":
    main()
