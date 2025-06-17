import numpy as np
import json
import requests
import os
import sys
import base64
import tempfile
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import google.generativeai as genai
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
import uvicorn
from dotenv import load_dotenv
import os
app = FastAPI()

load_dotenv()
def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

AIPIPE_TOKEN = os.getenv("AIPIPE_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
PORT=os.getenv("PORT", 8000)
MODEL_NAME = "BAAI/bge-base-en-v1.5"
OPENROUTER_MODEL = "openai/gpt-4o-mini"
GEMINI_MODEL = "gemini-1.5-flash"

print("📦 Loading embedding model and saved data...")
model = SentenceTransformer(MODEL_NAME)
embeddings = np.load("embeddings2.npz")["vectors"]

with open("metadata2.json", "r", encoding="utf-8") as f:
    metadata = json.load(f)

print("🔑 Configuring Gemini...")
genai.configure(api_key=GEMINI_API_KEY)
gemini_model = genai.GenerativeModel(GEMINI_MODEL)

@app.post("/api/")
async def process_query(request: Request):
    try:
        data = await request.json()
        question = data.get("question")
        image_b64 = data.get("image")
        
        if not question:
            raise HTTPException(status_code=400, detail="Missing 'question' in request body")
        
        image_context = ""
        temp_path = None
        
        if image_b64:
            eprint("🖼️ Processing base64 image...")
            try:
                if image_b64.startswith("data:"):
                    header, encoded = image_b64.split(",", 1)
                else:
                    encoded = image_b64
                
                image_data = base64.b64decode(encoded)
                
                with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp_file:
                    temp_file.write(image_data)
                    temp_path = temp_file.name
                
                img = genai.upload_file(temp_path)
                response = gemini_model.generate_content(
                    ["Describe this image in detail, focusing on any text, diagrams, or technical content:", img],
                    request_options={"timeout": 60}
                )
                image_context = response.text.strip()
                eprint("✅ Gemini Image Description Received")
            except Exception as e:
                eprint(f"❌ Error processing image: {str(e)}")
            finally:
                if temp_path and os.path.exists(temp_path):
                    os.unlink(temp_path)

        full_query = question + (f"\n\n[Image Description]\n{image_context}" if image_context else "")

        eprint("\n🔍 Generating embedding for combined query...")
        query_embedding = model.encode([full_query], normalize_embeddings=True)

        boosted_indices = set()
        
        eprint("\n🧠 Calculating cosine similarity for matches...")
        sims = cosine_similarity(query_embedding, embeddings)[0]

        context = []
        added_urls = set()

        for idx in boosted_indices:
            item = metadata[idx]
            url = item.get("url", "")
            context.append(f"{item['text_preview'].strip()}\n(Source: {url})")
            added_urls.add(url)

        top_indices = sims.argsort()[::-1]  
        for idx in top_indices:
            if len(context) >= 15:  
                break
                
            item = metadata[idx]
            url = item.get("url", "")
            if url and url not in added_urls:
                context.append(f"{item['text_preview'].strip()}\n(Source: {url})")
                added_urls.add(url)

        
        if image_context:
            context.append(f"[Image Context]\n{image_context}")

        eprint(f"\n🧠 Using {len(context)} context chunks")

        
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "generate_answer_with_links",
                    "description": "Answer the question based only on provided context.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "answer": {"type": "string"},
                            "links": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "url": {"description": "The https://discourse.onlinedegree.iitm.ac.in/ or s-anand.net source should be the url", "type": "string"},
                                        "text": {"type": "string"}
                                    },
                                    "required": ["url", "text"]
                                }
                            }
                        },
                        "required": ["answer", "links"]
                    }
                }
            }
        ]

        eprint("\n🚀 Sending request to OpenRouter...")
        response = requests.post(
            "https://aipipe.org/openrouter/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {AIPIPE_TOKEN}",
                "Content-Type": "application/json"
            },
            json={
                "model": OPENROUTER_MODEL,
                "messages": [
                    {
                        "role": "system",
                        "content": "Answer using ONLY the provided context."
                    },
                    {
                        "role": "user",
                        "content": f"Context:\n{'-'*50}\n" + '\n\n'.join(context) + 
                                   f"\n{'-'*50}\nQuestion: {question}"
                    }
                ],
                "tools": tools,
                "tool_choice": {"type": "function", "function": {"name": "generate_answer_with_links"}}
            },
            timeout=60
        )

        if response.status_code != 200:
            error_msg = f"OpenRouter API Error {response.status_code}: {response.text}"
            eprint(f"❌ {error_msg}")
            raise HTTPException(status_code=500, detail=error_msg)
        
        response_data = response.json()
        fn_call = response_data["choices"][0]["message"]["tool_calls"][0]
        args = json.loads(fn_call["function"]["arguments"])
        
        output = {
            "answer": args.get("answer", ""),
            "links": []
        }
        
        sources = args.get("links", []) or args.get("sources", [])
        for source in sources:
            output["links"].append({
                "url": source.get("url", ""),
                "text": source.get("text", source.get("description", ""))
            })

        return output

    except Exception as e:
        eprint(f"❌ Critical error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)