#!/usr/bin/env python3
"""
CFR Section Lookup Utility

This script demonstrates how to look up CFR sections from the JSON data
created by the convert_cfr_xml_to_json.py script.

Usage:
    python lookup_cfr_section.py --year YEAR --title TITLE --part PART --section SECTION [--json-dir JSON_DIR]

Example:
    python lookup_cfr_section.py --year 1996 --title 21 --part 1 --section 1.1
"""

import os
import json
import argparse
import sys

def load_index(json_dir):
    """Load the CFR index file."""
    index_path = os.path.join(json_dir, "index.json")
    try:
        with open(index_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: Index file not found at {index_path}")
        print("Please run convert_cfr_xml_to_json.py first to create the JSON data.")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in index file {index_path}")
        sys.exit(1)

def load_title_data(json_dir, year, title):
    """Load the data for a specific title and year."""
    file_path = os.path.join(json_dir, year, f"title_{title}.json")
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: Title data file not found at {file_path}")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in title data file {file_path}")
        sys.exit(1)

def lookup_section(json_dir, year, title, part, section):
    """Look up a specific CFR section."""
    # Load the index to verify the requested data exists
    index = load_index(json_dir)
    
    # Check if the requested year exists
    if year not in index:
        print(f"Error: No data available for year {year}")
        print(f"Available years: {', '.join(sorted(index.keys()))}")
        return None
    
    # Check if the requested title exists
    if title not in index[year]:
        print(f"Error: No data available for title {title} in year {year}")
        print(f"Available titles for {year}: {', '.join(sorted(index[year].keys()))}")
        return None
    
    # Check if the requested part exists
    if part not in index[year][title]["parts"]:
        print(f"Error: No data available for part {part} in title {title}, year {year}")
        print(f"Available parts: {', '.join(sorted(index[year][title]['parts'].keys()))}")
        return None
    
    # Check if the requested section exists
    if section not in index[year][title]["parts"][part]["sections"]:
        print(f"Error: No data available for section {section} in part {part}, title {title}, year {year}")
        print(f"Available sections: {', '.join(sorted(index[year][title]['parts'][part]['sections']))}")
        return None
    
    # Load the title data
    title_data = load_title_data(json_dir, year, title)
    
    # Extract the section data (O(1) lookup)
    section_data = title_data["parts"][part]["sections"][section]
    
    return section_data

def format_section_data(section_data):
    """Format section data for display."""
    if not section_data:
        return "No data found."
    
    output = []
    output.append(f"Section: {section_data['section_number']}")
    output.append(f"Title: {section_data['section_title']}")
    output.append("\nContent:")
    output.append(section_data['content'])
    
    return "\n".join(output)

def main():
    parser = argparse.ArgumentParser(description="Look up CFR sections from JSON data")
    parser.add_argument("--year", required=True, help="Year of the CFR (e.g., 1996)")
    parser.add_argument("--title", required=True, help="CFR title number (e.g., 21)")
    parser.add_argument("--part", required=True, help="CFR part number (e.g., 1)")
    parser.add_argument("--section", required=True, help="CFR section number (e.g., 1.1)")
    parser.add_argument("--json-dir", default="json_cfr", help="Directory containing JSON files")
    args = parser.parse_args()
    
    section_data = lookup_section(
        args.json_dir, 
        args.year, 
        args.title, 
        args.part, 
        args.section
    )
    
    print(format_section_data(section_data))

if __name__ == "__main__":
    main() 