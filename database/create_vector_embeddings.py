import os
import openai
from sentence_transformers import SentenceTransformer


def embed_text(text, model_name, base_url, api_key):
    """Generates vector embeddings for the given text."""
    if model_name == "text-embedding-3-small":
        openai_client = openai.Client(base_url=base_url, api_key=api_key)
        embeddings = (
            openai_client.embeddings.create(input=[text], model=model_name)
            .data[0]
            .embedding
        )
        return embeddings
    else:
        model = SentenceTransformer(model_name, trust_remote_code=True)
        embedding = model.encode(text)
        return embedding.tolist()


def embed_dataframe(df, text_column, model_name, base_url, api_key):
    """Generates vector embeddings for the given DataFrame."""
    df["text_embedding"] = df[text_column].apply(
        lambda x: embed_text(x, model_name, base_url, api_key)
    )
    return df
