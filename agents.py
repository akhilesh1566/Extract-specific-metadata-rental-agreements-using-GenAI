
import os
import time
import re # Import regex for parsing
import json # For potential structured output parsing
import io 

# --- LangChain Core Imports ---
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
# Consider PydanticOutputParser for more robust structured output later
# from langchain_core.pydantic_v1 import BaseModel, Field # If using PydanticOutputParser

# --- LangChain Community/Integrations ---
from langchain_community.vectorstores import FAISS
from langchain.chains import RetrievalQA # Can use this simple chain
# Or build custom with LCEL:
# from langchain_core.runnables import RunnablePassthrough

# --- LangChain Google GenAI ---
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings

# --- LangChain Text Splitters ---
from langchain.text_splitter import RecursiveCharacterTextSplitter

# --- Local Utils ---
# import pdf_utils # Not needed directly if text is passed in

# --- Environment Loading ---
from dotenv import load_dotenv
load_dotenv()

class RentalAgreementAgent:
    def __init__(self, api_key):
        if not api_key:
            raise ValueError("API key cannot be empty.")
        self.api_key = api_key
        self.llm = None
        self.embeddings = None
        self.vector_store = None
        self.retriever = None
        self.extracted_text = None # Agent can optionally store the text it processed

        try:
            self.llm = ChatGoogleGenerativeAI(
                model="gemini-1.5-flash-latest", # Using Flash for potentially better rate limits
                google_api_key=self.api_key,
                temperature=0.1, # Lower temp for more deterministic extraction
                convert_system_message_to_human=True
            )
            print("LLM (Gemini Flash) initialized.")

            self.embeddings = GoogleGenerativeAIEmbeddings(
                model="models/embedding-001",
                google_api_key=self.api_key
            )
            print("Embedding model initialized.")
        except Exception as e:
            print(f"Error during agent component initialization: {e}")
            raise ConnectionError(f"Failed to initialize Google AI components: {e}")

        print("RentalAgreementAgent initialized successfully.")
    
    


    def _create_vector_store(self, text):
        """Chunks text, creates embeddings, builds FAISS index. Returns FAISS store."""
        # --- (Keep implementation from Phase 3) ---
        if not text: print("Error: No text provided."); return None
        if not self.embeddings: print("Error: Embeddings not initialized."); return None
        print("Starting vector store creation...")
        try:
            text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
            chunks = text_splitter.split_text(text)
            if not chunks: print("Warning: No chunks created."); return None
            print(f"Split text into {len(chunks)} chunks.")
            print("Creating FAISS index...")
            vector_store = FAISS.from_texts(chunks, self.embeddings)
            print("FAISS index created successfully.")
            return vector_store
        except Exception as e:
            print(f"Error creating vector store ({type(e).__name__}): {e}")
            return None


    def load_and_index_document(self, extracted_text):
        """Loads text, creates index, sets up retriever. Returns bool."""
         # --- (Keep implementation from Phase 3) ---
        print("Agent received request to load and index document...")
        if not extracted_text: print("Error: No text provided."); return False
        self.extracted_text = extracted_text
        self.vector_store = self._create_vector_store(self.extracted_text)
        if self.vector_store:
            self.retriever = self.vector_store.as_retriever(search_kwargs={"k": 5}) # Get top 5 chunks
            print("Retriever is ready.")
            return True
        else:
            print("Indexing failed."); self.retriever = None; return False


    # --- IMPLEMENTED IN PHASE 4 ---
    def extract_metadata(self):
        """Extracts all target metadata fields using RAG."""
        print("Starting metadata extraction...")
        if not self.retriever:
            print("Error: Document not indexed (Retriever not ready). Cannot extract metadata.")
            return None # Indicate failure

        metadata = {}
        # Define the fields, queries, and specific extraction instructions
        target_fields = [
            {"name": "Agreement Value",
             "query": "What is the primary monetary value of the agreement, such as monthly rent, total rent, or security deposit amount?",
             "format": "Extract ONLY the monetary value mentioned (e.g., '1500/month', 'Rupees 18,000', 'Rs.2000', '50000 rupees'). If multiple values exist (like rent and deposit), prioritize rent. If no value is found, return 'Not Found'."},
            {"name": "Agreement Start Date",
             "query": "What is the commencement date, start date, or effective date of this agreement?",
             "format": "Extract ONLY the date. Return the date in YYYY-MM-DD format if possible, otherwise return the date as written. If no date is found, return 'Not Found'."},
            {"name": "Agreement End Date",
             "query": "What is the termination date, end date, or expiration date of this agreement term?",
             "format": "Extract ONLY the date. Return the date in YYYY-MM-DD format if possible, otherwise return the date as written. If no date is found, return 'Not Found'."},
            {"name": "Renewal Notice (Days)",
             "query": "How many days notice is required before the end date for renewal or non-renewal termination? Look for phrases like 'notice period', 'days prior', 'written notice'.",
             "format": "Extract ONLY the number of days (e.g., 30, 60, 90). Ignore other details. If no specific number of days is mentioned, return 'Not Found'."},
            {"name": "Party One",
             "query": "Identify the full name of the Tenant(s), Lessee(s), Resident(s), or the primary party agreeing to rent (often listed first or defined as such).",
             "format": "Extract ONLY the full name(s) of the tenant/lessee/first party. If multiple tenants, list them separated by 'and' or commas as written. If not clearly identified, return 'Not Found'."},
            {"name": "Party Two",
             "query": "Identify the full name of the Landlord, Lessor, Owner, Property Manager, or the second party providing the rental property.",
             "format": "Extract ONLY the full name(s) or company name of the landlord/lessor/second party. If not clearly identified, return 'Not Found'."}
        ]

        # --- Setup RAG Chain (Can be defined once if reusable) ---
        # Using a simple RetrievalQA chain for this example
        # Note: For more complex parsing or control, LCEL is recommended
        try:
            qa_chain = RetrievalQA.from_chain_type(
                llm=self.llm,
                chain_type="stuff", # "stuff" puts all retrieved docs into the context
                retriever=self.retriever,
                return_source_documents=False, # We only need the answer
                chain_type_kwargs={
                    "prompt": PromptTemplate(
                        template="""Use the following pieces of context to answer the question at the end.
If you don't find the answer in the context, respond with 'Not Found'. Do not make up information.
Follow the specific formatting instructions precisely.

Context:
{context}

Question: {question}

Answer:""",
                        input_variables=["context", "question"],
                    )
                }
            )
            print("RAG QA chain created.")
        except Exception as e:
            print(f"Error creating RAG chain: {e}")
            return None


        # --- Loop through fields and extract ---
        total_fields = len(target_fields)
        for i, field_info in enumerate(target_fields):
            field_name = field_info["name"]
            query_with_format = f"{field_info['query']} Instruction: {field_info['format']}"
            print(f"({i+1}/{total_fields}) Extracting field: {field_name}...")

            try:
                # Add a small delay BEFORE each call to respect potential rate limits
                # Adjust sleep time based on observed limits (start with 1-2 sec for Flash)
                time.sleep(2)

                # Invoke the RAG chain
                response_dict = qa_chain.invoke({"query": query_with_format})
                raw_answer = response_dict.get("result", "Error: No result key")

                # --- Basic Parsing/Cleaning ---
                # Remove potential markdown, leading/trailing spaces, handle "Not Found"
                cleaned_answer = raw_answer.strip().strip('`').strip()
                if "not found" in cleaned_answer.lower() or not cleaned_answer:
                    metadata[field_name] = "Not Found"
                else:
                     # Add more specific cleaning per field if needed (e.g., date formatting)
                     metadata[field_name] = cleaned_answer

                print(f"  Raw answer: '{raw_answer}' -> Cleaned: '{metadata[field_name]}'")

            except Exception as e:
                print(f"  Error extracting field '{field_name}' ({type(e).__name__}): {e}")
                # Check specifically for API/Quota errors
                if "quota" in str(e).lower() or "429" in str(e):
                     print("RATE LIMIT HIT! Consider increasing sleep time or checking your plan.")
                     # You might want to stop the whole process here or just mark field as error
                     metadata[field_name] = "Rate Limit Error"
                     # Optionally break the loop if rate limited
                     # break
                else:
                    metadata[field_name] = "Extraction Error"


        print(f"Finished metadata extraction. Result: {metadata}")
        return metadata


    # --- Helper for parsing (can be expanded) ---
    # def _parse_llm_output(self, result, field_name):
    #     # Add more sophisticated parsing here based on field_name
    #     cleaned = result.strip().strip('`').strip()
    #     if "not found" in cleaned.lower() or not cleaned:
    #         return "Not Found"
    #     # Add date parsing, number extraction etc. here
    #     return cleaned


    # --- Cleanup Method ---
    def cleanup(self):
        """Perform cleanup if necessary."""
        # --- (Keep implementation from Phase 3) ---
        print("Agent cleanup called.")
        self.vector_store = None
        self.retriever = None
        self.extracted_text = None