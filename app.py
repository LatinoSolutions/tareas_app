import streamlit as st
import json
from pathlib import Path
from typing import Dict, List
import base64

"""
Trading Tasks App – v1.3 (estabilidad)
======================================
Corregido ▸ errores al crear subpáginas y renombrar tareas.
Mejoras
-------
* **Callbacks seguros** para crear carpetas, subpáginas, imágenes.
* **Renombrar**: campo texto + botón «Guardar título» (evita crash).
* Uso de `st.rerun()` (estable) en vez de `st.experimental_rerun()`.
* Keys de widgets únicas para sliders y textos.
"""

DATA_FILE = Path("data.json")
DEFAULT_STATE_TAGS = ["Revisada", "No revisada", "Comentario pendiente"]
STAR_RANGE = list(range(6))  # 0‑5 estrellas

# ---------------------------------------------------------------------------
# Datos helpers
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

def init_session_state():
    defaults = {
        "current_folder": None,
        "current_task": None,
        "new_folder": "",
        "new_task": "",
        "new_img": "",
        "rename_task_input": "",
    }
    for k, v in defaults.items():
        st.session_state.setdefault(k, v)

# ---------------------------------------------------------------------------
# Callbacks
# ---------------------------------------------------------------------------

def add_folder_callback():
    data = load_data()
    name = st.session_state.new_folder.strip()
    if not name:
        st.sidebar.warning("Escribe un nombre primero")
        return
    if name in data:
        st.sidebar.warning("La carpeta ya existe")
        return
    data[name] = {}
    save_data(data)
    st.session_state.new_folder = ""
    st.sidebar.success("Carpeta creada ✔️")
    st.rerun()


def add_task_callback():
    data = load_data()
    folder = data[st.session_state.current_folder]
    title = st.session_state.new_task.strip()
    if not title:
        st.warning("Nombre vacío")
        return
    if title in folder:
        st.warning("La subpágina ya existe")
        return
    folder[title] = {"images": [], "comments": "", "tags": ["No revisada"], "stars": 0}
    save_data(data)
    st.session_state.new_task = ""
    st.session_state.current_task = title
    st.rerun()


def add_image_callback():
    data = load_data()
    folder = data[st.session_state.current_folder]
    task = folder[st.session_state.current_task]
    url = st.session_state.new_img.strip()
    if url:
        task["images"].append(url)
        save_data(data)
        st.session_state.new_img = ""
        st.rerun()
    else:
        st.warning("URL vacía")


def rename_task_callback():
    data = load_data()
    folder = data[st.session_state.current_folder]
    old_name = st.session_state.current_task
    new_name = st.session_state.rename_task_input.strip()
    if not new_name:
        st.warning("Nombre vacío")
        return
    if new_name == old_name:
        return
    if new_name in folder:
        st.warning("Ya existe una tarea con ese nombre")
        return
    folder[new_name] = folder.pop(old_name)
    save_data(data)
    st.session_state.current_task = new_name
    st.session_state.rename_task_input = new_name
    st.success("Título actualizado ✔️")
    st.rerun()

# ---------------------------------------------------------------------------
# Sidebar (backup, creación y filtros)
# ---------------------------------------------------------------------------

def sidebar(data: Dict) -> List[str]:
    st.sidebar.title("☰ Menú & Filtros")

    # Backup
    st.sidebar.markdown("### Backup")
    if st.sidebar.button("📥 Descargar backup"):
        json_str = json.dumps(data, ensure_ascii=False, indent=2)
        b64 = base64.b64encode(json_str.encode()).decode()
        href = f'<a href="data:application/json;base64,{b64}" download="trading_tasks_backup.json">Descargar archivo</a>'
        st.sidebar.markdown(href, unsafe_allow_html=True)

    uploaded = st.sidebar.file_uploader("📤 Cargar backup", type="json")
    if uploaded:
        data.clear()
        data.update(json.load(uploaded))
        save_data(data)
        st.sidebar.success("Backup restaurado ✔️")
        st.rerun()

    st.sidebar.divider()

    # Nueva carpeta
    st.sidebar.text_input("Nueva carpeta", key="new_folder", placeholder="Ej: Semana 2")
    st.sidebar.button("➕ Crear carpeta", on_click=add_folder_callback, type="primary")

    # Filtros
    all_tags = set(DEFAULT_STATE_TAGS)
    for folder in data.values():
        for task in folder.values():
            all_tags.update(task.get("tags", []))
    return st.sidebar.multiselect("Filtrar por etiquetas", sorted(all_tags))

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    init_session_state()
    data = load_data()

    selected_tags = sidebar(data)
    st.title("📂 Tareas de Trading – Mentoría")

    # --- Vista de carpetas ------------------------------------------------
    if st.session_state.current_folder is None:
        st.header("Carpetas")
        if not data:
            st.info("Crea tu primera carpeta en la barra lateral ✨")
        for name in data:
            st.button(
                f"🗂️ {name}", key=f"folder_{name}",
                on_click=lambda n=name: st.session_state.update({"current_folder": n, "current_task": None})
            )
        return

    # --- Dentro de carpeta ----------------------------------------------
    folder_name = st.session_state.current_folder
    folder = data[folder_name]
    st.header(f"📁 {folder_name}")

    if st.button("⬅️ Volver a carpetas"):
        st.session_state.update({"current_folder": None, "current_task": None})
        st.rerun()

    # Crear subpágina
    st.text_input("Nueva subpágina", key="new_task", placeholder="Ej: Patrón BTC 4H")
    st.button("➕ Crear subpágina", on_click=add_task_callback)

    # Filtrar tareas por etiquetas
    task_items = folder.items()
    if selected_tags:
        task_items = [(k, v) for k, v in task_items if set(v.get("tags", [])) & set(selected_tags)]

    # Listado con miniatura
    for task_name, task_data in task_items:
        col1, col2 = st.columns([1, 5])
        with col1:
            if task_data["images"]:
                st.image(task_data["images"][0], width=120)
        with col2:
            tag_badges = " ".join(f"[{t}]" for t in task_data.get("tags", []))
            stars = "★" * task_data.get("stars", 0)
            st.button(
                f"{task_name} {stars} {tag_badges}", key=f"task_btn_{task_name}",
                on_click=lambda n=task_name: st.session_state.update({"current_task": n})
            )

    # --- Subpágina --------------------------------------------------------
    if st.session_state.current_task:
        task_name = st.session_state.current_task
        task = folder[task_name]

        st.divider()
        st.subheader("Detalles de la subpágina")

        # Renombrar título
        st.text_input(
            "Título", value=task_name, key="rename_task_input"
        )
        st.button("Guardar título", on_click=rename_task_callback)

        # Volver botón
        if st.button("⬅️ Volver a subpáginas"):
            st.session_state.current_task = None
            st.rerun()

        # Galería
        st.text_input("URL de imagen (TradingView)", key="new_img", placeholder="https://...")
        st.button("Añadir imagen", on_click=add_image_callback)

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
            st.success("Comentario guardado ✔️")

        # Etiquetas
        st.markdown("### Etiquetas")
        new_tag_str = st.text_input("Añadir etiquetas personalizadas (coma)")
        if st.button("Guardar etiquetas") and new_tag_str.strip():
            new_tags = [t.strip() for t in new_tag_str.split(",") if t.strip()]
            task["tags"].extend([t for t in new_tags if t not in task["tags"]])
            save_data(data)
            st.rerun()

        state_tags = st.multiselect(
            "Etiquetas de estado", DEFAULT_STATE_TAGS,
            default=[t for t in task["tags"] if t in DEFAULT_STATE_TAGS]
        )
        # Sincronizar
        changed = False
        for tag in DEFAULT_STATE_TAGS:
            if tag in state_tags and tag not in task["tags"]:
                task["tags"].append(tag); changed = True
            elif tag not in state_tags and tag in task["tags"]:
                task["tags"].remove(tag); changed = True
        if changed:
            save_data(data)

        # Estrellas
        star_key = f"star_slider_{task_name}"
        stars = st.slider("Valoración (0‑5 ⭐)", 0, 5, task.get("stars", 0), key=star_key)
        if stars != task.get("stars", 0):
            task["stars"] = stars
            save_data(data)

# ---------------------------------------------------------------------------
if __name__ == "__main__":
    main()
