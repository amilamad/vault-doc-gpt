import asyncio
from llama_index.core.agent.workflow import AgentWorkflow

from llama_index.core import VectorStoreIndex, SimpleDirectoryReader
from llama_index.core.node_parser import SentenceSplitter

from extensions.nomic_embedding import NomicEmbedding
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

from llama_index.core.llms.mock import MockLLM
from llama_index.llms.ollama import Ollama

from llama_index.core import VectorStoreIndex
from llama_index.core import StorageContext
from llama_index.vector_stores.chroma import ChromaVectorStore
import chromadb
from huggingface_hub import login

print("RAG starting")

# Load custom embedding. Custom NomicEmbedding because it light weight.
embed_model = NomicEmbedding();
print("Loaded custom embedding model")

# Initialize the Chroma client
chroma_client = chromadb.PersistentClient(path="./chroma_db")

collection_name = "random_facts_collection"
collections = chroma_client.list_collections()

index = None
if  not collection_name in collections:
    print("Collection {} was not found. Creating ... ".format(collection_name))

    documents = SimpleDirectoryReader("./docs").load_data()
    
    # Choose better chunk size for breaking the text. 
    # If too big context text match size will be too big.
    splitter = SentenceSplitter(chunk_size=200) 
    nodes = splitter.get_nodes_from_documents(documents)

    # Create collection
    chroma_collection = chroma_client.create_collection(collection_name)

    # LlamaIndex wrapper for Chroma db
    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    index = VectorStoreIndex(nodes=nodes,
                            embed_model=embed_model,
                            storage_context=storage_context)
else:
    chroma_collection = chroma_client.get_collection(collection_name)

    print("Collection {} is already in the data base".format(collection_name))

    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
    index = VectorStoreIndex.from_vector_store(vector_store=vector_store,
                                               embed_model=embed_model);

# Create the llm instance
#mock_llm_model=MockLLM()
llm_model=Ollama(model="llama3.2", request_timeout=360.0)
print("Loaded LLM model")

query_engine = index.as_query_engine(similarity_top_k=4, llm=llm_model)

async def search_documents(query: str) -> str:
    print("Searching document index for query {}".format(query))
    response = await query_engine.aquery(query)
    return str(response)

async def main():
    response = await search_documents("Who is this")
    print(str(response))

# Run the agent
if __name__ == "__main__":
    asyncio.run(main())