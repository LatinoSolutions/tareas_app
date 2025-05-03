#!/usr/bin/env python3
"""
Migración de data.json ➜ posts.json (estilo Fotolog)
Uso:
    python migrate_to_posts.py trading_tasks_backup.json
"""
import json, sys, uuid, datetime, pathlib

def main(src_path):
    src = pathlib.Path(src_path)
    if not src.exists():
        print("No encontrado:", src)
        sys.exit(1)

    data = json.loads(src.read_text("utf-8"))
    posts = []
    now_iso = datetime.datetime.utcnow().isoformat()

    for folder_name, folder in data.items():
        for sub_name, sub in folder.items():
            post = {
                "id": str(uuid.uuid4()),
                "created_at": now_iso,           # puedes ajustar si quieres
                "folder": folder_name,
                "title": sub_name,
                "image": sub["images"][0] if sub["images"] else "",
                "gallery": sub["images"][1:],
                "notes": sub.get("comments", ""),
                "tags": sub.get("tags", []),
                "comments": [],
                "private": False
            }
            posts.append(post)

    out = pathlib.Path("posts.json")
    out.write_text(json.dumps(posts, ensure_ascii=False, indent=2), "utf-8")
    print(f"Convertidos {len(posts)} posts ➜ {out}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python migrate_to_posts.py <archivo_json>")
        sys.exit(1)
    main(sys.argv[1])
