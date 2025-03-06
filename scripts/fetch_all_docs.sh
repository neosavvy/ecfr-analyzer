#!/bin/bash

if [[ "$1" != "odd" && "$1" != "even" ]]; then
  echo "Usage: $0 <odd|even>"
  exit 1
fi

for ((i=2019; i>=1990; i--)); do
  if [[ "$1" == "odd" && $((i % 2)) -eq 1 ]]; then
    ./scripts/fetch_all_agency_documents.sh --target-year $i
  elif [[ "$1" == "even" && $((i % 2)) -eq 0 ]]; then
    ./scripts/fetch_all_agency_documents.sh --target-year $i
  fi
done
