# app.py

import streamlit as st
import os
from dotenv import load_dotenv

# Import UI functions
import ui
# Import the PDF utility function
import pdf_utils
# --- Import the Agent ---
from agents import RentalAgreementAgent

# --- Load Environment Variables ---
load_dotenv()
google_api_key = os.getenv("GOOGLE_API_KEY")

# --- Page Configuration ---
st.set_page_config(
    page_title="Rental Agreement Extractor",
    page_icon="📄",
    layout="wide"
)

# --- Initialize Session State ---
# Ensure keys exist
if 'uploaded_filename' not in st.session_state:
    st.session_state.uploaded_filename = None
if 'extracted_text' not in st.session_state:
    st.session_state.extracted_text = None
if 'agent' not in st.session_state: # Add agent to session state
    st.session_state.agent = None
if 'rag_index_ready' not in st.session_state:
    st.session_state.rag_index_ready = False
if 'extracted_metadata' not in st.session_state:
    st.session_state.extracted_metadata = None
if 'processing_error' not in st.session_state:
    st.session_state.processing_error = None


# --- Initialize Agent ---
# Try to initialize the agent once when the app loads if API key is available
# This prevents re-initialization on every rerun unless necessary
# Note: Secrets management might require initialization inside main() if key is dynamic
def initialize_agent():
    """Initializes the agent and stores it in session state."""
    if st.session_state.agent is None:
        if not google_api_key:
            st.error("⚠️ Google API Key not found. Please set the GOOGLE_API_KEY environment variable or in .env file.")
            st.stop() # Stop execution if no key
        try:
            st.session_state.agent = RentalAgreementAgent(api_key=google_api_key)
        except Exception as e:
            st.error(f"🚨 Failed to initialize AI Agent: {e}")
            st.session_state.agent = None # Ensure agent is None if init fails
            st.stop()


# --- Main Application Logic ---
def main():
    initialize_agent() # Attempt agent initialization

    # Stop if agent failed to initialize
    if st.session_state.agent is None:
        return # Error messages handled in initialize_agent

    # --- Render Header ---
    ui.display_header()

    # --- Step 1: Upload Area ---
    uploaded_file = ui.display_upload_area()

    # --- Step 2: Process Upload & Extract Text ---
    if uploaded_file:
        if uploaded_file.name != st.session_state.get('uploaded_filename', None):
            print(f"New file uploaded: {uploaded_file.name}")
            st.session_state.uploaded_filename = uploaded_file.name
            # Reset dependent states
            st.session_state.extracted_text = None
            st.session_state.rag_index_ready = False
            st.session_state.extracted_metadata = None
            st.session_state.processing_error = None

            with st.spinner(f"Extracting text from '{uploaded_file.name}'..."):
                try:
                    extracted_text_result = pdf_utils.extract_text_from_pdf(uploaded_file)
                    if extracted_text_result:
                        st.session_state.extracted_text = extracted_text_result
                        print("Text extraction successful.")
                    else:
                        st.session_state.processing_error = f"Could not extract text from '{uploaded_file.name}'."
                        st.session_state.extracted_text = None
                        print(f"Text extraction failed for {uploaded_file.name}")
                except Exception as e:
                    st.session_state.processing_error = f"An unexpected error occurred during text extraction: {str(e)}"
                    st.session_state.extracted_text = None
                    print(f"Unexpected error in app.py calling extraction: {e}")

    # --- Display Status/Preview/Buttons based on Session State ---
    if st.session_state.get('processing_error', None):
        st.error(st.session_state.processing_error)

    elif st.session_state.get('extracted_text', None):
        ui.display_processing_message("Text extraction complete.")
        ui.display_text_preview(st.session_state.extracted_text)

        # --- Step 3: Process & Index Document ---
        if not st.session_state.get('rag_index_ready', False):
            # Show the "Process" button only if text is ready and index isn't
            if ui.display_process_button(): # Use the new UI function
                with st.spinner("Processing document: Chunking, Embedding, Indexing... (This may take a moment)"):
                    agent = st.session_state.agent # Get agent from session state
                    if agent:
                        try:
                            success = agent.load_and_index_document(st.session_state.extracted_text)
                            if success:
                                st.session_state.rag_index_ready = True
                                print("Indexing successful, RAG is ready.")
                                # Use experimental_rerun to immediately reflect the state change
                                st.rerun() # Rerun to hide "Process" button and show "Extract" button section
                            else:
                                st.session_state.processing_error = "Failed to process and index the document."
                                st.session_state.rag_index_ready = False
                                st.error(st.session_state.processing_error) # Show error immediately
                        except Exception as e:
                            st.session_state.processing_error = f"Error during document processing: {str(e)}"
                            st.session_state.rag_index_ready = False
                            st.error(st.session_state.processing_error) # Show error immediately
                            print(f"Error calling load_and_index_document: {e}")
                    else:
                         st.error("Agent not initialized. Cannot process document.")

        # --- Step 4 & 5: Extract Metadata & Display ---
        # Show extraction button only if RAG index is ready
        if st.session_state.get('rag_index_ready', False):
            # Display the "Extract Metadata" button
            if ui.display_extract_button():
                agent = st.session_state.agent
                if agent:
                    ui.display_processing_message("Extracting metadata...")
                    with st.spinner("AI is analyzing the document..."):
                         try:
                            metadata_result = agent.extract_metadata() # Call Phase 4 logic
                            st.session_state.extracted_metadata = metadata_result
                            if metadata_result:
                                ui.display_processing_message("Metadata extraction complete.")
                            else:
                                st.session_state.processing_error = "Metadata extraction failed or returned no results."
                                st.warning(st.session_state.processing_error) # Use warning for failed extraction
                         except Exception as e:
                             st.session_state.processing_error = f"Error during metadata extraction: {str(e)}"
                             st.session_state.extracted_metadata = None # Clear previous results on error
                             st.error(st.session_state.processing_error)
                             print(f"Error calling extract_metadata: {e}")
                else:
                     st.error("Agent not available for extraction.")

            # Display metadata table if extraction was successful and results exist
            if st.session_state.get('extracted_metadata'):
                ui.display_metadata_table(st.session_state.extracted_metadata)
            # Display processing error related to extraction if it occurred
            elif st.session_state.get('processing_error') and "extraction" in st.session_state.processing_error.lower():
                 st.warning(st.session_state.processing_error) # Use warning if extraction specifically failed


    # Show initial prompt if no file is uploaded
    elif not uploaded_file:
        st.info("Upload a PDF rental agreement to start the process.")


# --- Run the main function ---
if __name__ == "__main__":
    main()