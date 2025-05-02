
# pdf_utils.py

import io
import streamlit as st # Keep for potential caching later
import os # For file extension checking

# --- PDF Libraries ---
import PyPDF2
import fitz # PyMuPDF - Recommended for image rendering for OCR

# --- OCR Library ---
import pytesseract
from PIL import Image # Pillow for image handling

# --- Docx Library ---
import docx

try:
    # --- Windows Example ---
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe' # <--- UPDATE THIS PATH if needed
    # Verify the file exists at the path you provide
    if not os.path.exists(pytesseract.pytesseract.tesseract_cmd):
         print(f"Warning: Tesseract executable not found at specified path: {pytesseract.pytesseract.tesseract_cmd}")
         # Optionally raise an error or revert to PATH check
except Exception as config_ex:
    print(f"Warning: Could not set tesseract_cmd path - {config_ex}. Ensure Tesseract is installed and in PATH or path is set correctly.")


# @st.cache_data # Consider adding caching back later
def _extract_text_image(image_file_object):
    """Extracts text from an uploaded image file object using OCR."""
    print("Attempting OCR on image file...")
    try:
        # Ensure pointer is at the beginning
        image_file_object.seek(0)
        # Open the image using Pillow
        img = Image.open(image_file_object)

        # Perform OCR using pytesseract
        # Timeout can prevent getting stuck
        extracted_text = pytesseract.image_to_string(img, lang='eng', timeout=60) # Longer timeout for potentially large images

        print(f"(OCR Image) Extraction length: {len(extracted_text)}")
        return extracted_text.strip() if extracted_text.strip() else None

    except pytesseract.TesseractError as tess_err:
         print(f"(OCR Image) Tesseract Error processing image: {tess_err}")
         return None # Indicate failure
    except Exception as e:
        print(f"Error extracting text from image: {e}")
        return None
    
def extract_text_from_file(uploaded_file):
    """
    Extracts text content from uploaded PDF, DOCX, Image files, or TXT.
    Uses OCR fallback for PDFs and directly for images.

    Args:
        uploaded_file: An uploaded file object from Streamlit.

    Returns:
        str: The extracted text content, or None if extraction fails or format unsupported.
    """
    if uploaded_file is None:
        return None

    # Define common image extensions
    IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif"}

    try:
        filename = uploaded_file.name
        file_extension = os.path.splitext(filename)[1].lower()
        print(f"Attempting to extract text from '{filename}' (type: {file_extension})")

        # Ensure file pointer is at the beginning
        uploaded_file.seek(0)

        if file_extension == ".pdf":
            return _extract_text_pdf_with_ocr_fallback(uploaded_file)
        elif file_extension == ".docx":
            return _extract_text_docx(uploaded_file)
        elif file_extension == ".txt":
             try:
                 return uploaded_file.getvalue().decode('utf-8', errors='ignore').strip()
             except Exception as txt_e:
                 print(f"Error reading TXT file: {txt_e}")
                 return None
        elif file_extension in IMAGE_EXTENSIONS: # Check if it's a supported image type
             return _extract_text_image(uploaded_file)
        else:
            print(f"Unsupported file type: {file_extension}")
            # Optionally try OCR anyway? Risky. Better to return None.
            # st.warning(f"Unsupported file type '{file_extension}'. Only PDF, DOCX, TXT, PNG, JPG, BMP, TIFF are supported.")
            return None

    except Exception as e:
        print(f"General error during file processing in extract_text_from_file: {e}")
        return None


def _extract_text_pdf_with_ocr_fallback(pdf_file_object):
    """Extract text from PDF using PyPDF2, with PyMuPDF+Tesseract OCR fallback."""
    extracted_text_pypdf2 = ""
    ocr_needed = False
    page_count_pypdf2 = 0

    # --- Attempt 1: Standard Text Extraction (PyPDF2) ---
    print("Attempting standard PDF text extraction (PyPDF2)...")
    try:
        pdf_file_object.seek(0) # Reset pointer
        reader = PyPDF2.PdfReader(pdf_file_object)
        page_count_pypdf2 = len(reader.pages)
        print(f"(PyPDF2) PDF has {page_count_pypdf2} pages.")

        for i, page in enumerate(reader.pages):
            page_num = i + 1
            try:
                page_text = page.extract_text()
                if page_text and page_text.strip():
                    extracted_text_pypdf2 += page_text + f"\n\n--- Page {page_num} End ---\n\n"
                else:
                    print(f"(PyPDF2) Warning: No text found on page {page_num}. Flagging for potential OCR.")
                    ocr_needed = True # Flag OCR might be useful
                    extracted_text_pypdf2 += f"\n\n--- Page {page_num} (No text via PyPDF2) ---\n\n"
            except Exception as page_ex: # Catch errors on specific pages
                print(f"(PyPDF2) Error extracting text from page {page_num}: {page_ex}")
                extracted_text_pypdf2 += f"\n\n--- Error on Page {page_num} (PyPDF2) ---\n\n"
                ocr_needed = True # Error suggests OCR might help

        extracted_text_pypdf2 = extracted_text_pypdf2.strip()
        print(f"(PyPDF2) Initial extraction length: {len(extracted_text_pypdf2)}")
        # Decide if OCR is needed: if flagged OR if total extracted text is very short relative to page count
        if not ocr_needed and len(extracted_text_pypdf2) < page_count_pypdf2 * 50: # Arbitrary threshold: < 50 chars/page avg
             print("(PyPDF2) Extracted text seems short, flagging for potential OCR check.")
             ocr_needed = True

    except PyPDF2.errors.PdfReadError as pdf_err:
         print(f"(PyPDF2) Invalid PDF file error: {pdf_err}. Attempting OCR.")
         ocr_needed = True
    except Exception as e:
        print(f"(PyPDF2) General error: {e}. Attempting OCR.")
        ocr_needed = True

    # --- Attempt 2: OCR Fallback (PyMuPDF + Tesseract) ---
    if ocr_needed:
        print("Attempting OCR fallback using PyMuPDF and Tesseract...")
        extracted_text_ocr = ""
        try:
            pdf_file_object.seek(0) # Reset pointer
            pdf_bytes = pdf_file_object.read() # Read bytes for fitz
            pdf_document = fitz.open(stream=pdf_bytes, filetype="pdf")
            page_count_ocr = pdf_document.page_count
            print(f"(OCR) Processing {page_count_ocr} pages.")

            for page_num_idx in range(page_count_ocr):
                page_num = page_num_idx + 1
                try:
                    page = pdf_document.load_page(page_num_idx)
                    # Higher DPI generally yields better OCR results
                    pix = page.get_pixmap(dpi=300)
                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

                    # Perform OCR using pytesseract
                    # Timeout can prevent getting stuck on problematic pages
                    page_text_ocr = pytesseract.image_to_string(img, lang='eng', timeout=30) # 30 second timeout per page

                    if page_text_ocr and page_text_ocr.strip():
                         extracted_text_ocr += page_text_ocr + f"\n\n--- Page {page_num} End (OCR) ---\n\n"
                    else:
                         print(f"(OCR) Warning: No text found on page {page_num}.")
                         extracted_text_ocr += f"\n\n--- Page {page_num} (No text via OCR) ---\n\n"

                except pytesseract.TesseractError as tess_err:
                     print(f"(OCR) Tesseract Error processing page {page_num}: {tess_err}")
                     extracted_text_ocr += f"\n\n--- Tesseract Error on Page {page_num} ---\n\n"
                except Exception as ocr_page_ex:
                     print(f"(OCR) General Error processing page {page_num}: {ocr_page_ex}")
                     extracted_text_ocr += f"\n\n--- Error on Page {page_num} (OCR) ---\n\n"

            pdf_document.close()
            extracted_text_ocr = extracted_text_ocr.strip()
            print(f"(OCR) Extraction length: {len(extracted_text_ocr)}")

            # Compare results: Prefer OCR if it found substantially more text
            # Or if PyPDF2 result was effectively empty
            if len(extracted_text_ocr) > max(len(extracted_text_pypdf2) * 1.2, 100): # If OCR is >20% longer OR > 100 chars when PyPDF2 was empty
                print("Using OCR result.")
                return extracted_text_ocr if extracted_text_ocr else None
            else:
                print("Using standard PyPDF2 extraction result (or OCR was not better).")
                return extracted_text_pypdf2 if extracted_text_pypdf2 else None

        except Exception as ocr_err:
            print(f"Error during OCR top-level processing: {ocr_err}. Falling back to PyPDF2 result.")
            # Fallback to PyPDF2 result if OCR failed completely
            return extracted_text_pypdf2 if extracted_text_pypdf2 else None
    else:
        # If OCR was not needed and PyPDF2 worked
        print("Standard PyPDF2 extraction sufficient.")
        return extracted_text_pypdf2


def _extract_text_docx(docx_file_object):
    """Extracts text content from an uploaded DOCX file object."""
    try:
        docx_file_object.seek(0) # Reset pointer
        document = docx.Document(docx_file_object)
        full_text = [para.text for para in document.paragraphs if para.text] # Ensure paragraph has text
        print(f"Successfully extracted text from DOCX.")
        result = '\n\n'.join(full_text).strip()
        return result if result else None # Return None if document was empty
    except Exception as e:
        print(f"Error extracting text from DOCX: {e}")
        return None