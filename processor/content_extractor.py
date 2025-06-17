import PyPDF2
import openpyxl
#import pdfplumber
#import pytesseract
from PIL import Image
import requests
from bs4 import BeautifulSoup

def get_text_from_url(url):
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        soup = BeautifulSoup(response.content, 'html.parser')
        text_content = soup.get_text(separator='\n', strip=True)
        return text_content
    except requests.exceptions.RequestException as e:
        return f"Error fetching URL: {e}"
    except Exception as e:
        return f"An error occurred: {e}"
    

def extract_text_from_pdf(pdf_path, default_pages=2):
    """Extracts text from a PDF file."""
    text = ""
    try:
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)  # Corrected class name
            for page_num in range(len(reader.pages)):
                if(page_num>=default_pages):
                    break
                page = reader.pages[page_num]
                text += page.extract_text()
                
    except FileNotFoundError:
        return "Error: PDF file not found."
    except Exception as e:
        return f"Error: An error occurred while processing the PDF: {e}"
    return text

import fitz  # PyMuPDF: pip install pymupdf

def extract_text_with_formatting(pdf_path, default_pages=1):
    """
    Extracts text from a PDF file while preserving formatting.

    Args:
        pdf_path (str): The path to the PDF file.

    Returns:
        str: The extracted text with formatting.
    """
    text = ""
    try:
        pdf_document = fitz.open(pdf_path)
        for page_num in range(pdf_document.page_count):
            if(page_num>=default_pages):
                break
            page = pdf_document[page_num]
            text += page.get_text("text", sort=True)  # "text" mode preserves layout
        pdf_document.close()
    except Exception as e:
      print(f"An error occurred: {e}")
    return text


from docx import Document # pip install python-docx

def extract_text_from_docx(docx_path):
    """Extracts text from a DOCX file."""
    text = ""
    try:
        document = Document(docx_path)
        for paragraph in document.paragraphs:
            text += paragraph.text + "\n"  # Add newline for paragraph separation
    except FileNotFoundError:
        return "Error: DOCX file not found."
    except Exception as e:
        return f"Error: An error occurred while processing the DOCX: {e}"
    return text


import requests
from bs4 import BeautifulSoup

def extract_text_from_linkedin(url):
    """Extracts visible text from a LinkedIn page.
       Requires you to be logged in to see the content."""

    try:
        # Get your LinkedIn cookies. You'll need to inspect your browser's developer tools
        # after logging into LinkedIn to find the appropriate cookie names and values.
        cookies = {
            'li_at': 'YOUR_LI_AT_COOKIE_VALUE', # Replace with your li_at cookie
            # Add other necessary cookies here if required (e.g., JSESSIONID, bcookie)
        }

        cookies = {
            #'li_at': 'AQEDATFj...long string...',
            'JSESSIONID': 'ajax:3896771027886688052',
            'bcookie': '"v=2&07cc9bc8-5da9-4683-8a85-e20ea8fd3e81"'  # Note the quotes are often part of the value
        }

        response = requests.get(url, cookies=cookies) # Include cookies for authentication
        response.raise_for_status()  # Raise an exception for bad status codes

        soup = BeautifulSoup(response.content, 'html.parser')

        # Extract text from the main content area. This might need adjusting
        # depending on the specific LinkedIn page you're scraping.
        main_content = soup.find('body') # Adjust this selector as needed
        if main_content:
            text = main_content.get_text(separator='\n', strip=True) #Use body to get all text.
        else:
            text = "Could not find main content area."

        return text

    except requests.exceptions.RequestException as e:
        return f"Error: A request error occurred: {e}"
    except Exception as e:
        return f"Error: An error occurred: {e}"


# Text Extraction - unchanged
def extract_text_from_attachment(filepath): #The code will be the same
    """Extracts text from different file types."""
    try:
        if filepath.lower().endswith('.pdf'):
            '''
            with pdfplumber.open(filepath) as pdf:
                text = "\n".join([page.extract_text() for page in pdf.pages])
            return text
            '''
            text = extract_text_with_formatting(filepath)
            return text
        
        elif filepath.lower().endswith(('.doc', '.docx')):
            text = extract_text_from_docx(filepath)
            return text
        
        elif filepath.lower().endswith(('.png', '.jpg', '.jpeg')):
            try:
                img = Image.open(filepath)
                text = pytesseract.image_to_string(img) # Requires Tesseract OCR installed
                return text
            except Exception as e:
                print(f"OCR Error: {e}")
                return ""

        elif filepath.lower().endswith(('.xlsx', '.xls')):
            try:
                workbook = openpyxl.load_workbook(filepath)
                text = ""
                for sheet in workbook:
                    for row in sheet.iter_rows():
                        text += " ".join(str(cell.value) for cell in row if cell.value is not None) + "\n"
                return text
            except Exception as e:
                print(f"Excel read error: {e}")
                return ""
        else:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:  # Try UTF-8 encoding
                    return f.read()
            except UnicodeDecodeError:
                 try:
                    with open(filepath, 'r', encoding='latin-1') as f: #Try latin-1 encoding
                        return f.read()
                 except Exception as e:
                    print(f"Text file read error: {e}")
                    return ""
    except Exception as e:
        print(f"File processing error: {e}")
        return ""
    
'''
bill_gate_url = "https://www.linkedin.com/in/williamhgates"
linkedin_text = extract_text_from_linkedin(bill_gate_url)
print(linkedin_text)

# Example Usage
docx_file = "path/to/your/document.docx"  # Replace with your DOCX file path
docx_text = extract_text_from_docx(docx_file)
print(docx_text)

# Example usage
pdf_file = "data/resume/ComputerScienceResumedocx.pdf"  # Replace with your PDF file path
pdf_text = extract_text_with_formatting(pdf_file) # extract_text_from_pdf(pdf_file)
print(pdf_text)'

'''