# from sentence_transformers import SentenceTransformer

# # Load the model
# model = SentenceTransformer("all-MiniLM-L6-v2")

# # Three hardcoded lines
# texts = [
#     "How do I reset my password?",
#     "Where can I change my login password?",
#     "The weather is very pleasant today."
# ]

# # Generate embeddings
# embeddings = model.encode(texts)

# # Print results
# for i, embedding in enumerate(embeddings):
#     print(f"\nText {i + 1}: {texts[i]}")
#     print(f"Embedding size: {len(embedding)}")
#     print("Embedding:")
#     print(embedding)



from sentence_transformers import SentenceTransformer, util

# Load model
model = SentenceTransformer("all-MiniLM-L6-v2")

# Your stored texts
texts = [
    # "How do I reset my current password?",
    # "Where can I apply for leave?",
    "How do I change my password?",
    "How do I connect to the company VPN?"
]

# Create embeddings for your stored texts
embeddings = model.encode(
    texts,
    convert_to_tensor=True
)

# -----------------------------
# User's search query
# -----------------------------

query = "I forgot my login password, how can I change it?"

# Convert query into an embedding
query_embedding = model.encode(
    query,
    convert_to_tensor=True
)

# Compare query against all stored text embeddings
similarities = util.cos_sim(
    query_embedding,
    embeddings
)[0]

# Find the most similar text
best_index = similarities.argmax().item()

print("\nQuery:")
print(query)

print("\nBest Match:")
print(texts[best_index])

print("\nSimilarity Score:")
print(similarities[best_index].item())