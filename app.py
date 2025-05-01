import streamlit as st
import json
from pathlib import Path
from typing import Dict, List
import base64

"""
Trading Tasks App – v1.2
=======================
➡️ Novedades
------------
* **Backup**: botón *Descargar backup* y opción *Cargar backup (.json)*.
* **Miniaturas**: pre‑visualización de cada imagen a 660 px (configurable).
* **Renombrar subpágina** (título editable).
* **Valoración** con 0–5 ⭐ (estrellas unicode).
* **Bug fix**: eliminado `st.experimental_rerun()` que generaba `AttributeError`.
"""

DATA_FILE = Path("data.json")
DEFAULT_STATE_TAGS = ["Revisada", "No revisada", "Comentario pendiente"]
STAR_RANGE = list(range(6))  # 0‑5 estrellas

# ---------------------------------------------------------------------------
# Utilidades de datos
# ---------------------------------------------------------------------------

def load_data() -> Dict:
    if DATA_FILE.exists():
        return json.loads(DATA_FILE.read_text("utf-8"))
    return {}


def save_data(data: Dict) -> None:
    DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), "utf-8")

# ---------------------------------------------------------------------------
# Session state defaults
# ---------------------------------------------------------------------------

def init_session_state():
    defaults = {
        "current_folder": None,
        "current_task": None,
        "new_folder": "",
        "new_task": "",
        "new_img": "",
        "rename_task": "",
    }
    for k, v in defaults.items():
        st.session_state.setdefault(k, v)

# ---------------------------------------------------------------------------
# Sidebar controls
# ---------------------------------------------------------------------------

def sidebar(data: Dict) -> List[str]:
    st.sidebar.title("☰ Menú & Filtros")

    # -- Backup -----------------------------------------------------------
    st.sidebar.markdown("### Backup")
    if st.sidebar.button("📥 Descargar backup"):
        json_str = json.dumps(data, ensure_ascii=False, indent=2)
        b64 = base64.b64encode(json_str.encode()).decode()
        href = f'<a href="data:application/json;base64,{b64}" download="trading_tasks_backup.json">Bajar archivo</a>'
        st.sidebar.markdown(href, unsafe_allow_html=True)

    uploaded = st.sidebar.file_uploader("📤 Cargar backup (.json)", type="json")
    if uploaded:
        data.clear()
        data.update(json.load(uploaded))
        save_data(data)
        st.sidebar.success("Backup restaurado ✔️")
        st.experimental_rerun()

    st.sidebar.markdown("---")

    # -- Nueva carpeta ----------------------------------------------------
    st.sidebar.text_input("Nueva carpeta", key="new_folder", placeholder="Ej: Semana 2")
    if st.sidebar.button("➕ Crear carpeta", type="primary"):
        name = st.session_state.new_folder.strip()
        if name:
            if name in data:
                st.sidebar.warning("Ya existe esa carpeta")
            else:
                data[name] = {}
                save_data(data)
                st.sidebar.success("Carpeta creada")
                st.session_state.new_folder = ""
                st.experimental_rerun()
        else:
            st.sidebar.warning("Escribe un nombre primero")

    # -- Filtros ----------------------------------------------------------
    all_tags = set(DEFAULT_STATE_TAGS)
    for folder in data.values():
        for task in folder.values():
            all_tags.update(task.get("tags", []))
    return st.sidebar.multiselect("Filtrar por etiquetas", sorted(all_tags))

# ---------------------------------------------------------------------------
# Main app
# ---------------------------------------------------------------------------

def main():
    init_session_state()
    data = load_data()

    selected_tags = sidebar(data)

    st.title("📂 Tareas de Trading – Mentoría")

    # ---------------- Carpeta raíz --------------------------------------
    if st.session_state.current_folder is None:
        st.header("Carpetas")
        if not data:
            st.info("Crea tu primera carpeta en la barra lateral ✨")
        for name in data:
            st.button(
                f"🗂️ {name}", key=f"folder_{name}",
                on_click=lambda n=name: st.session_state.update({"current_folder": n})
            )
        return

    # ---------------- Dentro de carpeta ---------------------------------
    folder_name = st.session_state.current_folder
    folder = data[folder_name]
    st.header(f"📁 {folder_name}")

    if st.button("⬅️ Volver a carpetas"):
        st.session_state.update({"current_folder": None, "current_task": None})
        return  # sin rerun

    # Crear subpágina (tarea específica)
    st.text_input("Nueva subpágina", key="new_task", placeholder="Ej: Patrón BTC 4H")
    if st.button("➕ Crear subpágina"):
        title = st.session_state.new_task.strip()
        if title and title not in folder:
            folder[title] = {"images": [], "comments": "", "tags": ["No revisada"], "stars": 0}
            save_data(data)
            st.session_state.new_task = ""
            st.experimental_rerun()
        else:
            st.warning("Nombre vacío o duplicado")

    # Filtrar
    task_items = folder.items()
    if selected_tags:
        task_items = [(k, v) for k, v in task_items if set(v.get("tags", [])) & set(selected_tags)]

    # Listado de subpáginas ✅ miniatura
    for task_name, task_data in task_items:
        col1, col2 = st.columns([1, 5])
        with col1:
            if task_data["images"]:
                st.image(task_data["images"][0], width=120)
        with col2:
            tag_badges = " ".join(f"[{t}]" for t in task_data.get("tags", []))
            stars = "★" * task_data.get("stars", 0)
            st.button(
                f"{task_name} {stars} {tag_badges}", key=f"task_{task_name}",
                on_click=lambda n=task_name: st.session_state.update({"current_task": n})
            )

    # ---------------- Subpágina -----------------------------------------
    if st.session_state.current_task:
        task_name = st.session_state.current_task
        task = folder[task_name]

        st.subheader("Subpágina:")
        st.text_input(
            "Título de la subpágina", value=task_name, key="rename_task",
            on_change=lambda: rename_task(task_name, data, folder)
        )

        if st.button("⬅️ Volver a subpáginas"):
            st.session_state.current_task = None
            return

        # Galería
        st.text_input("URL de imagen (TradingView)", key="new_img", placeholder="https://...")
        if st.button("Añadir imagen"):
            url = st.session_state.new_img.strip()
            if url:
                task["images"].append(url)
                save_data(data)
                st.session_state.new_img = ""
                st.experimental_rerun()

        if task["images"]:
            st.image(task["images"], width=660)
        else:
            st.write("*Sin imágenes aún*")

        # Comentarios
        st.markdown("### Comentarios")
        comment = st.text_area("Área de comentarios", value=task.get("comments", ""))
        if st.button("Guardar comentario"):
            task["comments"] = comment
            save_data(data)
            st.success("Comentario guardado")

        # Etiquetas
        st.markdown("### Etiquetas")
        new_tag_str = st.text_input("Añadir etiquetas personalizadas (coma)")
        if st.button("Guardar etiquetas") and new_tag_str.strip():
            new_tags = [t.strip() for t in new_tag_str.split(",") if t.strip()]
            task["tags"].extend([t for t in new_tags if t not in task["tags"]])
            save_data(data)
            st.experimental_rerun()

        state_tags = st.multiselect(
            "Etiquetas de estado", DEFAULT_STATE_TAGS,
            default=[t for t in task["tags"] if t in DEFAULT_STATE_TAGS]
        )
        synchronize_state_tags(task, state_tags)

        # Estrellas
        st.markdown("### Valoración (0‑5 ⭐)")
        stars = st.slider("Puntuación", 0, 5, task.get("stars", 0), key="star_slider")
        if stars != task.get("stars", 0):
            task["stars"] = stars
            save_data(data)

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def rename_task(old_name: str, data: Dict, folder: Dict):
    new_name = st.session_state.rename_task.strip()
    if new_name and new_name != old_name:
        if new_name in folder:
            st.warning("Ya existe una tarea con ese nombre")
        else:
            folder[new_name] = folder.pop(old_name)
            save_data(data)
            st.session_state.current_task = new_name
            st.experimental_rerun()


def synchronize_state_tags(task: Dict, selected: List[str]):
    changed = False
    # Añadir / quitar en función del multiselect
    for tag in DEFAULT_STATE_TAGS:
        if tag in selected and tag not in task["tags"]:
            task["tags"].append(tag)
            changed = True
        elif tag not in selected and tag in task["tags"]:
            task["tags"].remove(tag)
            changed = True
    if changed:
        save_data(data)

# ---------------------------------------------------------------------------
if __name__ == "__main__":
    main()
