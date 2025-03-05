#!/bin/bash

# Script to fetch documents for all agencies
# This script will:
# 1. Get a list of all agency slugs from the API
# 2. For each agency, generate and execute a curl command to fetch and process documents
# 3. Support resuming from where it left off if interrupted

# Configuration
API_HOST="http://localhost:8000"
PER_PAGE=20
RESET=false
PROCESS_ALL=true
DELAY_BETWEEN_REQUESTS=5  # Seconds to wait between requests to avoid overwhelming the server

# Resume functionality
PROGRESS_FILE="agency_fetch_progress.txt"
SUMMARY_LOG="agency_fetch_summary.log"  # Persistent log showing all agencies and their status
RESUME=false
START_FROM=""

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --resume)
      RESUME=true
      shift
      ;;
    --start-from)
      START_FROM="$2"
      shift 2
      ;;
    *)
      echo "Unknown option: $1"
      echo "Usage: $0 [--resume] [--start-from AGENCY_SLUG]"
      exit 1
      ;;
  esac
done

# Create a log file with timestamp
LOG_FILE="agency_document_fetch_$(date +%Y%m%d_%H%M%S).log"
echo "Starting document fetch for all agencies at $(date)" > $LOG_FILE
echo "Configuration: PER_PAGE=$PER_PAGE, RESET=$RESET, PROCESS_ALL=$PROCESS_ALL" >> $LOG_FILE

# Initialize or append to summary log
if [ ! -f "$SUMMARY_LOG" ] || [ "$RESUME" = false -a -z "$START_FROM" ]; then
    echo "=== AGENCY FETCH SUMMARY (Started: $(date)) ===" > $SUMMARY_LOG
    echo "FORMAT: [POSITION/TOTAL] AGENCY_SLUG - STATUS (DOCUMENTS)" >> $SUMMARY_LOG
    echo "------------------------------------------------------" >> $SUMMARY_LOG
fi

# Step 1: Get all agency slugs
echo "Fetching list of all agencies..."
AGENCIES_RESPONSE=$(curl -s -X 'GET' "$API_HOST/api/agencies/" -H 'accept: application/json')

# Check if the request was successful
if [ $? -ne 0 ]; then
    echo "Failed to fetch agencies. Please check if the API server is running." | tee -a $LOG_FILE
    exit 1
fi

# Extract agency slugs from the response
# This assumes the response is a JSON array of agency objects with a 'slug' field
AGENCY_SLUGS=$(echo $AGENCIES_RESPONSE | jq -r '.[].slug')

# Check if we got any agency slugs
if [ -z "$AGENCY_SLUGS" ]; then
    echo "No agency slugs found in the response. Please check the API response format." | tee -a $LOG_FILE
    echo "Response was: $AGENCIES_RESPONSE" | tee -a $LOG_FILE
    exit 1
fi

# Count the number of agencies
AGENCY_COUNT=$(echo "$AGENCY_SLUGS" | wc -l)
echo "Found $AGENCY_COUNT agencies to process" | tee -a $LOG_FILE

# Handle resume functionality
SKIP_UNTIL_FOUND=false
if [ "$RESUME" = true ] && [ -f "$PROGRESS_FILE" ]; then
    LAST_PROCESSED=$(cat "$PROGRESS_FILE")
    echo "Resuming from last processed agency: $LAST_PROCESSED" | tee -a $LOG_FILE $SUMMARY_LOG
    SKIP_UNTIL_FOUND=true
    START_FROM="$LAST_PROCESSED"
elif [ ! -z "$START_FROM" ]; then
    echo "Starting from specified agency: $START_FROM" | tee -a $LOG_FILE $SUMMARY_LOG
    SKIP_UNTIL_FOUND=true
fi

# Add a clear separator in the logs
echo "======== BEGINNING AGENCY PROCESSING ========" | tee -a $LOG_FILE $SUMMARY_LOG

# Step 2: For each agency, fetch and process documents
COUNTER=0
PROCESSED=0
for SLUG in $AGENCY_SLUGS; do
    COUNTER=$((COUNTER + 1))
    
    # Format the position counter with leading zeros for better readability
    POSITION=$(printf "%03d/%03d" $COUNTER $AGENCY_COUNT)
    
    # Skip agencies until we find the one to resume from
    if [ "$SKIP_UNTIL_FOUND" = true ]; then
        if [ "$SLUG" = "$START_FROM" ]; then
            SKIP_UNTIL_FOUND=false
            echo "[$POSITION] Found resume point at agency: $SLUG" | tee -a $LOG_FILE $SUMMARY_LOG
        else
            echo "[$POSITION] SKIPPED: $SLUG (already processed)" >> $LOG_FILE
            echo "[$POSITION] $SLUG - SKIPPED (already processed)" >> $SUMMARY_LOG
            continue
        fi
    fi
    
    PROCESSED=$((PROCESSED + 1))
    
    # Clear, highly visible log entry for each agency
    echo "" | tee -a $LOG_FILE
    echo "================================================================" | tee -a $LOG_FILE
    echo "[$POSITION] PROCESSING AGENCY: $SLUG" | tee -a $LOG_FILE
    echo "================================================================" | tee -a $LOG_FILE
    
    # Save current progress to allow resuming if interrupted
    echo "$SLUG" > "$PROGRESS_FILE"
    
    # Generate and execute the curl command
    CURL_CMD="curl -X 'GET' '$API_HOST/api/agencies/$SLUG/documents?per_page=$PER_PAGE&reset=$RESET&process_all=$PROCESS_ALL' -H 'accept: application/json'"
    
    echo "Executing: $CURL_CMD" >> $LOG_FILE
    
    # Execute the curl command and capture the response
    RESPONSE=$(eval $CURL_CMD)
    CURL_EXIT_CODE=$?
    
    # Log the response status
    if [ $CURL_EXIT_CODE -eq 0 ]; then
        # Try to extract some meaningful information from the response
        DOCUMENT_COUNT=$(echo $RESPONSE | jq -r '.total_documents // "unknown"')
        echo "  Success! Documents found: $DOCUMENT_COUNT" | tee -a $LOG_FILE
        
        # Add to summary log with SUCCESS status
        echo "[$POSITION] $SLUG - SUCCESS ($DOCUMENT_COUNT documents)" | tee -a $SUMMARY_LOG
    else
        echo "  Failed to fetch documents for $SLUG (exit code: $CURL_EXIT_CODE)" | tee -a $LOG_FILE
        echo "  Response: $RESPONSE" >> $LOG_FILE
        
        # Add to summary log with FAILED status
        echo "[$POSITION] $SLUG - FAILED (exit code: $CURL_EXIT_CODE) - RESUME POINT" | tee -a $SUMMARY_LOG
        
        # Optional: Exit on failure to allow manual intervention
        # Uncomment the next line if you want the script to stop on any failure
        # echo "Exiting due to failure. Run with --resume to continue from this point." | tee -a $LOG_FILE; exit 1
    fi
    
    # Wait before the next request to avoid overwhelming the server
    if [ $COUNTER -lt $AGENCY_COUNT ]; then
        echo "  Waiting $DELAY_BETWEEN_REQUESTS seconds before next request..." | tee -a $LOG_FILE
        sleep $DELAY_BETWEEN_REQUESTS
    fi
done

# Add completion marker to summary log
echo "======== COMPLETED AGENCY PROCESSING at $(date) ========" | tee -a $LOG_FILE $SUMMARY_LOG

# Clean up progress file when complete
if [ -f "$PROGRESS_FILE" ]; then
    rm "$PROGRESS_FILE"
    echo "Removed progress file as all agencies have been processed" | tee -a $LOG_FILE
fi

echo "Completed processing all agencies at $(date)" | tee -a $LOG_FILE
echo "Processed $PROCESSED agencies out of $AGENCY_COUNT total" | tee -a $LOG_FILE
echo "See $LOG_FILE for detailed logs"
echo "See $SUMMARY_LOG for a summary of all agency processing statuses"

# Print final instructions
echo ""
echo "=== IMPORTANT ==="
echo "If you need to resume this process later, run:"
echo "./$(basename "$0") --resume"
echo ""
echo "To check which agency to resume from, look at the summary log:"
echo "cat $SUMMARY_LOG | grep 'RESUME POINT'" 