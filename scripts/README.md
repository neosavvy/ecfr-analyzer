# Metrics Data Scripts

This directory contains scripts for managing and analyzing historical metrics data.

## Available Scripts

### 1. Generate Fake Metrics Data

```bash
python scripts/generate_fake_metrics.py
```

This script generates 20 years of fake historical metrics data for each agency and document in the system. It creates one metrics record per year (from 2003 to 2023) for each document, with realistic trending values over time.

Features:
- Generates metrics with realistic trends (documents tend to get longer and more complex over time)
- Adds random volatility to make the data look natural
- Processes agencies and documents in batches to handle large datasets
- Skips agencies that already have metrics data

### 2. Clean Metrics Data

```bash
python scripts/clean_metrics_data.py
```

This script removes all historical metrics data from the database, allowing you to start fresh with real data. It will ask for confirmation before deleting any data.

### 3. Analyze Metrics Data

```bash
python scripts/analyze_metrics_data.py
```

This script analyzes the metrics data in the database and provides various statistics:
- Total number of metrics records
- Metrics count by year
- Top agencies by metrics count
- Average metrics values (word count, complexity, readability, etc.)
- Metrics trends over time
- Documents with the most metrics, highest complexity, and highest readability

## Usage Workflow

1. First, run the migration to create the metrics table:
   ```bash
   alembic upgrade head
   ```

2. Generate fake metrics data:
   ```bash
   python scripts/generate_fake_metrics.py
   ```

3. Analyze the generated data:
   ```bash
   python scripts/analyze_metrics_data.py
   ```

4. When you're ready to start with real data, clean the fake data:
   ```bash
   python scripts/clean_metrics_data.py
   ```

## Requirements

These scripts require the following Python packages:
- SQLAlchemy
- Faker
- pandas
- numpy
- matplotlib (for future visualization features)

Install them with:
```bash
pip install faker pandas numpy matplotlib
``` 