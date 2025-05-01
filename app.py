import streamlit as st
import json
from pathlib import Path
from typing import Dict, List
import base64

"""
Trading Tasks App – v1.6 (gestión de carpetas)
==============================================
Novedades
---------
* **Renombrar carpeta**: campo de texto y botón «Guardar nombre».
* **Eliminar carpeta**: botón 🗑️ con casilla de confirmación.
* Ajustada la inicialización de `session_state` y helpers.
* Mantiene filtros globales y resto de funciones de v1.5.
"""

DATA_FILE = Path("data.json")
DEFAULT_STATE_TAGS = ["Revisada", "No revisada", "Comentario pendiente"]

# ---------------------------------------------------------------------------
# Helpers de datos
# ---------------------------------------------------------------------------

def load_data() -> Dict:
    if DATA_FILE.exists():
        return json.loads(DATA_FILE.read_text("utf-8"))
    return {}


def save_data(data: Dict) -> None:
    DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), "utf-8")

# ---------------------------------------------------------------------------
# Estado inicial
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
        "rename_folder_input": "",
        "confirm_delete_folder": False,
    }
    for k, v in defaults.items():
        st.session_state.setdefault(k, v)

# ---------------------------------------------------------------------------
# Navegación
# ---------------------------------------------------------------------------

def open_task(name: str):
    st.session_state.current_task = name


def back_to_root():
    st.session_state.current_folder = None
    st.session_state.current_task = None


def navigate_folder(name: str):
    st.session_state.update({"current_folder": name, "current_task": None, "rename_folder_input": name})

# ---------------------------------------------------------------------------
# Acciones carpetas
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


def rename_folder():
    data = load_data()
    old = st.session_state.current_folder
    new = st.session_state.rename_folder_input.strip()
    if not new:
        st.warning("Nombre vacío")
        return
    if new == old:
        return
    if new in data:
        st.warning("Ya existe una carpeta con ese nombre")
        return
    data[new] = data.pop(old)
    save_data(data)
    st.session_state.current_folder = new
    st.success("Carpeta renombrada ✔️")


def delete_folder():
    if not st.session_state.confirm_delete_folder:
        st.warning("Marca la casilla de confirmación primero")
        return
    data = load_data()
    data.pop(st.session_state.current_folder, None)
    save_data(data)
    back_to_root()
    st.session_state.confirm_delete_folder = False
    st.success("Carpeta eliminada 🗑️")

# ---------------------------------------------------------------------------
# Acciones tareas
# ---------------------------------------------------------------------------

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

# ---------------------------------------------------------------------------
# Sidebar
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
            data.clear(); data.update(json.load(uploaded)); save_data(data); st.success("Backup restaurado"); st.experimental_rerun()

    st.sidebar.divider()

    # Carpetas
    st.sidebar.markdown("### Carpetas")
    if data:
        for name in data:
            st.sidebar.button(name, key=f"side_{name}", on_click=lambda n=name: navigate_folder(n))
    else:
        st.sidebar.write("*Sin carpetas aún*")

    st.sidebar.text_input("Nueva carpeta", key="new_folder", placeholder="Ej: Semana 1")
    st.sidebar.button("➕ Crear carpeta", on_click=add_folder, type="primary")

    st.sidebar.divider()

    # Filtro etiquetas
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

    # ---------------- Página principal -------------------------------
    if st.session_state.current_folder is None:
        if selected_tags:
            st.header("Resultados por etiqueta")
            matches = []
            for folder_name, folder in data.items():
                for task_name, task in folder.items():
                    if set(task.get("tags", [])) & set(selected_tags):
                        matches.append((folder_name, task_name, task))

            if not matches:
                st.info("No se encontraron tareas con esas etiquetas")
            else:
                for folder_name, task_name, task in matches:
                    tags = " ".join(f"[{t}]" for t in task.get("tags", []))
                    stars = "★" * task.get("stars", 0)
                    label = f"{folder_name} / {task_name} {stars} {tags}"
                    st.button(label, key=f"match_{folder_name}_{task_name}", on_click=lambda f=folder_name, t=task_name: (navigate_folder(f), open_task(t)))
            return

        # Sin filtros: vista de carpetas
        st.header("Carpetas")
        if not data:
            st.info("Añade una carpeta en la barra lateral ⬅️")
        for name in data:
            st.button(f"🗂️ {name}", key=f"home_{name}", on_click=lambda n=name: navigate_folder(n))
        return

    # ---------------- Dentro de carpeta ------------------------------
    folder_name = st.session_state.current_folder
    folder = data[folder_name]

    col_back, col_title = st.columns([1, 8])
    with col_back:
        st.button("⬅️", help="Volver a carpetas", on_click=back_to_root)
    with col_title:
        st.header(folder
