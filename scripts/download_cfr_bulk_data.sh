#!/bin/bash

# Script to download and extract CFR bulk data files from 1996 to 2024
# Files will be saved in a 'bulk' directory organized by year
# Downloads in reverse chronological order (newest to oldest)

# Configuration
BASE_URL="https://www.govinfo.gov/bulkdata/CFR"
START_YEAR=2024  # Start with most recent year
END_YEAR=1996    # End with oldest year
BULK_DIR="bulk"
LOG_FILE="cfr_bulk_download_$(date +%Y%m%d_%H%M%S).log"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --start-year)
      START_YEAR="$2"
      shift 2
      ;;
    --end-year)
      END_YEAR="$2"
      shift 2
      ;;
    --bulk-dir)
      BULK_DIR="$2"
      shift 2
      ;;
    --force)
      FORCE_DOWNLOAD=true
      shift
      ;;
    *)
      echo "Unknown option: $1"
      echo "Usage: $0 [--start-year YEAR] [--end-year YEAR] [--bulk-dir DIR] [--force]"
      exit 1
      ;;
  esac
done

# Create log file
echo "Starting CFR bulk data download at $(date)" > $LOG_FILE
echo "Downloading data from $START_YEAR down to $END_YEAR (in reverse chronological order)" | tee -a $LOG_FILE

# Check if wget is installed
if ! command -v wget &> /dev/null; then
    echo "ERROR: wget is not installed. Please install wget and try again." | tee -a $LOG_FILE
    exit 1
fi

# Create bulk directory if it doesn't exist
if [ ! -d "$BULK_DIR" ]; then
    mkdir -p "$BULK_DIR"
    echo "Created directory: $BULK_DIR" | tee -a $LOG_FILE
fi

# Function to download and extract a single year
download_and_extract() {
    year=$1
    year_dir="$BULK_DIR/$year"
    zip_file="CFR-$year.zip"
    download_url="$BASE_URL/$year/$zip_file"
    
    echo "" | tee -a $LOG_FILE
    echo "================================================================" | tee -a $LOG_FILE
    echo "Processing year: $year" | tee -a $LOG_FILE
    echo "================================================================" | tee -a $LOG_FILE
    
    # Skip if directory already exists and has XML content (not just the directory or zip file)
    if [ "$FORCE_DOWNLOAD" != "true" ] && [ -d "$year_dir" ] && [ $(find "$year_dir" -name "*.xml" | wc -l) -gt 0 ]; then
        echo "SKIPPING: Year $year already downloaded and extracted (XML files found)" | tee -a $LOG_FILE
        return 0
    fi
    
    # Create year directory if it doesn't exist
    if [ ! -d "$year_dir" ]; then
        mkdir -p "$year_dir"
        echo "Created directory: $year_dir" | tee -a $LOG_FILE
    else
        echo "Directory $year_dir exists but contains no XML files or --force was specified" | tee -a $LOG_FILE
    fi
    
    # Download the zip file using wget with detailed progress display
    echo "Downloading $download_url..." | tee -a $LOG_FILE
    
    # Use wget with maximum verbosity for progress
    # --show-progress forces the progress bar even when not on a terminal
    # -v adds verbose output including server responses
    # --progress=bar:force:noscroll shows a detailed progress bar that doesn't scroll
    wget --show-progress --progress=bar:force:noscroll -v --tries=3 --continue -O "$year_dir/$zip_file" "$download_url" 2>&1 | tee -a $LOG_FILE
    
    WGET_EXIT_CODE=${PIPESTATUS[0]}  # Get wget's exit code, not tee's
    
    if [ $WGET_EXIT_CODE -eq 0 ]; then
        # Check if the file is a valid zip file (not an HTML error page)
        if file "$year_dir/$zip_file" | grep -q "Zip archive data"; then
            echo "Download successful: $zip_file" | tee -a $LOG_FILE
            
            # Get file size for reporting
            FILE_SIZE=$(du -h "$year_dir/$zip_file" | cut -f1)
            echo "File size: $FILE_SIZE" | tee -a $LOG_FILE
            
            # Extract the zip file with progress indication
            echo "Extracting $zip_file to $year_dir..." | tee -a $LOG_FILE
            
            # Count total files in zip for progress reporting
            TOTAL_FILES=$(unzip -l "$year_dir/$zip_file" | tail -n 1 | awk '{print $2}')
            echo "Total files to extract: $TOTAL_FILES" | tee -a $LOG_FILE
            
            # Use pv if available for progress bar during extraction
            if command -v pv &> /dev/null; then
                # Extract with progress bar
                unzip -o "$year_dir/$zip_file" -d "$year_dir" | pv -l -s $TOTAL_FILES > /dev/null
            else
                # Fall back to regular unzip with some output
                echo "For better extraction progress, install 'pv' utility"
                unzip -o "$year_dir/$zip_file" -d "$year_dir" | grep -v "inflating:" | grep -v "creating:" | tee -a $LOG_FILE
            fi
            
            UNZIP_EXIT_CODE=${PIPESTATUS[0]}
            
            if [ $UNZIP_EXIT_CODE -eq 0 ]; then
                # Count extracted files for verification
                XML_FILES=$(find "$year_dir" -name "*.xml" | wc -l)
                TOTAL_FILES=$(find "$year_dir" -type f | wc -l)
                echo "Extraction successful. Extracted $TOTAL_FILES files ($XML_FILES XML files)." | tee -a $LOG_FILE
                
                # Verify that XML files were actually extracted
                if [ $XML_FILES -eq 0 ]; then
                    echo "WARNING: No XML files were extracted. This might indicate a problem." | tee -a $LOG_FILE
                fi
                
                # Optionally remove the zip file after extraction to save space
                # Uncomment the next line if you want to delete the zip files
                # rm "$year_dir/$zip_file" && echo "Removed zip file to save space" | tee -a $LOG_FILE
                
                return 0
            else
                echo "ERROR: Failed to extract $zip_file" | tee -a $LOG_FILE
                return 1
            fi
        else
            echo "ERROR: Downloaded file is not a valid ZIP archive. Might be an error page." | tee -a $LOG_FILE
            return 1
        fi
    else
        echo "ERROR: Failed to download $zip_file (exit code: $WGET_EXIT_CODE)" | tee -a $LOG_FILE
        return 1
    fi
}

# Download and extract data for each year in REVERSE order (newest to oldest)
success_count=0
failure_count=0
skipped_count=0

# Create a sequence of years in descending order
years=$(seq $START_YEAR -1 $END_YEAR)

# Calculate total years for progress reporting
TOTAL_YEARS=$(echo "$years" | wc -w)
CURRENT_YEAR=0

for year in $years; do
    CURRENT_YEAR=$((CURRENT_YEAR + 1))
    echo "" | tee -a $LOG_FILE
    echo "PROGRESS: Processing year $CURRENT_YEAR of $TOTAL_YEARS ($year)" | tee -a $LOG_FILE
    
    download_and_extract $year
    result=$?
    
    if [ $result -eq 0 ]; then
        # Check if it was skipped or successful
        if grep -q "SKIPPING: Year $year" $LOG_FILE; then
            skipped_count=$((skipped_count + 1))
        else
            success_count=$((success_count + 1))
        fi
    else
        failure_count=$((failure_count + 1))
    fi
    
    # Calculate and display overall progress
    PERCENT_COMPLETE=$(( (CURRENT_YEAR * 100) / TOTAL_YEARS ))
    echo "OVERALL PROGRESS: $PERCENT_COMPLETE% complete ($CURRENT_YEAR/$TOTAL_YEARS years processed)" | tee -a $LOG_FILE
    
    # Add a small delay between downloads to be nice to the server
    if [ $year -gt $END_YEAR ]; then
        echo "Waiting 2 seconds before next download..." | tee -a $LOG_FILE
        sleep 2
    fi
done

# Print summary
echo "" | tee -a $LOG_FILE
echo "================================================================" | tee -a $LOG_FILE
echo "Download Summary" | tee -a $LOG_FILE
echo "================================================================" | tee -a $LOG_FILE
echo "Total years processed: $((START_YEAR - END_YEAR + 1))" | tee -a $LOG_FILE
echo "Successful downloads: $success_count" | tee -a $LOG_FILE
echo "Skipped (already downloaded): $skipped_count" | tee -a $LOG_FILE
echo "Failed downloads: $failure_count" | tee -a $LOG_FILE
echo "Completed at: $(date)" | tee -a $LOG_FILE
echo "See $LOG_FILE for detailed logs" | tee -a $LOG_FILE

# Print instructions for accessing the data
echo ""
echo "The CFR bulk data has been downloaded to the '$BULK_DIR' directory,"
echo "organized by year. Each year's data is in its own subdirectory."
echo ""
echo "To access a specific year's data, navigate to: $BULK_DIR/<YEAR>"
echo ""
echo "To continue downloading from where you left off, run:"
echo "$0 --start-year <LAST_FAILED_YEAR>"
echo ""
echo "If you need to force re-download of a year, use:"
echo "$0 --start-year <YEAR> --end-year <YEAR> --force" 