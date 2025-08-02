import fitz  # PyMuPDF
import cv2
import numpy as np
from typing import List, Dict, Any
import os
import tempfile

class PDFProcessor:
    def __init__(self):
        """
        PDF processor for converting PDF pages to images and extracting content.
        """
        self.supported_formats = ['.pdf']
    
    def process_pdf_pages(self, pdf_path: str) -> List[Dict[str, Any]]:
        """
        Process all pages of a PDF and convert them to images.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            List of dictionaries containing page data and images
        """
        try:
            # Open the PDF
            pdf_document = fitz.open(pdf_path)
            processed_pages = []
            
            for page_num in range(len(pdf_document)):
                # Get the page
                page = pdf_document[page_num]
                
                # Convert page to image
                mat = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0))  # 2x zoom for better quality
                
                # Convert to numpy array
                img_array = np.frombuffer(mat.samples, dtype=np.uint8)
                img_array = img_array.reshape(mat.height, mat.width, mat.n)
                
                # Convert to BGR format for OpenCV
                if mat.n == 4:  # RGBA
                    img_array = cv2.cvtColor(img_array, cv2.COLOR_RGBA2BGR)
                elif mat.n == 1:  # Grayscale
                    img_array = cv2.cvtColor(img_array, cv2.COLOR_GRAY2BGR)
                
                processed_pages.append({
                    'page_number': page_num + 1,
                    'image': img_array,
                    'width': mat.width,
                    'height': mat.height,
                    'rotation': page.rotation
                })
            
            pdf_document.close()
            return processed_pages
            
        except Exception as e:
            print(f"Error processing PDF: {e}")
            return []
    
    def extract_text_from_pdf(self, pdf_path: str) -> List[Dict[str, Any]]:
        """
        Extract text from PDF pages with positioning information.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            List of dictionaries containing text blocks with positions
        """
        try:
            pdf_document = fitz.open(pdf_path)
            all_text_blocks = []
            
            for page_num in range(len(pdf_document)):
                page = pdf_document[page_num]
                
                # Extract text blocks
                text_dict = page.get_text("dict")
                
                for block in text_dict["blocks"]:
                    if "lines" in block:
                        for line in block["lines"]:
                            for span in line["spans"]:
                                text_block = {
                                    'text': span["text"],
                                    'page_number': page_num + 1,
                                    'bounding_box': [
                                        span["bbox"][0],  # x1
                                        span["bbox"][1],  # y1
                                        span["bbox"][2],  # x2
                                        span["bbox"][3]   # y2
                                    ],
                                    'font_size': span["size"],
                                    'font_name': span["font"]
                                }
                                all_text_blocks.append(text_block)
            
            pdf_document.close()
            return all_text_blocks
            
        except Exception as e:
            print(f"Error extracting text from PDF: {e}")
            return []
    
    def get_pdf_info(self, pdf_path: str) -> Dict[str, Any]:
        """
        Get basic information about the PDF.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Dictionary containing PDF metadata
        """
        try:
            pdf_document = fitz.open(pdf_path)
            
            info = {
                'page_count': len(pdf_document),
                'title': pdf_document.metadata.get('title', ''),
                'author': pdf_document.metadata.get('author', ''),
                'subject': pdf_document.metadata.get('subject', ''),
                'creator': pdf_document.metadata.get('creator', ''),
                'producer': pdf_document.metadata.get('producer', ''),
                'creation_date': pdf_document.metadata.get('creationDate', ''),
                'modification_date': pdf_document.metadata.get('modDate', '')
            }
            
            pdf_document.close()
            return info
            
        except Exception as e:
            print(f"Error getting PDF info: {e}")
            return {}
    
    def save_page_as_image(self, pdf_path: str, page_num: int, output_path: str, 
                          zoom: float = 2.0) -> bool:
        """
        Save a specific page as an image.
        
        Args:
            pdf_path: Path to the PDF file
            page_num: Page number (1-based)
            output_path: Output image path
            zoom: Zoom factor for image quality
            
        Returns:
            True if successful, False otherwise
        """
        try:
            pdf_document = fitz.open(pdf_path)
            
            if page_num > len(pdf_document):
                print(f"Page {page_num} does not exist")
                return False
            
            page = pdf_document[page_num - 1]  # Convert to 0-based
            mat = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
            
            # Save the image
            mat.save(output_path)
            
            pdf_document.close()
            return True
            
        except Exception as e:
            print(f"Error saving page as image: {e}")
            return False
    
    def extract_emergency_symbols_from_pdf(self, pdf_path: str) -> List[Dict[str, Any]]:
        """
        Extract emergency lighting symbols from PDF text.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            List of emergency symbol occurrences
        """
        emergency_symbols = ['EL', 'A1', 'A1E', 'A2', 'A2E', 'W', 'E1', 'E2', 'EM', 'EXIT']
        text_blocks = self.extract_text_from_pdf(pdf_path)
        emergency_occurrences = []
        
        for block in text_blocks:
            text = block['text'].upper()
            
            for symbol in emergency_symbols:
                if symbol in text:
                    emergency_occurrences.append({
                        'symbol': symbol,
                        'text': block['text'],
                        'page_number': block['page_number'],
                        'bounding_box': block['bounding_box'],
                        'font_size': block['font_size']
                    })
                    break
        
        return emergency_occurrences 