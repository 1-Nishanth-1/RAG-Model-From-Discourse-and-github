import os
import json
import re
from pathlib import Path
from bs4 import BeautifulSoup
import google.generativeai as genai
import os
from dotenv import load_dotenv


load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-2.0-flash")

Path("markdowns2").mkdir(exist_ok=True)

def sanitize_filename(text):
    return re.sub(r"[^\w\-]", "-", text.lower()).strip("-")

import requests
import base64

def explain_image_with_flash2(img_url):
    try:
        
        response = requests.get(img_url)
        response.raise_for_status()

        
        image_data = base64.b64encode(response.content).decode("utf-8")

        
        gemini_input = [
            {
                "text": "Explain the content of this image in the context of an academic discussion forum and extract text from the image. Focus on providing a concise and informative description that would help users understand the image's relevance to the discussion, do not include solution or anything that is not relevant to the image.",
            },
            {
                "inline_data": {
                    "mime_type": "image/png",  
                    "data": image_data
                }
            }
        ]

        
        result = model.generate_content(gemini_input)
        print(img_url)
        print(result)
        return result.text.strip()

    except Exception as e:
        return f"_Gemini Flash 2.0 error: {e}_"
    
def is_valid_image(img_url):
    
    blocked_patterns = [
        "emoji.discourse-cdn.com",  
        "avatar",                   
        "gravatar",                
        "user_avatar",             
    ]
    return not any(p in img_url for p in blocked_patterns)


def process_html(html, topic_id, post_no):
    soup = BeautifulSoup(html, "html.parser")

    for img in soup.find_all("img"):
        img_url = img.get("src")
        if img_url and is_valid_image(img_url):
            description = explain_image_with_flash2(img_url)
            md_img = f"![Image]({img_url})\n\n> **Flash 2.0 Description:** {description}\n"
            img.replace_with(md_img)
        else:
            
            img.decompose()

    return soup.get_text()


with open("tds_kb_full_posts.json", "r", encoding="utf-8") as f:
    topics = json.load(f)

for topic in topics:
    filename = sanitize_filename(f"{topic['topic_id']}-{topic['title']}") + ".md"
    with open(os.path.join("markdowns2", filename), "w", encoding="utf-8") as md:
        md.write(f"# {topic['title']}\n\n")
        md.write(f"**Topic ID**: {topic['topic_id']}\n\n**Slug**: {topic['slug']}\n\n")
        md.write(f"[View Topic](https://discourse.onlinedegree.iitm.ac.in/t/{topic['slug']}/{topic['topic_id']})\n\n")
        md.write("## Posts\n\n")
        for post in topic["posts"]:
            username = post["username"]
            post_number = post["post_number"]
            post_url = post["url"]
            text = process_html(post["html"], topic['topic_id'], post_number)

            md.write(f"---\n\n### {username} ([Post #{post_number}]({post_url}))\n\n")
            md.write(text.strip() + "\n\n")

print("✅ Markdown files with Flash 2.0 descriptions created.")
