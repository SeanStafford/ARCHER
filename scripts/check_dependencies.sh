#!/bin/bash
# Check system dependencies for ARCHER
#
# Usage: check_dependencies.sh [DIRECTORY]
#
# This script recursively finds all dependencies.txt files in the specified directory
# and verifies that the listed Debian/Ubuntu packages are installed. Displays version
# information for each installed package.
#
# Arguments:
#   DIRECTORY - Path to search for dependencies.txt files (required)

# Check for required directory argument
if [ -z "$1" ]; then
    echo "ERROR: Directory argument required"
    echo "Usage: $0 DIRECTORY"
    exit 1
fi

SEARCH_DIR="$1"
EXCLUDE_DIRS="(__pycache__|\.git|\.pytest_cache|\.ruff_cache|node_modules)"

# Verify directory exists
if [ ! -d "$SEARCH_DIR" ]; then
    echo "ERROR: Directory not found: $SEARCH_DIR"
    exit 1
fi

echo "Checking dependencies for $SEARCH_DIR"
echo ""

# Find all dependencies.txt files recursively, excluding certain directories
dep_files=$(find "$SEARCH_DIR" -type f -name "dependencies.txt" | grep -vE "$EXCLUDE_DIRS" | sort)

if [ -z "$dep_files" ]; then
    echo "No dependencies.txt files found"
    exit 0
fi

all_missing=()

# Process each dependencies file
for dep_file in $dep_files; do
    # Get relative path for display
    rel_path="${dep_file#$SEARCH_DIR/}"
    echo "From: $rel_path"

    missing_packages=()
    readarray -t lines < "$dep_file"

    for package in "${lines[@]}"; do

        # Skip lines without content (assumes no trailing or leading spaces)
        case "$package" in
            \#*) continue ;; # Skip comments (lines starting with #)
            *[!\ ]*) ;;      # Line contains non-space characters - process it
            *) continue ;;   # Only spaces or empty - skip it
        esac

        # Check if package is installed via dpkg
        if dpkg -l "$package" 2>/dev/null | grep -q "^ii"; then
            # Extract version from dpkg -l output (3rd column)
            version=$(dpkg -l "$package" 2>/dev/null | grep "^ii" | awk '{print $3}')
            echo "  ✓ $package ($version)"
        else
            echo "  ✗ $package (NOT installed)"
            missing_packages+=("$package")
            all_missing+=("$package")
        fi
    done

    echo ""
done

# Report overall results
NUM_PACKAGES_MISSING=${#all_missing[@]}
if [ $NUM_PACKAGES_MISSING -eq 0 ]; then
    echo "✓ All dependencies satisfied"
    exit 0
else
    echo "✗ Missing $NUM_PACKAGES_MISSING package(s):"
    for package in "${all_missing[@]}"; do
        echo "   - $package"
    done
    echo ""
    echo "Install with:"
    echo "   sudo apt-get install ${all_missing[*]}"
    exit 1
fi
