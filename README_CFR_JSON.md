# CFR XML to JSON Conversion

This set of tools converts Code of Federal Regulations (CFR) XML files to a structured JSON format optimized for efficient lookups. The conversion extracts only the regulatory text (not citations or explanatory material) and organizes it for O(1) constant time lookups based on title, part, and section.

## Features

- Extracts only the regulatory text, excluding citations and explanatory material
- Organizes data hierarchically by year, title, part, and section
- Creates an index for efficient lookups
- Supports parallel processing for faster conversion
- Provides a simple lookup utility to demonstrate usage

## Requirements

- Python 3.6+
- Required packages: `tqdm` (for progress bars)

Install the required package:

```bash
pip install tqdm
```

## Usage

### 1. Convert XML to JSON

Run the conversion script to process all CFR XML files in the bulk directory:

```bash
python scripts/convert_cfr_xml_to_json.py --input-dir bulk --output-dir json_cfr
```

Options:
- `--input-dir`: Directory containing CFR XML files (default: "bulk")
- `--output-dir`: Directory to save JSON files (default: "json_cfr")

The script will:
1. Recursively find all CFR XML files in the input directory
2. Extract regulatory text from each file
3. Organize the data by year, title, part, and section
4. Save the data as JSON files in the output directory
5. Create an index file for efficient lookups

### 2. Look up CFR Sections

Use the lookup utility to retrieve specific CFR sections:

```bash
python scripts/lookup_cfr_section.py --year 1996 --title 21 --part 1 --section 1.1
```

Options:
- `--year`: Year of the CFR (e.g., 1996)
- `--title`: CFR title number (e.g., 21)
- `--part`: CFR part number (e.g., 1)
- `--section`: CFR section number (e.g., 1.1)
- `--json-dir`: Directory containing JSON files (default: "json_cfr")

## JSON Structure

The conversion creates the following structure:

1. **Title Files** (`json_cfr/<year>/title_<number>.json`):
   - Contains all parts and sections for a specific title and year
   - Organized hierarchically for efficient lookups

2. **Index File** (`json_cfr/index.json`):
   - Maps years, titles, parts, and sections to their locations
   - Enables quick verification of available data

### Example JSON Structure

```json
{
  "year": "1996",
  "title_number": "21",
  "volume": "1",
  "parts": {
    "1": {
      "part_number": "1",
      "part_title": "General Enforcement Regulations",
      "sections": {
        "1.1": {
          "section_number": "1.1",
          "section_title": "General",
          "content": "This part contains the general provisions applicable to all regulations issued by the Food and Drug Administration."
        },
        "1.2": {
          "section_number": "1.2",
          "section_title": "Definitions",
          "content": "..."
        }
      }
    }
  }
}
```

## Programmatic Usage

You can also use the conversion and lookup functionality in your own Python code:

```python
from scripts.convert_cfr_xml_to_json import CFRConverter
from scripts.lookup_cfr_section import lookup_section

# Convert XML to JSON
converter = CFRConverter("bulk", "json_cfr")
converter.convert()

# Look up a section
section_data = lookup_section("json_cfr", "1996", "21", "1", "1.1")
print(section_data["content"])
```

## Performance Considerations

- The conversion process uses parallel processing to speed up XML parsing
- JSON files are organized to enable O(1) constant time lookups
- For very large datasets, consider using a database instead of JSON files

## Troubleshooting

- If you encounter memory issues during conversion, reduce the parallelism by modifying the `ProcessPoolExecutor` in the script
- If XML files have unexpected structures, check the logs for specific errors
- For very large XML files, you may need to increase Python's recursion limit 