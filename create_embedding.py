import os
import glob
import json
import numpy as np
from sklearn.preprocessing import normalize
from sentence_transformers import SentenceTransformer
import torch
# Initialize local embedding model
device = "cuda" if torch.cuda.is_available() else "cpu"
model = SentenceTransformer("BAAI/bge-base-en-v1.5", device=device)


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
            if emb is not None:
                vectors.append(emb)
                metadata.append({
                    "source": os.path.basename(filepath),
                    "filepath": filepath,
                    "chunk_id": i,
                    "text_preview": chunk[:100],
                    "url": f"file://{os.path.abspath(filepath)}#chunk-{i}"
                })

process_directory("markdowns2")
process_directory("tools-in-data-science-public")

# Save embeddings and metadata
np.savez_compressed("embeddings2.npz", vectors=np.array(vectors))
with open("metadata2.json", "w", encoding='utf-8') as f:
    json.dump(metadata, f, indent=2)

print("✅ Saved to `embeddings2.npz` and `metadata.json`.")

