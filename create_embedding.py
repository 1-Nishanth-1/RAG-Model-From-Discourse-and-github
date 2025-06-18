import os
import glob
import json
import numpy as np
from sklearn.preprocessing import normalize
from sentence_transformers import SentenceTransformer
import torch
# Initialize local embedding model
device = "cuda" if torch.cuda.is_available() else "cpu"
model = SentenceTransformer("BAAI/bge-base-en-v1.5")
if device == "cuda":
    model = model.to("cuda")




CHUNK_SIZE = 1000
OVERLAP = 200

def chunk_with_overlap(text, chunk_size=CHUNK_SIZE, overlap=OVERLAP):
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end])
        if end == len(text):
            break
        start = end - overlap
    return chunks

def get_embedding(text):
    try:
        embedding = model.encode(text, normalize_embeddings=True)
        return embedding
    except Exception as e:
        print("Embedding error:", e)
        return None

# Load markdowns, embed, and store
vectors = []
metadata = []

def process_directory(directory):
    for filepath in glob.glob(os.path.join(directory, "*.md")):
        with open(filepath, 'r', encoding='utf-8') as f:
            text = f.read()

        chunks = chunk_with_overlap(text)
        for i, chunk in enumerate(chunks):
            emb = get_embedding(chunk)
            filename = os.path.basename(filepath)

            if directory == "markdowns2":
                file_id = filename.split("-")[0]
                topic_slug = filename.split("-", 1)[1].replace(".md", "")
                # Replace multiple consecutive hyphens with a single hyphen
                topic_slug = "-".join(filter(None, topic_slug.split("-")))
                print(topic_slug, file_id)
                url = f"https://discourse.onlinedegree.iitm.ac.in/t/{topic_slug}/{file_id}"
            else:
                name_no_ext = os.path.splitext(filename)[0]
                url = f"https://tds.s-anand.net/#/{name_no_ext}"

            if emb is not None:
                vectors.append(emb)
                metadata.append({
                    "source": os.path.basename(filepath),
                    "filepath": filepath,
                    "chunk_id": i,
                    "text_preview": chunk[:100],
                    "text": chunk,

                    "url": url
                })

process_directory("markdowns2")
process_directory("tools-in-data-science-public")

# Save embeddings and metadata
np.savez_compressed("embeddings2.npz", vectors=np.array(vectors))
with open("metadata2.json", "w", encoding='utf-8') as f:
    json.dump(metadata, f, indent=2)

print("✅ Saved to `embeddings2.npz` and `metadata.json`.")

