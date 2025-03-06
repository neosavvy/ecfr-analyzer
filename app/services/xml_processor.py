import re
import xml.etree.ElementTree as ET
from typing import Optional, Dict, Any
from .readability_analyzer import ReadabilityAnalyzer
import logging

logger = logging.getLogger(__name__)

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
    def analyze_content(text: str) -> Dict[str, Any]:
        """
        Analyze the content and return various metrics including readability scores.
        """
        # Handle invalid input
        if not text or not isinstance(text, str):
            return {
                "word_count": 0,
                "sentence_count": 0,
                "paragraph_count": 0,
                "readability_score": 0.0,
                "readability_metrics": {
                    "flesch_reading_ease": 0.0,
                    "smog_index": 0.0,
                    "automated_readability_index": 0.0
                }
            }
            
        # Clean the text
        text = text.strip()
        if not text:
            return {
                "word_count": 0,
                "sentence_count": 0,
                "paragraph_count": 0,
                "readability_score": 0.0,
                "readability_metrics": {
                    "flesch_reading_ease": 0.0,
                    "smog_index": 0.0,
                    "automated_readability_index": 0.0
                }
            }
            
        # Remove any non-printable characters
        text = ''.join(char for char in text if char.isprintable())
        
        # Get basic counts
        word_count = XMLProcessor.count_words(text)
        sentence_count = XMLProcessor.count_sentences(text)
        paragraph_count = XMLProcessor.count_paragraphs(text)
        
        try:
            # Compute readability metrics
            readability_score, detailed_metrics = ReadabilityAnalyzer.compute_readability_score(text)
        except Exception as e:
            logger.error(f"Error computing readability metrics: {str(e)}")
            readability_score, detailed_metrics = 0.0, {
                "flesch_reading_ease": 0.0,
                "smog_index": 0.0,
                "automated_readability_index": 0.0
            }
        
        return {
            "word_count": word_count,
            "sentence_count": sentence_count,
            "paragraph_count": paragraph_count,
            "readability_score": readability_score,
            "readability_metrics": detailed_metrics
        }
    
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