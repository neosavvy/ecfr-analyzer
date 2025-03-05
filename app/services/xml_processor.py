import re
import xml.etree.ElementTree as ET
from typing import Optional

class XMLProcessor:
    """Service for processing XML content from eCFR API"""
    
    @staticmethod
    def extract_text_from_xml(xml_content: str) -> Optional[str]:
        """
        Extract plain text from XML content.
        Returns None if the XML is invalid.
        """
        try:
            # Remove XML declaration if present
            xml_content = re.sub(r'<\?xml[^>]+\?>', '', xml_content)
            
            # Parse the XML
            root = ET.fromstring(f"<root>{xml_content}</root>")
            
            # Extract all text content
            text_content = []
            for elem in root.iter():
                if elem.text and elem.text.strip():
                    text_content.append(elem.text.strip())
                if elem.tail and elem.tail.strip():
                    text_content.append(elem.tail.strip())
            
            # Join all text with newlines
            return "\n".join(text_content)
        except Exception as e:
            print(f"Error processing XML: {str(e)}")
            return None
    
    @staticmethod
    def count_words(text: str) -> int:
        """Count the number of words in a text"""
        if not text:
            return 0
        return len(re.findall(r'\b\w+\b', text))
    
    @staticmethod
    def count_sentences(text: str) -> int:
        """Count the number of sentences in a text"""
        if not text:
            return 0
        return len(re.findall(r'[.!?]+', text))
    
    @staticmethod
    def count_paragraphs(text: str) -> int:
        """Count the number of paragraphs in a text"""
        if not text:
            return 0
        return len(re.split(r'\n\s*\n', text)) 