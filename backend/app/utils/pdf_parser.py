import PyPDF2
import pdfplumber
import re
from typing import Optional, List, Dict


class PDFParser:
    """Extract text from PDF files"""
    
    @staticmethod
    def extract_text(file_path: str) -> str:
        """Extract text using pdfplumber (best quality)"""
        try:
            with pdfplumber.open(file_path) as pdf:
                text = ""
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
                return text.strip()
        except Exception as e:
            print(f"pdfplumber error: {e}, trying PyPDF2...")
            
            # Fallback to PyPDF2
            try:
                with open(file_path, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    text = ""
                    for page in pdf_reader.pages:
                        text += page.extract_text() + "\n"
                    return text.strip()
            except Exception as e2:
                print(f"PyPDF2 error: {e2}")
                return ""
    
    @staticmethod
    def extract_email(text: str) -> Optional[str]:
        """Extract email address"""
        pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        matches = re.findall(pattern, text)
        return matches[0] if matches else None
    
    @staticmethod
    def extract_phone(text: str) -> Optional[str]:
        """Extract phone number"""
        patterns = [
            r'\+?\d{1,3}[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',
            r'\+?\d{10,}',
        ]
        for pattern in patterns:
            matches = re.findall(pattern, text)
            if matches:
                return matches[0]
        return None
    
    @staticmethod
    def extract_basic_info(text: str) -> Dict[str, Optional[str]]:
        """Extract basic contact information"""
        return {
            "email": PDFParser.extract_email(text),
            "phone": PDFParser.extract_phone(text)
        }