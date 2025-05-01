import streamlit as st
import json
from pathlib import Path
from typing import Dict, List

"""
Trading Tasks App – Streamlit
----------------------------
Versión corregida y simplificada para que **añadir carpetas y subpáginas funcione sin errores**.

✓ Acceso correcto a `st.session_state` (sin prefijo `st.sidebar` que causaba fallo).
✓ Inicialización segura de claves en `session_state`.
✓ Código encapsulado en `main()` para claridad.
✓ Mensajes de estado en la barra lateral y la página principal.
"""

DATA_FILE = Path("data.json")
DEFAULT_STATE_TAGS = ["Revisada", "No revisada", "Comentario pendiente"]

# ---------------------------------------------------------------------------
# Utilidades de datos
# ---------------------------------------------------------------------------

def load_data() -> Dict:
    if DATA_FILE.exists():
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_data(data: Dict) -> None:
    DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

# ---------------------------------------------------------------------------
# Inicializar variables en session_state
# ---------------------------------------------------------------------------

def init_session_state():
    defaults = {
        "current_folder": None,
        "current_task": None,
        "new_folder": "",
        "new_task": "",
        "new_img": "",
    }
    for k, v in defaults.items():
        st.session_state.setdefault(k, v)

# ---------------------------------------------------------------------------
# Sidebar: creación de carpetas y filtros
# ---------------------------------------------------------------------------

def sidebar_section(data: Dict) -> List[str]:
    st.sidebar.title("Gestión de Carpetas & Filtros")

    # --- Crear carpeta -----------------------------------------------------
    def add_folder():
        name = st.session_state.get("new_folder", "").strip()
        if not name:
            st.sidebar.warning("Escribe un nombre antes de crear")
            return
        if name in data:
            st.sidebar.warning("La carpeta ya existe")
            return
        data[name] = {}
        save_data(data)
        st.session_state.new_folder = ""
        st.sidebar.success(f"Carpeta '{name}' creada")

    st.sidebar.text_input("Nombre de nueva carpeta", key="new_folder", placeholder="Ej: Semana 1")
    st.sidebar.button("Crear carpeta", on_click=add_folder, type="primary")

    # --- Filtros por etiquetas --------------------------------------------
    all_custom_tags: List[str] = []
    for folder in data.values():
        for task in folder.values():
            all_custom_tags.extend(task.get("tags", []))
    unique_tags = sorted(set(DEFAULT_STATE_TAGS + all_custom_tags))
    return st.sidebar.multiselect("Filtrar por etiquetas", unique_tags, default=[])

# ---------------------------------------------------------------------------
# Página principal
# ---------------------------------------------------------------------------

def main():
    init_session_state()
    data = load_data()

    selected_tags = sidebar_section(data)

    st.title("📂 Tareas de Trading – Mentoría")

    # ---------------------------------------------------------------------
    # Vista de listado de carpetas
    # ---------------------------------------------------------------------
    if st.session_state.current_folder is None:
        st.header("Carpetas")
        if not data:
            st.info("Aún no hay carpetas. Usa la barra lateral para crear la primera ✨")
        for name in data:
            st.button(
                f"🗂️ {name}",
                key=f"folder_{name}",
                on_click=lambda n=name: st.session_state.update({"current_folder": n})
            )
        return  # fin vista principal

    # ---------------------------------------------------------------------
    # Vista dentro de una carpeta
    # ---------------------------------------------------------------------
    folder_name = st.session_state.current_folder
    folder = data[folder_name]
    st.header(f"Carpeta: {folder_name}")

    if st.button("⬅️ Volver a carpetas"):
        st.session_state.update({"current_folder": None, "current_task": None})
        st.experimental_rerun()

    # --- Crear subpágina --------------------------------------------------
    def add_task():
        title = st.session_state.get("new_task", "").strip()
        if not title:
            st.warning("Escribe un nombre antes de crear")
            return
        if title in folder:
            st.warning("La subpágina ya existe")
            return
        folder[title] = {"images": [], "comments": "", "tags": ["No revisada"]}
        save_data(data)
        st.session_state.new_task = ""
        st.experimental_rerun()

    st.text_input("Nombre de nueva subpágina", key="new_task", placeholder="Ej: Ejemplo EURUSD 1H")
    st.button("Crear subpágina", on_click=add_task)

    # Filtrar subpáginas por etiquetas si procede
    task_items = folder.items()
    if selected_tags:
        task_items = [(k, v) for k, v in task_items if set(v.get("tags", [])) & set(selected_tags)]

    # --- Listado de subpáginas -------------------------------------------
    for task_name, task_data in task_items:
        tag_badges = " ".join(f"[{t}]" for t in task_data.get("tags", []))
        st.button(
            f"📄 {task_name} {tag_badges}",
            key=f"task_{task_name}",
            on_click=lambda n=task_name: st.session_state.update({"current_task": n})
        )

    # ---------------------------------------------------------------------
    # Vista de una Subpágina específica
    # ---------------------------------------------------------------------
    if st.session_state.current_task:
        task_name = st.session_state.current_task
        task = folder[task_name]

        st.subheader(f"Subpágina: {task_name}")
        if st.button("⬅️ Volver a subpáginas"):
            st.session_state.current_task = None
            st.experimental_rerun()

        # --- Galería de imágenes -----------------------------------------
        def add_image():
            url = st.session_state.get("new_img", "").strip()
            if url:
                task["images"].append(url)
                save_data(data)
                st.session_state.new_img = ""
                st.experimental_rerun()

        st.text_input("URL de imagen de TradingView", key="new_img", placeholder="https://...")
        st.button("Añadir imagen", on_click=add_image)

        if task["images"]:
            st.image(task["images"], width=320, caption=[f"Img {i+1}" for i in range(len(task["images"]))])
        else:
            st.write("*Aún no hay imágenes*")

        # --- Comentarios --------------------------------------------------
        st.markdown("### Comentarios del mentor")
        comment = st.text_area("Escribe o edita comentarios", value=task.get("comments", ""))
        if st.button("Guardar comentario"):
            task["comments"] = comment
            save_data(data)
            st.success("Comentario guardado ✅")

        # --- Etiquetas ----------------------------------------------------
        st.markdown("### Etiquetas")
        new_tag_str = st.text_input("Añadir etiquetas personalizadas (coma separadas)")
        if st.button("Guardar etiquetas personalizadas") and new_tag_str.strip():
            new_tags = [t.strip() for t in new_tag_str.split(",") if t.strip()]
            task["tags"].extend([t for t in new_tags if t not in task["tags"]])
            save_data(data)
            st.experimental_rerun()

        state_tags = st.multiselect(
            "Etiquetas de estado", DEFAULT_STATE_TAGS,
            default=[t for t in task["tags"] if t in DEFAULT_STATE_TAGS]
        )
        # Sincronizar etiquetas de estado
        for tag in DEFAULT_STATE_TAGS:
            if tag in state_tags and tag not in task["tags"]:
                task["tags"].append(tag)
            elif tag not in state_tags and tag in task["tags"]:
                task["tags"].remove(tag)
        save_data(data)

        st.write("**Etiquetas actuales:**", ", ".join(task["tags"]))

# ---------------------------------------------------------------------------
if __name__ == "__main__":
    main()
