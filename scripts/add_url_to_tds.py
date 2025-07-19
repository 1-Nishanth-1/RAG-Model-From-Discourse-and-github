import os
import glob

MARKDOWN_DIR = "tools-in-data-science-public"
BASE_URL = "https://tds.s-anand.net/#/"

for filepath in glob.glob(os.path.join(MARKDOWN_DIR, "*.md")):
    filename = os.path.basename(filepath)
    slug = os.path.splitext(filename)[0]  
    new_url_line = f"{BASE_URL}{slug}\n"

    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()

    if lines and lines[0].startswith("https://tds.s-anand.net/#/"):
        if lines[0] != new_url_line:
            lines[0] = new_url_line
            with open(filepath, "w", encoding="utf-8") as f:
                f.writelines(lines)
            print(f"Updated: {filename}")
        else:
            print(f"Already up to date: {filename}")
    else:
        print(f"Skipped (no matching top line): {filename}")
