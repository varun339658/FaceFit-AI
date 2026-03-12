from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import CharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import SentenceTransformerEmbeddings
from langchain_openai import ChatOpenAI
from langchain_classic.chains import RetrievalQA
import json
import re
import os
from openai import OpenAI

# Load skincare knowledge
loader = TextLoader("rag_data/skincare_knowledge.txt")
documents = loader.load()

# Split documents
splitter = CharacterTextSplitter(chunk_size=300, chunk_overlap=50)
docs = splitter.split_documents(documents)

# Create embeddings
embedding = SentenceTransformerEmbeddings(
    model_name="all-MiniLM-L6-v2"
)

# Vector DB
vectorstore = Chroma.from_documents(docs, embedding)

# Retriever
retriever = vectorstore.as_retriever()

# LLM
llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0,
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
)

# RAG chain
qa_chain = RetrievalQA.from_chain_type(
    llm=llm,
    retriever=retriever
)

def generate_skin_recommendation(skin_tone, skin_conditions):

    routine = {
        "morning": [],
        "night": []
    }

    ingredients = {
        "cleanser": "",
        "serum": "",
        "moisturizer": "",
        "sunscreen": ""
    }

    if "acne" in skin_conditions:

        routine["morning"] = [
            "Salicylic Acid Cleanser",
            "Niacinamide Serum",
            "Oil Free Moisturizer",
            "SPF 50 Sunscreen"
        ]

        routine["night"] = [
            "Gentle Cleanser",
            "Niacinamide Serum",
            "Lightweight Moisturizer"
        ]

        ingredients["cleanser"] = "salicylic acid cleanser"
        ingredients["serum"] = "niacinamide serum"
        ingredients["moisturizer"] = "oil free moisturizer"
        ingredients["sunscreen"] = "spf 50 sunscreen"

    else:

        routine["morning"] = [
            "Gentle Cleanser",
            "Hydrating Serum",
            "Moisturizer",
            "Sunscreen"
        ]

        routine["night"] = [
            "Gentle Cleanser",
            "Hydrating Serum",
            "Night Moisturizer"
        ]

        ingredients["cleanser"] = "gentle face cleanser"
        ingredients["serum"] = "hydrating face serum"
        ingredients["moisturizer"] = "ceramide moisturizer"
        ingredients["sunscreen"] = "spf 50 sunscreen"

    return {
        "routine": routine,
        "ingredients": ingredients
    }