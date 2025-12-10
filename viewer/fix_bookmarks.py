# fix_bookmarks.py
import json
import os

bookmark_files = [
    './viewer/data/bookmarks.json',
    './viewer/appdata/bookmarks.json',
]

for file_path in bookmark_files:
    if os.path.exists(file_path):
        print(f"Processing: {file_path}")
        try:
            with open(file_path, 'r', encoding='utf-8-sig') as f:
                data = json.load(f)

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            print(f"✅ Fixed: {file_path}")
        except Exception as e:
            print(f"❌ Error: {e}")