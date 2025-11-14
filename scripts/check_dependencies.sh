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
all_optional_missing=()

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

        # Detect if package is optional
        is_optional=false
        if [[ "$package" == *"# optional"* ]]; then
            is_optional=true
            # Extract package name by removing everything from # onwards
            package=$(echo "$package" | sed 's/\s*#.*$//')
        fi

        # Check if package is installed via dpkg
        if dpkg -l "$package" 2>/dev/null | grep -q "^ii"; then
            # Extract version from dpkg -l output (3rd column)
            version=$(dpkg -l "$package" 2>/dev/null | grep "^ii" | awk '{print $3}')
            echo "  ✓ $package ($version)"
        else
            # Different handling for optional vs required
            if [ "$is_optional" = true ]; then
                echo "  ℹ $package (NOT installed - optional)"
                all_optional_missing+=("$package")
            else
                echo "  ✗ $package (NOT installed)"
                missing_packages+=("$package")
                all_missing+=("$package")
            fi
        fi
    done

    echo ""
done

# Report overall results
NUM_REQUIRED_MISSING=${#all_missing[@]}
NUM_OPTIONAL_MISSING=${#all_optional_missing[@]}

if [ $NUM_REQUIRED_MISSING -eq 0 ]; then
    # Show "required" only if there are missing optional dependencies
    if [ $NUM_OPTIONAL_MISSING -gt 0 ]; then
        echo "✓ All required dependencies satisfied"
        echo ""
        echo "Optional packages available for install:"
        echo "   sudo apt-get install ${all_optional_missing[*]}"
    else
        echo "✓ All dependencies satisfied"
    fi

    exit 0
else
    echo "✗ Missing $NUM_REQUIRED_MISSING required package(s):"
    for package in "${all_missing[@]}"; do
        echo "   - $package"
    done
    echo ""
    echo "Install with:"
    echo "   sudo apt-get install ${all_missing[*]}"

    # Also mention optional packages if any are missing
    if [ $NUM_OPTIONAL_MISSING -gt 0 ]; then
        echo ""
        echo "Optional packages also available:"
        echo "   sudo apt-get install ${all_optional_missing[*]}"
    fi

    exit 1
fi
