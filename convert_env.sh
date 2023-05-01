#!/bin/bash

# Read each line of the .env file
while IFS= read -r line; do
  # Split the line into key and value
  IFS='=' read -r key value <<< "$line"
  
  # Format the key and value
  formatted_key="'$key'"
  formatted_value="'$value'"
  
  # Print the formatted pair
  printf "%s=%s " "$formatted_key" "$formatted_value"
done < .env