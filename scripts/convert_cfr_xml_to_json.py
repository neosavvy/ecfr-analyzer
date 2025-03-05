#!/usr/bin/env python3
"""
CFR XML to JSON Converter

This script converts CFR XML files to a structured JSON format for efficient lookup.
It extracts only the regulatory text (not citations or explanatory material) and
organizes it for O(1) lookups based on title, part, and section.

Usage:
    python convert_cfr_xml_to_json.py [--input-dir INPUT_DIR] [--output-dir OUTPUT_DIR]

Example:
    python convert_cfr_xml_to_json.py --input-dir bulk --output-dir json_cfr
"""

import os
import re
import json
import argparse
import glob
from pathlib import Path
try:
    from lxml import etree as ET
except ImportError:
    print("ERROR: lxml package is required. Please install it with: pip install lxml")
    print("Then run this script again.")
    exit(1)
from concurrent.futures import ProcessPoolExecutor
import logging
from tqdm import tqdm

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("cfr_conversion.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# XML namespaces in CFR files
namespaces = {
    'ns': 'http://www.govinfo.gov/cfr/exchange/CFR'
}

class CFRConverter:
    """Converts CFR XML files to JSON format optimized for lookups."""
    
    def __init__(self, input_dir, output_dir):
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.title_data = {}
        
    def find_xml_files(self):
        """Find all CFR XML files in the input directory."""
        pattern = os.path.join(self.input_dir, "**", "CFR-*.xml")
        return glob.glob(pattern, recursive=True)
    
    def extract_title_part_info(self, filename):
        """Extract title and part information from the filename."""
        match = re.search(r'CFR-(\d+)-title(\d+)-vol(\d+)', filename)
        if match:
            year = match.group(1)
            title = match.group(2)
            volume = match.group(3)
            return year, title, volume
        return None, None, None
    
    def clean_text(self, text):
        """Clean and normalize text content."""
        if text is None:
            return ""
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Remove XML-specific characters
        text = text.replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')
        
        return text
    
    def extract_text_from_element(self, element):
        """Extract text from an XML element and its children."""
        if element is None:
            return ""
            
        # Get direct text
        text = element.text or ""
        
        # Get text from children
        for child in element:
            # Skip citation elements
            if child.tag.endswith(('CITE', 'CITA', 'FTNT')):
                continue
                
            # Add text from this child
            if child.text:
                text += " " + child.text
                
            # Recursively get text from this child's children
            text += " " + self.extract_text_from_element(child)
                
            # Add tail text
            if child.tail:
                text += " " + child.tail
                
        return self.clean_text(text)
    
    def is_within_citation(self, element):
        """Check if an element is within a citation element."""
        parent = element.getparent()
        while parent is not None:
            if parent.tag.endswith(('CITE', 'CITA', 'FTNT')):
                return True
            parent = parent.getparent()
        return False
    
    def process_section(self, section_element):
        """Process a section element and extract its content."""
        section_num = section_element.find('.//SECTNO')
        section_subject = section_element.find('.//SUBJECT')
        
        # Extract section number and clean it
        if section_num is not None and section_num.text:
            section_number = self.clean_text(section_num.text)
            # Extract just the number part (e.g., "§ 1.1" -> "1.1")
            section_number = re.sub(r'^.*?(\d+\.\d+).*$', r'\1', section_number)
        else:
            section_number = "unknown"
            
        # Extract section title/subject
        section_title = ""
        if section_subject is not None:
            section_title = self.extract_text_from_element(section_subject)
            
        # Extract the content (excluding citations)
        content_elements = section_element.findall('.//P') + section_element.findall('.//FP')
        content = ""
        
        for elem in content_elements:
            # Skip if this is within a citation
            if self.is_within_citation(elem):
                continue
                
            # Extract text from this paragraph
            para_text = self.extract_text_from_element(elem)
            if para_text:
                content += para_text + "\n\n"
                
        return {
            "section_number": section_number,
            "section_title": section_title,
            "content": content.strip()
        }
    
    def process_part(self, part_element):
        """Process a part element and extract its sections."""
        part_num = part_element.find('.//PARTNO')
        part_subject = part_element.find('.//SUBJECT')
        
        # Extract part number
        if part_num is not None and part_num.text:
            part_number = self.clean_text(part_num.text)
            # Extract just the number part (e.g., "PART 1" -> "1")
            part_number = re.sub(r'^.*?(\d+).*$', r'\1', part_number)
        else:
            part_number = "unknown"
            
        # Extract part title
        part_title = ""
        if part_subject is not None:
            part_title = self.extract_text_from_element(part_subject)
            
        # Process all sections in this part
        sections = {}
        section_elements = part_element.findall('.//SECTION')
        
        for section_elem in section_elements:
            section_data = self.process_section(section_elem)
            section_number = section_data["section_number"]
            sections[section_number] = section_data
            
        return {
            "part_number": part_number,
            "part_title": part_title,
            "sections": sections
        }
    
    def process_xml_file(self, xml_file):
        """Process a single XML file and extract its content."""
        try:
            year, title_num, volume = self.extract_title_part_info(xml_file)
            if not all([year, title_num, volume]):
                logger.warning(f"Could not extract title/part info from {xml_file}")
                return None
                
            logger.info(f"Processing {xml_file} (Year: {year}, Title: {title_num}, Volume: {volume})")
            
            # Parse the XML file
            parser = ET.XMLParser(recover=True)  # Use a parser that can recover from errors
            tree = ET.parse(xml_file, parser)
            root = tree.getroot()
            
            # Process all parts in this title
            parts = {}
            part_elements = root.findall('.//PART')
            
            for part_elem in part_elements:
                part_data = self.process_part(part_elem)
                part_number = part_data["part_number"]
                parts[part_number] = part_data
                
            # Create the title data structure
            title_data = {
                "year": year,
                "title_number": title_num,
                "volume": volume,
                "parts": parts
            }
            
            return title_num, year, title_data
            
        except Exception as e:
            logger.error(f"Error processing {xml_file}: {str(e)}")
            return None
    
    def save_json(self, title_num, year, data):
        """Save the processed data to a JSON file."""
        # Create output directory if it doesn't exist
        year_dir = os.path.join(self.output_dir, year)
        os.makedirs(year_dir, exist_ok=True)
        
        # Save to JSON file
        output_file = os.path.join(year_dir, f"title_{title_num}.json")
        with open(output_file, 'w') as f:
            json.dump(data, f, indent=2)
            
        logger.info(f"Saved {output_file}")
    
    def merge_title_data(self, title_num, year, new_data):
        """Merge new title data with existing data."""
        key = (title_num, year)
        
        if key not in self.title_data:
            self.title_data[key] = new_data
            return
            
        # Merge parts
        existing_parts = self.title_data[key]["parts"]
        new_parts = new_data["parts"]
        
        for part_num, part_data in new_parts.items():
            if part_num not in existing_parts:
                existing_parts[part_num] = part_data
            else:
                # Merge sections
                existing_sections = existing_parts[part_num]["sections"]
                new_sections = part_data["sections"]
                
                for section_num, section_data in new_sections.items():
                    if section_num not in existing_sections:
                        existing_sections[section_num] = section_data
    
    def convert(self):
        """Convert all CFR XML files to JSON."""
        xml_files = self.find_xml_files()
        logger.info(f"Found {len(xml_files)} XML files to process")
        
        # Create output directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Process files in parallel
        with ProcessPoolExecutor(max_workers=4) as executor:
            results = list(tqdm(executor.map(self.process_xml_file, xml_files), total=len(xml_files)))
            
        # Merge results and save to JSON
        for result in results:
            if result is not None:
                title_num, year, title_data = result
                self.merge_title_data(title_num, year, title_data)
                
        # Save all merged title data
        for (title_num, year), data in self.title_data.items():
            self.save_json(title_num, year, data)
            
        logger.info(f"Conversion complete. JSON files saved to {self.output_dir}")
        
        # Create lookup index
        self.create_lookup_index()
    
    def create_lookup_index(self):
        """Create a lookup index for all titles, parts, and sections."""
        index = {}
        
        for (title_num, year), data in self.title_data.items():
            if year not in index:
                index[year] = {}
                
            if title_num not in index[year]:
                index[year][title_num] = {
                    "file": f"title_{title_num}.json",
                    "parts": {}
                }
                
            for part_num, part_data in data["parts"].items():
                index[year][title_num]["parts"][part_num] = {
                    "part_title": part_data["part_title"],
                    "sections": list(part_data["sections"].keys())
                }
                
        # Save index to JSON
        index_file = os.path.join(self.output_dir, "index.json")
        with open(index_file, 'w') as f:
            json.dump(index, f, indent=2)
            
        logger.info(f"Created lookup index: {index_file}")

def main():
    parser = argparse.ArgumentParser(description="Convert CFR XML files to JSON format")
    parser.add_argument("--input-dir", default="bulk", help="Directory containing CFR XML files")
    parser.add_argument("--output-dir", default="json_cfr", help="Directory to save JSON files")
    args = parser.parse_args()
    
    converter = CFRConverter(args.input_dir, args.output_dir)
    converter.convert()

if __name__ == "__main__":
    main() 