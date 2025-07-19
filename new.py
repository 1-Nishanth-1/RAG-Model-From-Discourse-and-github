import faiss
import numpy as np

data = np.load("embeddings2.npz")
vectors = data["vectors"]#djust key if needed

# Ensure float32
vectors = vectors.astype('float32')

# Create index
dimension = vectors.shape[1]
index = faiss.IndexFlatL2(dimension)  
index.add(vectors)
faiss.write_index(index, "embeddings.faiss")
