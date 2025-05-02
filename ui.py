# ui.py
import streamlit as st
import pandas as pd
import io # Keep for BytesIO
import base64

# --- Existing Functions ---
def display_header():
    st.title("📄 Rental Agreement Metadata Extractor")
    st.markdown("Upload a PDF or DOCX rental agreement to extract key information.") # Singular
    st.markdown("---")

# --- Modified ---
def display_upload_area():
    """Displays the file uploader widget for a SINGLE file."""
    st.subheader("1. Upload Agreement")
    uploaded_file = st.file_uploader(
        "Choose a Rental Agreement File (PDF or DOCX)", # Singular
        type=["pdf", "docx"], # Keep both types
        accept_multiple_files=False # Back to single file
    )
    return uploaded_file # Returns a single file object or None

def display_processing_message(message_type, message):
    """Displays status messages using different types."""
    if message_type == "info":
        st.info(message)
    elif message_type == "success":
        st.success(message)
    elif message_type == "warning":
        st.warning(message)
    elif message_type == "error":
        st.error(message)
    else:
        st.write(message)

def display_process_button(disabled=False):
    # Button text is fine
    if st.button("📊 Process Document (Index)", disabled=disabled): # Clarify purpose
        return True
    return False

def display_extract_button(disabled=False):
    # Button text is fine
    if st.button("✨ Extract Key Information", type="primary", disabled=disabled):
        return True
    return False

# --- Keep Excel conversion helper ---
@st.cache_data
def convert_df_to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Metadata')
    processed_data = output.getvalue()
    return processed_data

# --- Modified Table Display (Takes single dict) ---
def display_metadata_table(metadata_dict, filename=""): # Accept filename optionally
    """Displays extracted metadata for a single file in a table with download."""
    st.subheader("3. Extracted Information")
    st.caption(f"Results for: **{filename}**") if filename else None # Display filename

    if metadata_dict:
        # Prepare data for display and potential DataFrame creation
        display_data = []
        error_found = False
        for field, value in metadata_dict.items():
            status = "✅"
            if value is None or str(value).strip() == "":
                value = "Not Found"
                status = "❓"
            # Check for specific error strings set by the agent
            elif isinstance(value, str) and ("not found" in value.lower() and len(value) < 20): # Allow longer "Not Found" explanations
                 status = "❓"
                 value = "Not Found" # Standardize
            elif isinstance(value, str) and ("error" in value.lower() and len(value) < 50): # Basic error check
                status = "❌"
                error_found = True

            display_data.append({"Field": field, "Value": value, "Status": status})

        if not display_data:
             st.warning("No metadata fields processed.")
             return

        df = pd.DataFrame(display_data)

        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={ # Add configuration for better display
                "Field": st.column_config.TextColumn("Field", width="medium"),
                "Value": st.column_config.TextColumn("Extracted Value", width="large"),
                "Status": st.column_config.TextColumn("Status", width="small"),
            }
         )

        # --- Add Download Button ---
        # Only offer download if no critical errors were found during extraction
        if not error_found or st.checkbox("Include rows with errors in download?"):
            st.markdown("---")
            # Prepare DataFrame for export (maybe without status)
            export_df = df[['Field', 'Value']].copy()
            excel_bytes = convert_df_to_excel(export_df)
            st.download_button(
                label="📥 Download Results as Excel",
                data=excel_bytes,
                file_name=f'metadata_{filename}.xlsx' if filename else 'rental_agreement_metadata.xlsx',
                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
        elif error_found:
             st.warning("Extraction errors detected. Download disabled unless checkbox is checked.")


    else:
        st.warning("No metadata extracted yet or extraction failed.")
    st.markdown("---")

    
