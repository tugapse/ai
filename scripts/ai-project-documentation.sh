#!/bin/bash

# Function to sanitize a path to prevent directory traversal and invalid characters
sanitize_path() {
    local input="$1"
    # Remove any characters that are not alphanumeric, underscores, or slashes
    local sanitized=$(echo "$input" | sed 's/[^a-zA-Z0-9_\/]//g')
    # Ensure it's an absolute path
    if [[ "$sanitized" != /* ]]; then
        sanitized="/$sanitized"
    fi
    echo "$sanitized"
}

# Function to create project documentation with recursive file filtering
ai-create-project-doc() {
    local source_directory="$1"
    local destination_directory="$2"
    local file_extension="$3"

    # Check if the source directory exists
    if [ ! -d "$source_directory" ]; then
        echo "Source directory $source_directory does not exist."
        return 1
    fi

    # Check if the destination directory exists, if not, exit
    if [ ! -d "$destination_directory" ]; then
        echo "Destination directory $destination_directory does not exist. Exiting..."
        exit 1
    fi

    # Find all files recursively with the specified extension
    find "$source_directory" -type f -name "*.$file_extension" | while read -r file; do
        # Extract the relative path from the source file
        relative_path="${file#$source_directory/}"
        # Construct the destination file path
        destination_file="$destination_directory/$relative_path"
        # Echo the file path for processing (instead of copying)
        echo "Processing $file -> $destination_file"
        sleep 1
    done
}

# Main execution entry point
if [ $# -ne 3 ]; then
    echo "Usage: ai-create-project-doc <source_directory> <destination_directory> <file_extension>"
    exit 1
fi

source_directory="$1"
destination_directory="$2"
file_extension="$3"

# Sanitize the destination directory to prevent directory traversal and invalid characters
sanitized_dest=$(sanitize_path "$destination_directory")

# Validate the sanitized path
if [[ -z "$sanitized_dest" || ! "$sanitized_dest" =~ ^/ ]]; then
    echo "Invalid or empty destination directory: $destination_directory"
    exit 1
fi

# Resolve source directory to absolute path
resolved_source=$(cd "$source_directory" && pwd 2>/dev/null)
if [ -z "$resolved_source" ]; then
    echo "Invalid source directory: $source_directory"
    exit 1
fi

# Call the main function with the resolved source directory and sanitized destination
ai-create-project-doc "$resolved_source" "$sanitized_dest" "$file_extension"