import chromadb
from transformers import AutoTokenizer, AutoModel
import uuid  # Import the uuid module
from enum import Enum

class ModelNames(Enum):
    QWEN_RE_RANKER_0_6B = "Qwen/Qwen3-Reranker-0.6B"
    INSTRUCTOR_XL = "hkunlp/instructor-xl"
    SENTENCE_TRANSFORMERS_ALL_MINILM_L6_V2 = "sentence-transformers/all-MiniLM-L6-v2"  # This is the model name in your example

class BaseDB:
    def __init__(self, collection_name="my_records", model: ModelNames = ModelNames.SENTENCE_TRANSFORMERS_ALL_MINILM_L6_V2, path="db"):
        self.client = chromadb.PersistentClient(path=path)  # Removed session_name
        self.collection = self.client.get_or_create_collection(collection_name)
        self.tokenizer = AutoTokenizer.from_pretrained(model.value)
        self.model = AutoModel.from_pretrained(model.value)

    def generate_embedding(self, text):
        inputs = self.tokenizer(text, padding=True, truncation=True, return_tensors="pt")
        outputs = self.model(**inputs)
        # Generate the embedding by averaging the hidden states
        return outputs.last_hidden_state.mean(dim=1).detach().numpy().tolist()[0]

    def add_record(self, title, content, metadata=None):
        record_id = str(uuid.uuid4())  # Generate a UUID for note ID
        combined_text = f"{title} {content}"

        if metadata:
            for key in metadata:
                if isinstance(metadata[key], list):
                    metadata[key] = ','.join(map(str, metadata[key]))

        embedding = self.generate_embedding(combined_text)
        if metadata is None:
            metadata = {}
        self.collection.add(
            documents=[combined_text],
            embeddings=[embedding],
            ids=[record_id],
            metadatas=[metadata]  # Add the metadata here
        )
        return record_id

    def search_records(self, query, n_results=5):
        embedding = self.generate_embedding(query)
        results = self.collection.query(
            query_embeddings=[embedding],
            n_results=n_results
        )
        return results

    def get_record(self, record_id):
        try:
            result = self.collection.get(ids=[record_id])
            return result
        except ValueError as e:
            print(f"Error retrieving record with ID {record_id}: {e}")
            return None

    def parse_search_results(self, results):
        if not results or not results['ids']:
            return []

        parsed_results = []
        for i, note_id in enumerate(results['ids'][0]):
            document = results['documents'][0][i]
            metadata = results.get('metadatas', [{}])[0][i]  # Retrieve the metadata
            distance = results['distances'][0][i]

            parsed_results.append({
                'id': note_id,
                'document': document,
                'distance': distance,
                'metadata': metadata
            })
        return parsed_results

    def get_all_records(self):
        all_documents = self.collection.get()
        return all_documents  # Returns a dictionary with 'ids', 'embeddings', 'documents', etc.

# Example usage (for testing)
if __name__ == '__main__':
    db_qwen_model = BaseDB(model=ModelNames.QWEN_RE_RANKER_0_6B)

    record1_id = db_qwen_model.add_record("My First Record", "This is the content of my first record.", {"tags": ["important"], "author": "Fabio"})
    print(f"Added record with ID: {record1_id}")

    record2_id = db_qwen_model.add_record("Another Record", "This is another record with some different content.", {"category": "miscellaneous", "date": "2023-10-05"})
    print(f"Added record with ID: {record2_id}")

    all_records = db_qwen_model.get_all_records()

    print("\n--- All Records ---")
    if 'ids' in all_records:
        for i in range(len(all_records['ids'])):
            record_id = all_records['ids'][i]
            document = all_records['documents'][i]
            metadata = all_records['metadatas'][i]  # Retrieve the metadata
            print(f"ID: {record_id}")
            print(f"Record: {document}")
            print(f"Metadata: {metadata}")
            print("-" * 20)
    else:
        print("No records found.")

    search_query = "first record"
    results_array = db_qwen_model.parse_search_results(db_qwen_model.search_records(search_query))

    print("\n--- Search Results ---")
    for result in results_array:
        print(f"ID: {result['id']}")
        print(f"Document: {result['document']}")
        print(f"Distance: {result['distance']}")
        print(f"Metadata: {result['metadata']}")
        print("-" * 20)