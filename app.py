import streamlit as st
import os
from dotenv import load_dotenv

# Import UI functions and potentially agent/utils later
import ui
# import pdf_utils # Will be needed in Phase 2
# from agents import RentalAgreementAgent # Will be needed in Phase 3

# --- Load Environment Variables ---
load_dotenv()
# Example of how to get the key (will be used in Phase 3)
# google_api_key = os.getenv("GOOGLE_API_KEY")

# --- Page Configuration (MUST be the first Streamlit command) ---
st.set_page_config(
    page_title="Rental Agreement Extractor",
    page_icon="📄",
    layout="wide"
)

# --- Initialize Session State ---
# This will hold data across reruns
if 'uploaded_filename' not in st.session_state:
    st.session_state.uploaded_filename = None
if 'extracted_text' not in st.session_state:
    st.session_state.extracted_text = None
if 'rag_index_ready' not in st.session_state:
    st.session_state.rag_index_ready = False
if 'extracted_metadata' not in st.session_state:
    st.session_state.extracted_metadata = None
if 'processing_error' not in st.session_state:
    st.session_state.processing_error = None
# Add 'agent' to session state later in Phase 3


# --- Main Application Logic ---
def main():
    # --- Render Header ---
    ui.display_header()

    # --- Step 1: Upload Area ---
    uploaded_file = ui.display_upload_area()

    # --- Step 2 (Placeholder): Process Upload & Extract Text ---
    if uploaded_file:
        # Basic check if it's a new file
        if uploaded_file.name != st.session_state.uploaded_filename:
            st.session_state.uploaded_filename = uploaded_file.name
            st.session_state.extracted_text = None # Reset state for new file
            st.session_state.rag_index_ready = False
            st.session_state.extracted_metadata = None
            st.session_state.processing_error = None
            ui.display_processing_message(f"Processing '{uploaded_file.name}'...")
            # --- Call Phase 2 logic here (Text Extraction) ---
            # Placeholder: In Phase 2, call pdf_utils and update session state
            st.session_state.extracted_text = f"Placeholder: Text for '{uploaded_file.name}' would be extracted here." # Replace in Phase 2
            if st.session_state.extracted_text:
                 ui.display_processing_message("Text extracted.")
            else:
                 ui.display_processing_message("Text extraction failed.")
                 st.session_state.processing_error = "Text extraction failed."


        # --- Display Text Preview (if extracted) ---
        if st.session_state.extracted_text:
            ui.display_text_preview(st.session_state.extracted_text)
        elif st.session_state.processing_error:
             st.error(st.session_state.processing_error)


        # --- Step 3 & 4 (Placeholder): Process Document & Extract Metadata ---
        if st.session_state.extracted_text: # Only proceed if text is available
             # --- Placeholder: Indexing (Phase 3) ---
             # Add logic here later: If not indexed -> button "Create Index" -> call agent.load_and_index... -> update rag_index_ready
             st.session_state.rag_index_ready = True # Assume ready for now

             if st.session_state.rag_index_ready:
                # --- Extraction Button (Phase 5) ---
                if ui.display_extract_button():
                    ui.display_processing_message("Extracting metadata...")
                    with st.spinner("AI is analyzing the document..."):
                        # --- Call Phase 4 logic here (Metadata Extraction) ---
                        # Placeholder: In Phase 5, call agent.extract_metadata()
                        st.session_state.extracted_metadata = { # Replace with actual call
                            "Agreement Value": "$1500/month (Placeholder)",
                            "Agreement Start Date": "2024-01-01 (Placeholder)",
                            "Agreement End Date": "2024-12-31 (Placeholder)",
                            "Renewal Notice (Days)": "60 (Placeholder)",
                            "Party One": "Jane Doe (Placeholder)",
                            "Party Two": "Landlord Corp (Placeholder)"
                        }
                        if st.session_state.extracted_metadata:
                            ui.display_processing_message("Metadata extraction complete.")
                        else:
                            ui.display_processing_message("Metadata extraction failed.")
                            st.session_state.processing_error = "Metadata extraction failed."
             else:
                 ui.display_processing_message("Document needs to be processed (indexed) first.")

    # --- Step 5 (Placeholder): Display Results Table ---
    # Display metadata only if it exists in session state
    if st.session_state.extracted_metadata:
        ui.display_metadata_table(st.session_state.extracted_metadata)
    elif not uploaded_file:
         st.info("Upload a PDF agreement to start.")


# --- Run the main function ---
if __name__ == "__main__":
    main()