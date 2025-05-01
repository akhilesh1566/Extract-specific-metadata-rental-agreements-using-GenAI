import PyPDF2
import io
# No streamlit import needed here for now

def extract_text_from_pdf(pdf_file_object):
    """
    Extracts text content from an uploaded PDF file object.

    Args:
        pdf_file_object: An uploaded file object from Streamlit (like BytesIO).

    Returns:
        str: The extracted text content from all pages, or None if extraction fails.
    """
    if pdf_file_object is None:
        return None

    extracted_text = ""
    try:
        # Ensure the file pointer is at the beginning (important for reruns)
        pdf_file_object.seek(0)
        reader = PyPDF2.PdfReader(pdf_file_object)
        num_pages = len(reader.pages)
        print(f"PDF has {num_pages} pages.")

        for i, page in enumerate(reader.pages):
            try:
                page_text = page.extract_text()
                if page_text:
                    extracted_text += page_text + "\n\n--- Page {} End ---\n\n".format(i+1) # Clearer separator
                else:
                    print(f"Warning: No text found on page {i+1}")
            except Exception as page_ex:
                # Catch errors extracting from a specific page
                print(f"Error extracting text from page {i+1}: {page_ex}")
                extracted_text += f"\n\n--- Error on Page {i+1} ---\n\n" # Indicate page error

        print(f"Successfully extracted approx {len(extracted_text)} characters.")
        # Return stripped text, or None if nothing meaningful was extracted
        return extracted_text.strip() if extracted_text.strip() else None

    # Catch broader errors like invalid PDF format
    except PyPDF2.errors.PdfReadError as pdf_err:
         print(f"Invalid PDF file error: {pdf_err}")
         return None
    except Exception as e:
        print(f"General error extracting text from PDF: {e}")
        return None