import re
from typing import List, Dict
from dataclasses import dataclass
from sentence_transformers import SentenceTransformer
from sentence_transformers import models
import torch
import nltk
from nltk.tokenize import word_tokenize
import warnings
warnings.filterwarnings('ignore')

# Check and download required NLTK data
def ensure_nltk_data():
    """Download NLTK tokenizer data with fallback for different versions"""
    try:
        nltk.data.find('tokenizers/punkt_tab')
        return True
    except LookupError:
        try:
            # Try downloading punkt_tab for newer NLTK versions
            nltk.download('punkt_tab')
            return True
        except:
            # Fallback to older punkt tokenizer
            try:
                nltk.data.find('tokenizers/punkt')
                return True
            except LookupError:
                nltk.download('punkt')
                return True
            
# Data structures for chunking
@dataclass
class TextChunk:
    """Data class to represent a text chunk with metadata"""
    text: str
    word_count: int
    metadata: Dict = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.word_count == 0:
            self.word_count = len(self.text.split())

def clean_text(text: str) -> str:
        """Clean and preprocess text"""
        # Replace all newlines with spaces first
        text = text.replace('\n', ' ')
        # Remove extra whitespace and newlines '\n'
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

class TextChunker:
    """
    Chunker that chunks by section or by fixed size with overlap
    """
    
    def __init__(self, chunk_size: int = 256, overlap: int = 8):
        """
        Initialize the TextChunker
        
        Args:
            chunk_size: Maximum size of each chunk (in tokens)
            overlap: Number of tokens to overlap between chunks
        """
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.chunks: List[TextChunk] = []
    
    def chunk_by_fixed_size(self, text: str) -> List[TextChunk]:
        """
        Chunk text by fixed token size with overlap
        
        Args:
            text: Input text to chunk
            
        Returns:
            List of TextChunk objects
        """
        chunks = []
        cleaned_text = clean_text(text)
        tokens = word_tokenize(cleaned_text)
        
        start = 0
        
        while start < len(tokens):
            # Calculate end position
            end = min(start + self.chunk_size, len(tokens))
            # Extract chunk tokens
            chunk_tokens = tokens[start:end]
            # Convert tokens back to text
            chunk_text = ' '.join(chunk_tokens)
            # Create chunk object
            chunk = TextChunk(
                text=chunk_text,
                word_count=len(chunk_tokens),
            )
            chunks.append(chunk)
            # Move start position with overlap
            start = end - self.overlap
            # Break if we've reached the end
            if end >= len(tokens):
                break
        
        return chunks

def process_all_medical_records(medical_data: dict, max_tokens: int = 256, overlap: int = 8) -> List[TextChunk]:
    """
    Process medical records from a dictionary structure and create text chunks.

    Args:
        medical_data (dict): Dictionary containing medical records data
        max_tokens (int): Maximum tokens per chunk
        overlap (int): Number of overlapping tokens between chunks

    Returns:
        List[TextChunk]: List of processed text chunks with metadata
    """
    all_chunks = []
    chunker = TextChunker(chunk_size=max_tokens, overlap=overlap)

    # print("Processing medical records with metadata...")

    # Process each date section
    for date, records in medical_data.items():
        print(f"Processing date: {date}")

        # Process each record within the date
        for record_idx, record in enumerate(records):
            if not isinstance(record, dict):
                continue

            record_type = record.get('record_type', '')

            text_content = {}

            if record_type == 'Lab Results':
              doctor = ''
              section_type = 'Lab Results'
              subsections = []
              allergies = ''
              tests = record.get('tests', [])
              for test in tests:
                  test_results = test.get('lab results', {})
                  for key, value in test_results.items():
                      text_content[key] = value

            else: # record_type == 'Medical Records'
            # Extract metadata
              doctor = record.get('doctor', '')
              section_type = record.get('section_type', '')
              subsections = record.get('subsections', [])
              allergies = record.get('allergies') or ''
              text_content = record.get('text', {})

            if isinstance(text_content, dict):
                for category, category_text in text_content.items():
                    if not category_text or not category_text.strip():
                        continue

                    # Clean the text
                    cleaned_text = clean_text(category_text)

                    # Calculate token count
                    tokens = word_tokenize(cleaned_text)
                    tokens_len = len(tokens)

                    # Create base metadata for this text chunk
                    base_metadata = {
                        "date": date,
                        "doctor": doctor,
                        "section_type": section_type,
                        "text_category": category,
                        "subsections": subsections,
                        "allergies": allergies,
                        "record_index": record_idx
                    }

                    if tokens_len <= max_tokens:
                        # Single chunk for this category
                        chunk = TextChunk(
                            text=cleaned_text,
                            word_count=tokens_len,
                            metadata={**base_metadata, "chunk": 1, "total_chunks": 1}
                        )
                        all_chunks.append(chunk)
                        # print(f"  {category}: Single chunk ({tokens_len} tokens)")
                    else:
                        # Multiple chunks needed for this category
                        category_chunks = chunker.chunk_by_fixed_size(cleaned_text)

                        # Update metadata for each chunk
                        for chunk_idx, chunk in enumerate(category_chunks, 1):
                            chunk.metadata = {
                                **base_metadata,
                                "chunk": chunk_idx,
                                "total_chunks": len(category_chunks)
                            }

                        all_chunks.extend(category_chunks)
                        # print(f"  {category}: {len(category_chunks)} chunks ({tokens_len} tokens total)")

    print(f"Completed. Total chunks: {len(all_chunks)}")
    return all_chunks

def prepare_chunks_for_embedding(chunks: List[TextChunk]) -> List[Dict]:
    prepared_chunks = []

    for i, chunk in enumerate(chunks):
        # Generate unique ID using index, date, category, and chunk number
        chunk_id = i + 1
        if chunk.metadata and 'date' in chunk.metadata:
            # Include text_category to avoid duplicates from same date/chunk
            category = chunk.metadata.get('text_category', 'unknown')
            chunk_num = chunk.metadata.get('chunk', 1)
            chunk_id = f"{chunk.metadata['date']}_{category}_chunk_{chunk_num}_{i}"
        prepared_chunk = {
            'id': chunk_id,
            'text': chunk.metadata['date'] + ", " + chunk.metadata['text_category'] + ": " + chunk.text,
            'metadata': {
                **chunk.metadata
            }
        }
        prepared_chunks.append(prepared_chunk)

    return prepared_chunks

def build_bioclinical_sentence_model(max_seq_len: int = 384):
    word_emb = models.Transformer("emilyalsentzer/Bio_ClinicalBERT", max_seq_length=max_seq_len)
    pooling = models.Pooling(
        word_emb.get_word_embedding_dimension(),
        pooling_mode_mean_tokens=True,
        pooling_mode_cls_token=False,
        pooling_mode_max_tokens=False,
    )
    return SentenceTransformer(modules=[word_emb, pooling])

def generate_embeddings(prepared_chunks: List[Dict], model_name: str = "emilyalsentzer/Bio_ClinicalBERT") -> List[Dict]:
    print(f"Loading model: {model_name}")
    model = build_bioclinical_sentence_model()

    # Check if GPU is available
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model = model.to(device)
    # print(f"Device: {device}")

    # Extract texts for embedding
    texts = [chunk['text'] for chunk in prepared_chunks]

    print(f"Processing {len(texts)} text chunks...")
    # start_time = time.time()

    # Generate embeddings for all texts
    embeddings = model.encode(
        texts,
        convert_to_tensor=True,
        show_progress_bar=False
    )

    # Convert to CPU and numpy for storage
    embeddings = embeddings.cpu().numpy()

    # end_time = time.time()
    # print(f"Embedding generation completed in {end_time - start_time:.1f}s")
    # print(f"Vector dimension: {len(embeddings[0])}")

    # Add embeddings to chunks
    embedded_chunks = []
    for chunk, embedding in zip(prepared_chunks, embeddings):
        embedded_chunk = {
            **chunk,
            'embedding': embedding.tolist(),  # Convert numpy array to list for JSON serialization
            'embedding_model': "emilyalsentzer/Bio_ClinicalBERT",
            'embedding_dimension': len(embedding)
        }
        embedded_chunks.append(embedded_chunk)

    return embedded_chunks

from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType, utility
import uuid

class MilvusVectorStore:

    def __init__(self, collection_name: str = "medical_rag_embeddings", db_file: str = "./milvus_lite.db"):
        self.collection_name = collection_name
        self.db_file = db_file
        self.collection = None

    def connect(self):
        try:
            connections.connect("default", uri=self.db_file)
            print(f"Connected to Milvus Lite at {self.db_file}")
            return True
        except Exception as e:
            print(f"Connection failed: {e}")
            return False

    def create_collection(self, embedding_dim: int = 768):
        # Drop existing collection if it exists
        if utility.has_collection(self.collection_name):
            utility.drop_collection(self.collection_name)
            print(f"Removed existing collection: {self.collection_name}")

        # Define schema
        fields = [
            FieldSchema(name="id", dtype=DataType.VARCHAR, max_length=200, is_primary=True),
            FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=10000),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=embedding_dim),
            FieldSchema(name="date", dtype=DataType.VARCHAR, max_length=50),
            FieldSchema(name="chunk_number", dtype=DataType.INT64),
            FieldSchema(name="word_count", dtype=DataType.INT64),
        ]

        schema = CollectionSchema(fields, f"Medical RAG embeddings collection with {embedding_dim}D vectors")

        # Create collection
        self.collection = Collection(self.collection_name, schema)
        # print(f"Collection created: {self.collection_name}")

        # Create index for vector search
        index_params = {
            "index_type": "FLAT",
            "metric_type": "COSINE",
            "params": {}
        }

        self.collection.create_index("embedding", index_params)
        # print("Vector index ready")

    def insert_embeddings(self, embedded_chunks: List[Dict]):
        """
        Insert embedded chunks into Milvus collection

        Args:
            embedded_chunks: List of chunks with embeddings
        """
        if not self.collection:
            print("Collection not initialized. Call create_collection() first.")
            return

        # Prepare data for insertion
        ids = []
        texts = []
        embeddings = []
        dates = []
        chunk_numbers = []
        word_counts = []
        i = 0
        for chunk in embedded_chunks:
            # Generate unique ID if not present
            chunk_id = chunk.get('id', str(uuid.uuid4()))

            ids.append(str(chunk_id))
            texts.append(chunk['text'][:9999])  # Truncate if too long
            embeddings.append(chunk['embedding'])
            dates.append(chunk['metadata'].get('date', 'unknown'))
            chunk_numbers.append(chunk['metadata'].get('chunk', 1))
            word_counts.append(chunk['metadata'].get('word_count', 0))

        # Insert data
        data = [ids, texts, embeddings, dates, chunk_numbers, word_counts]

        try:
            insert_result = self.collection.insert(data)
            self.collection.flush()
            print(f"Data inserted ({len(embedded_chunks)} chunks)")
            # print(f"Sample IDs: {insert_result.primary_keys[:3]}..." if len(insert_result.primary_keys) > 3 else f"IDs: {insert_result.primary_keys}")

            self.load_collection()
            # print(f"Loaded into memory for search")
            return insert_result
        except Exception as e:
            print(f"Insert failed: {e}")
            return None

    def load_collection(self):
        if self.collection:
            self.collection.load()
            # print("Collection loaded into memory")

    def search_similar(self, query_embedding: List[float], top_k: int = 8, date_filter: str = None):
        if not self.collection:
            print("Collection not initialized")
            return []

        search_params = {"metric_type": "COSINE", "params": {}}

        # Optional date filtering
        expr = None
        if date_filter:
            expr = f'date == "{date_filter}"'
        results = self.collection.search(
            [query_embedding],
            "embedding",
            search_params,
            limit=top_k,
            expr=expr,
            output_fields=["text", "date", "chunk_number", "word_count"]
        )
        return results

    def get_collection_stats(self):
        if self.collection:
            self.collection.flush()
            stats = self.collection.num_entities
            print(f"Collection '{self.collection_name}' contains {stats} vectors")
            return stats
        return 0
    
class MedicalRAGRetriever:

    def __init__(self, vector_store, embedding_model_name: str = "emilyalsentzer/Bio_ClinicalBERT"):

        self.vector_store = vector_store
        self.embedding_model = build_bioclinical_sentence_model()

        # Move to GPU if available
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.embedding_model = self.embedding_model.to(device)

        print(f"RAG Retriever initialized ({embedding_model_name})")
        # print(f"Device: {device}")

    def generate_query_embedding(self, query: str) -> List[float]:
        embedding = self.embedding_model.encode(query, convert_to_tensor=True)
        return embedding.cpu().numpy().tolist()

    def retrieve_for_queries(self, queries: List[str], top_k: int) -> Dict:
        all_chunks = []

        for i, query in enumerate(queries):
            print(f"Processing query {i+1}/{len(queries)}: {query[:50]}...")

            # Generate embedding for the query
            query_embedding = self.generate_query_embedding(query)

            # Simple search for top 2 results
            results = self.vector_store.search_similar(query_embedding, top_k=top_k)
            chunks = self._process_search_results(results)

            if chunks:
                all_chunks.extend(chunks)

        # Remove duplicates based on chunk_id
        seen_ids = set()
        unique_chunks = []
        for chunk in all_chunks:
            if chunk['chunk_id'] not in seen_ids:
                unique_chunks.append(chunk)
                seen_ids.add(chunk['chunk_id'])

        # Aggregate text from all unique chunks
        aggregated_text = "\n\n".join([chunk['text'] for chunk in unique_chunks])

        return {
            'queries': queries,
            'retrieved_chunks': unique_chunks,
            'aggregated_text': aggregated_text,
            'chunk_count': len(unique_chunks)
        }

    def _process_search_results(self, results) -> List[Dict]:
        chunks = []
        for hits in results:
            for hit in hits:
                chunks.append({
                    'text': hit.entity.get('text', ''),
                    'score': float(hit.score),
                    'date': hit.entity.get('date', 'unknown'),
                    'chunk_number': hit.entity.get('chunk_number', 0),
                    'word_count': hit.entity.get('word_count', 0),
                    'chunk_id': hit.id
                })
        return chunks
    
def retrieve_rag(timeline, field_sets, top_k=2, chunk_size=256, overlap=8):
    
    ensure_nltk_data()

    # Process using the timeline variable
    all_processed_chunks = process_all_medical_records(timeline, chunk_size, overlap)

    # Prepare chunks for the next stage of RAG pipeline (embedding generation)
    prepared_for_embedding = prepare_chunks_for_embedding(all_processed_chunks)

    # Generate embeddings for all prepared chunks
    embedded_chunks = generate_embeddings(prepared_for_embedding)

    # Show sample embedded chunk structure (without the full embedding vector)
    sample_chunk = embedded_chunks[0].copy()
    sample_chunk['embedding'] = f"[{len(sample_chunk['embedding'])}-dim vector]"

    # Initialize and setup Milvus Lite vector database
    vector_store = MilvusVectorStore()

    # Connect to Milvus Lite
    if vector_store.connect():
        # Create collection with appropriate embedding dimension
        embedding_dim = embedded_chunks[0]['embedding_dimension'] if embedded_chunks else 768
        vector_store.create_collection(embedding_dim)

        # Insert all embeddings
        insert_result = vector_store.insert_embeddings(embedded_chunks)

        if insert_result:
            # Load collection for search
            vector_store.load_collection()

            # Get statistics
            vector_store.get_collection_stats()
        else:
            print("Failed to insert embeddings")
    else:
        print("Could not connect to Milvus")

    # Initialize the retriever
    if 'vector_store' in locals() and hasattr(vector_store, 'collection') and vector_store.collection:
        retriever = MedicalRAGRetriever(vector_store)

        # Store retrieval results for all field sets
        all_retrieval_results = {}

        # Process each field set
        for field_num, field_queries in field_sets.items():
            retrieval_result = retriever.retrieve_for_queries(field_queries, top_k)
            all_retrieval_results[field_num] = retrieval_result

        return all_retrieval_results

    else:
        print("Vector store not available. Run the database setup cell first.")