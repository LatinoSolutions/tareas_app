import streamlit as st
import json
from pathlib import Path
from typing import Dict, List

"""
Aplicación de Tareas de Trading para mentorías.
------------------------------------------------
Esta es una versión mínima y funcional con las siguientes características:
1. Página de inicio con listado de carpetas (tareas generales).
2. Dentro de cada carpeta se pueden crear Subpáginas (tareas específicas).
3. Cada Subpágina permite: añadir links de imágenes (TradingView) que se
   muestran como galería, añadir/editar etiquetas y escribir comentarios.
4. Sistema de filtros por etiquetas en la barra lateral.

★ Sugerencia: guarda el archivo como app.py en la raíz del repositorio y
   añade un requirements.txt con "streamlit>=1.35".
"""

# --- Configuración del archivo de datos -------------------------------------
DATA_FILE = Path("data.json")
DEFAULT_STATE_TAGS = ["Revisada", "No revisada", "Comentario pendiente"]

# ---------------------------------------------------------------------------
# Funciones auxiliares
# ---------------------------------------------------------------------------

def load_data() -> Dict:
    """Carga los datos desde DATA_FILE o devuelve estructura vacía."""
    if DATA_FILE.exists():
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_data(data: Dict) -> None:
    """Guarda los datos en DATA_FILE."""
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# Sidebar – filtros y creación de nuevas carpetas
# ---------------------------------------------------------------------------

st.sidebar.title("Gestión de Carpetas y Filtros")

data = load_data()

# Crear nueva carpeta
def new_folder():
    if st.sidebar.session_state.new_folder.strip():
        name = st.sidebar.session_state.new_folder.strip()
        if name not in data:
            data[name] = {}
            save_data(data)
            st.sidebar.success(f"Carpeta '{name}' creada")
        else:
            st.sidebar.warning("La carpeta ya existe")
        st.sidebar.session_state.new_folder = ""

st.sidebar.text_input("Nombre de nueva carpeta", key="new_folder")
st.sidebar.button("Crear carpeta", on_click=new_folder)

# Filtro de etiquetas
all_custom_tags: List[str] = []
for folder in data.values():
    for task in folder.values():
        all_custom_tags.extend(task.get("tags", []))

unique_tags = sorted(set(DEFAULT_STATE_TAGS + all_custom_tags))
selected_tags = st.sidebar.multiselect("Filtrar por etiquetas", unique_tags, default=[])

# ---------------------------------------------------------------------------
# Página principal – listado de carpetas
# ---------------------------------------------------------------------------

st.title("📂 Tareas de Trading – Mentoría")

folder_names = list(data.keys())

if "current_folder" not in st.session_state:
    st.session_state.current_folder = None
if "current_task" not in st.session_state:
    st.session_state.current_task = None

# --- Selección de carpeta ---------------------------------------------------
if st.session_state.current_folder is None:
    st.header("Carpetas")
    if not folder_names:
        st.info("Aún no hay carpetas. Usa la barra lateral para crear la primera ✨")
    for name in folder_names:
        st.button(f"🗂️ {name}", key=f"folder_{name}", on_click=lambda n=name: st.session_state.update({"current_folder": n}))
else:
    folder = data[st.session_state.current_folder]
    st.header(f"Carpeta: {st.session_state.current_folder}")

    # Botón para volver
    if st.button("⬅️ Volver a carpetas"):
        st.session_state.current_folder = None
        st.session_state.current_task = None
        st.experimental_rerun()

    # Crear nueva subpágina (tarea específica)
    def add_task():
        title = st.session_state.new_task.strip()
        if title:
            if title not in folder:
                folder[title] = {"images": [], "comments": "", "tags": ["No revisada"]}
                save_data(data)
                st.session_state.new_task = ""
                st.experimental_rerun()
            else:
                st.warning("La subpágina ya existe")

    st.text_input("Nombre de nueva subpágina", key="new_task")
    st.button("Crear subpágina", on_click=add_task)

    # Filtrar tareas por etiquetas, si se seleccionaron
    task_items = folder.items()
    if selected_tags:
        task_items = [(k, v) for k, v in task_items if set(selected_tags) & set(v.get("tags", []))]

    # Listado de subpáginas
    for task_name, task_data in task_items:
        tag_badges = " ".join([f"[{t}]" for t in task_data.get("tags", [])])
        label = f"📄 {task_name} {tag_badges}"
        st.button(label, key=f"task_{task_name}", on_click=lambda n=task_name: st.session_state.update({"current_task": n}))

    # -----------------------------------------------------------------------
    # Vista de una Subpágina específica
    # -----------------------------------------------------------------------
    if st.session_state.current_task:
        task = folder[st.session_state.current_task]
        st.subheader(f"Subpágina: {st.session_state.current_task}")

        # Botón para volver del task
        if st.button("⬅️ Volver a subpáginas"):
            st.session_state.current_task = None
            st.experimental_rerun()

        # --- Galería de imágenes -------------------------------------------
        def add_image():
            url = st.session_state.new_img.strip()
            if url:
                task["images"].append(url)
                save_data(data)
                st.session_state.new_img = ""

        st.text_input("Pegar URL de imagen de TradingView", key="new_img")
        st.button("Añadir imagen", on_click=add_image)

        if task["images"]:
            st.image(task["images"], width=300, caption=[f"Imagen {i+1}" for i in range(len(task["images"]))])
        else:
            st.write("*Aún no hay imágenes*")

        # --- Comentarios ----------------------------------------------------
        st.markdown("### Comentarios del mentor")
        comment = st.text_area("Escribe o edita comentarios aquí", value=task.get("comments", ""))
        if st.button("Guardar comentario"):
            task["comments"] = comment
            save_data(data)
            st.success("Comentario guardado")

        # --- Etiquetas ------------------------------------------------------
        st.markdown("### Etiquetas")
        # Crear etiqueta personalizada
        new_tag = st.text_input("Crear o seleccionar etiquetas personalizadas (separadas por coma)", value="")
        if st.button("Añadir etiquetas personalizadas") and new_tag.strip():
            new_tags = [t.strip() for t in new_tag.split(",") if t.strip()]
            task["tags"].extend([t for t in new_tags if t not in task["tags"]])
            save_data(data)
            st.experimental_rerun()

        current_tags = st.multiselect("Etiquetas de estado", DEFAULT_STATE_TAGS, default=[t for t in task["tags"] if t in DEFAULT_STATE_TAGS])
        # Sincronizar etiquetas de estado
        for tag in DEFAULT_STATE_TAGS:
            if tag in current_tags and tag not in task["tags"]:
                task["tags"].append(tag)
            if tag not in current_tags and tag in task["tags"]:
                task["tags"].remove(tag)
        save_data(data)

        st.write("**Etiquetas actuales:**", ", ".join(task["tags"]))
