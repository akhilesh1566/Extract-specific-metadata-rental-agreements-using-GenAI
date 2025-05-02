# app.py
import streamlit as st
import os
from dotenv import load_dotenv
import ui
import pdf_utils
from agents import RentalAgreementAgent
import time

print("-" * 20)
print(f"Imported pdf_utils: {pdf_utils}")
print(f"Path to imported pdf_utils: {pdf_utils.__file__}")
print("Attributes available in pdf_utils:")
print(dir(pdf_utils)) # List everything defined in the imported module
print("-" * 20)
load_dotenv()

google_api_key = os.getenv("GOOGLE_API_KEY")

st.set_page_config(
    page_title="Rental Agreement Extractor",
    page_icon="📄",
    layout="wide"
)

# --- Initialize Session State (Simplified for Single File) ---
if 'uploaded_filename' not in st.session_state: st.session_state.uploaded_filename = None
if 'extracted_text' not in st.session_state: st.session_state.extracted_text = None
if 'agent' not in st.session_state: st.session_state.agent = None
if 'rag_index_ready' not in st.session_state: st.session_state.rag_index_ready = False
if 'extracted_metadata' not in st.session_state: st.session_state.extracted_metadata = None
if 'processing_error' not in st.session_state: st.session_state.processing_error = None
if 'is_processing' not in st.session_state: st.session_state.is_processing = False # General processing flag


# --- Initialize Agent ---
def initialize_agent():
    if st.session_state.agent is None:
        if not google_api_key:
            st.error("⚠️ Google API Key not found.")
            st.stop()
        try:
            st.session_state.agent = RentalAgreementAgent(api_key=google_api_key)
        except Exception as e:
            st.error(f"🚨 Failed to initialize AI Agent: {e}")
            st.session_state.agent = None
            st.stop()

# --- Main Application Logic ---
def main():
    initialize_agent()
    if st.session_state.agent is None: return

    ui.display_header()

    # --- Step 1: Upload Area (Allow PDF, DOCX, TXT, Images) ---
    IMAGE_TYPES = ["png", "jpg", "jpeg", "bmp", "tif", "tiff"]
    DOC_TYPES = ["pdf", "docx", "txt"]
    ACCEPTED_TYPES = DOC_TYPES + IMAGE_TYPES

    uploaded_file = st.file_uploader(
        f"Choose Agreement File ({', '.join(ACCEPTED_TYPES).upper()})", # Update label
        type=ACCEPTED_TYPES, # Use the combined list
        accept_multiple_files=False # Keep as single file
    )

    # --- Step 2: Process Upload & Extract Text ---
    if uploaded_file:
        # If it's a new file upload
        if uploaded_file.name != st.session_state.get('uploaded_filename', None):
            print(f"New file uploaded: {uploaded_file.name}")
            # Reset all states for the new file
            st.session_state.uploaded_filename = uploaded_file.name
            st.session_state.extracted_text = None
            st.session_state.rag_index_ready = False
            st.session_state.extracted_metadata = None
            st.session_state.processing_error = None
            st.session_state.is_processing = True # Start processing immediately
            st.rerun() # Rerun to show spinner and start extraction
            

        # --- Text Extraction (Triggered after rerun if is_processing and text is None) ---
        if st.session_state.get('is_processing', False) and st.session_state.extracted_text is None:
            with st.spinner(f"Extracting text from '{st.session_state.uploaded_filename}'..."):
                text_result = None
                error_msg = None
                try:
                    # --- This is the call ---
                    extracted_text_result = pdf_utils.extract_text_from_file(uploaded_file)
                    # --- End of call ---

                    if not extracted_text_result:
                        error_msg = f"Could not extract text from '{st.session_state.uploaded_filename}'."
                    else:
                         text_result = extracted_text_result # Assign if successful

                except Exception as e: # <--- THIS BLOCK IS LIKELY RUNNING
                    # Constructing the error message using the exception 'e'
                    error_msg = f"Error during text extraction: {str(e)}"
                    print(f"Unexpected error calling extraction: {e}") # Log original error

                # --- Update session state based on outcome ---
                st.session_state.extracted_text = text_result # Will be None if error occurred
                st.session_state.processing_error = error_msg # Stores the message you are seeing
                st.session_state.is_processing = False # Done with this step
                st.rerun() # Rerun to show preview/button or errorr

    # --- Display Current State and Buttons ---
    current_error = st.session_state.get('processing_error', None)
    current_text = st.session_state.get('extracted_text', None)
    is_indexed = st.session_state.get('rag_index_ready', False)
    is_processing_now = st.session_state.get('is_processing', False) # General processing flag

    if current_error:
        ui.display_processing_message("error", current_error)

    if current_text:
        # No Text Preview as requested
        # ui.display_text_preview(current_text) # REMOVED
        if not current_error:
             ui.display_processing_message("success", "Text extraction complete.")

        # --- Step 3: Indexing ---
        if not is_indexed:
            if ui.display_process_button(disabled=is_processing_now):
                st.session_state.is_processing = True
                st.session_state.processing_error = None # Clear previous error
                st.rerun()

        # --- Indexing Action ---
        if st.session_state.get('is_processing', False) and not is_indexed:
             with st.spinner("Processing document: Chunking, Embedding, Indexing..."):
                 agent = st.session_state.agent
                 success = False
                 error_msg = None
                 if agent and current_text:
                     try:
                         success = agent.load_and_index_document(current_text)
                     except Exception as e:
                         error_msg = f"Error during document processing: {str(e)}"
                         print(f"Error calling load_and_index_document: {e}")

                     if success:
                         st.session_state.rag_index_ready = True
                         print("Indexing successful, RAG is ready.")
                     else:
                         st.session_state.processing_error = error_msg or "Failed to process and index the document."
                         st.session_state.rag_index_ready = False
                 else:
                     st.session_state.processing_error = "Agent or text not available for processing."

             st.session_state.is_processing = False
             st.rerun()

        # --- Step 4/5: Metadata Extraction ---
        if is_indexed:
            if ui.display_extract_button(disabled=is_processing_now):
                 st.session_state.is_processing = True
                 st.session_state.processing_error = None # Clear previous error
                 st.session_state.extracted_metadata = None # Clear old results
                 st.rerun()

        # --- Metadata Extraction Action ---
        if st.session_state.get('is_processing', False) and is_indexed:
            # Check if extraction needs to run (metadata is None)
            if st.session_state.extracted_metadata is None:
                with st.spinner("AI is analyzing the document..."):
                    agent = st.session_state.agent
                    metadata_result = None
                    error_msg = None
                    if agent:
                        try:
                            metadata_result = agent.extract_metadata()
                        except Exception as e:
                            error_msg = f"Error during metadata extraction: {str(e)}"
                            print(f"Error calling extract_metadata: {e}")

                    st.session_state.extracted_metadata = metadata_result
                    if not metadata_result and not error_msg:
                        error_msg = "Metadata extraction failed or returned no results."
                    st.session_state.processing_error = error_msg

                st.session_state.is_processing = False
                st.rerun()

    # --- Display Final Metadata Table ---
    current_metadata = st.session_state.get('extracted_metadata', None)
    if current_metadata:
         # Display table even if there were non-critical extraction errors handled within the dict
         ui.display_metadata_table(current_metadata, st.session_state.get('uploaded_filename', ''))
         # Display specific extraction error if one was set
         if st.session_state.get('processing_error') and "extraction" in st.session_state.processing_error.lower():
             ui.display_processing_message("warning", st.session_state.processing_error)

    # --- Initial Prompt ---
    elif not uploaded_file:
        st.info("Upload a PDF or DOCX agreement to start.")


# --- Run the main function ---
if __name__ == "__main__":
    main()