# Historical Metrics Fake Data Generator

This project includes tools to generate, analyze, and manage fake historical metrics data for federal regulation documents. These tools are designed to help you build and test your frontend before implementing real metrics calculation.

## Overview

The fake data generation system creates a complete data pipeline:
1. First, it generates search descriptors for each agency
2. Then it creates documents based on those descriptors
3. Finally, it generates 20 years of historical metrics for each document

The generated data follows realistic trends over time, with documents generally becoming longer and more complex as years progress.

## Quick Start

1. **Create the necessary tables**:
   ```bash
   alembic upgrade head
   ```

2. **Install required packages**:
   ```bash
   pip install faker pandas numpy matplotlib
   ```

3. **Generate fake documents and descriptors**:
   ```bash
   python scripts/generate_fake_documents.py
   ```

4. **Generate fake metrics data**:
   ```bash
   python scripts/generate_fake_metrics.py
   ```

5. **Analyze the generated data**:
   ```bash
   python scripts/analyze_metrics_data.py
   ```

6. **When ready for real data, clean the database**:
   ```bash
   python scripts/clean_metrics_data.py
   ```

## Available Scripts

### 1. Generate Fake Documents (`scripts/generate_fake_documents.py`)

This script creates a complete document hierarchy for each agency:

- Creates 20 search descriptors per agency
- Generates one document for each descriptor
- Creates realistic document titles, IDs, and hierarchies
- Adds sample content and metadata
- Skips agencies that already have enough descriptors

**Usage**:
```bash
python scripts/generate_fake_documents.py
```

**Configuration Options** (edit the script to modify):
- `DESCRIPTORS_PER_AGENCY`: Number of descriptors to create per agency (default: 20)
- `BATCH_SIZE`: Number of records to insert at once (default: 50)

### 2. Generate Fake Metrics (`scripts/generate_fake_metrics.py`)

This script creates historical metrics records for all documents in your database:

- Creates one metrics record per year (2003-2023) for each document
- Generates realistic trending values (documents get longer and more complex over time)
- Adds random volatility to make the data look natural
- Processes in batches to handle large datasets
- Skips agencies that already have metrics data

**Usage**:
```bash
python scripts/generate_fake_metrics.py
```

**Configuration Options** (edit the script to modify):
- `START_YEAR` / `END_YEAR`: Date range for historical data (default: 2003-2023)
- `BATCH_SIZE`: Number of records to insert at once (default: 100)
- Various range parameters for metrics values

### 3. Analyze Metrics Data (`scripts/analyze_metrics_data.py`)

This script provides statistics about the generated data:

- Total number of metrics records
- Metrics count by year
- Top agencies by metrics count
- Average metrics values
- Metrics trends over time
- Notable documents (most metrics, highest complexity, highest readability)

**Usage**:
```bash
python scripts/analyze_metrics_data.py
```

### 4. Clean Metrics Data (`scripts/clean_metrics_data.py`)

This script removes all metrics data when you're ready to start with real data:

- Counts and displays the number of records to be deleted
- Asks for confirmation before deleting
- Resets ID sequences if possible

**Usage**:
```bash
python scripts/clean_metrics_data.py
```

## Data Model

### Search Descriptors

The fake search descriptors include:
- Hierarchical structure (title, chapter, part, subpart)
- Date ranges (starts_on, ends_on)
- Type information (PART, SUBPART, SECTION, etc.)
- Hierarchy headings and full text excerpts
- Processing status and other metadata

### Documents

The fake documents include:
- Realistic titles based on regulation topics and sectors
- Unique document IDs in a standard format
- Sample content and metadata
- Creation and update timestamps
- Association with the correct agency and descriptor hierarchy

### Metrics

The fake data populates the `AgencyRegulationDocumentHistoricalMetrics` model with the following fields:

- **Basic Information**:
  - `id`: UUID primary key
  - `metrics_date`: Date of the metrics snapshot (Dec 31 of each year)
  - `agency_id`: Foreign key to the agency
  - `document_id`: Foreign key to the document

- **Document Metrics**:
  - `word_count`: Number of words in the document
  - `paragraph_count`: Number of paragraphs
  - `sentence_count`: Number of sentences
  - `section_count`: Number of sections
  - `subpart_count`: Number of subparts

- **Complexity Metrics**:
  - `language_complexity_score`: Overall complexity (0.1-1.0)
  - `readability_score`: Readability (30-100, higher is more readable)
  - `average_sentence_length`: Average words per sentence
  - `average_word_length`: Average characters per word
  - `simplicity_score`: Overall simplicity (inverse of complexity)

- **Author Metrics**:
  - `total_authors`: Number of unique authors who have touched the document
  - `revision_authors`: Number of authors who touched the document in this revision

- **Content**:
  - `content_snapshot`: Sample of the document content

## Data Characteristics

The generated data has the following characteristics:

1. **Complete Data Pipeline**:
   - Search descriptors → Documents → Historical metrics
   - All properly linked with foreign keys

2. **Realistic Hierarchies**:
   - Documents organized by title, chapter, part, subpart
   - Descriptors with proper types and structure

3. **Realistic Trends**:
   - Word count increases by ~3% per year on average
   - Complexity increases by ~2% per year
   - Readability decreases by ~1% per year
   - Author count grows over time

4. **Natural Variation**:
   - Each document has its own baseline values
   - Random volatility makes trends look natural
   - No perfect linear progression

5. **Consistency**:
   - Each document has one record per year
   - All metrics are properly related to their documents and agencies
   - Unique constraint prevents duplicate metrics for the same document/date

## Frontend Development

This fake data is particularly useful for developing:

1. **Historical Trend Charts**:
   - Line charts showing metrics changes over time
   - Comparison charts between agencies or documents

2. **Complexity Analysis**:
   - Heatmaps of document complexity
   - Readability scores visualization

3. **Agency Dashboards**:
   - Summary statistics by agency
   - Document counts and averages

4. **Document Detail Views**:
   - Historical metrics for individual documents
   - Year-over-year comparisons

5. **Hierarchical Navigation**:
   - Browse documents by title, chapter, part, subpart
   - Filter by document type or status

## Transitioning to Real Data

When you're ready to implement real metrics calculation:

1. Run the cleanup script to remove all fake data:
   ```bash
   python scripts/clean_metrics_data.py
   ```

2. Implement your real metrics calculation logic

3. The database schema will remain the same, so your frontend should work with both fake and real data

## Troubleshooting

- **Memory Issues**: If you encounter memory problems with large datasets, reduce the `BATCH_SIZE` in the generation scripts
- **Missing Dependencies**: Ensure you've installed all required packages
- **Database Connection**: Check your database connection settings in `app/database.py`
- **UUID Errors**: Some databases require special handling for UUID columns 