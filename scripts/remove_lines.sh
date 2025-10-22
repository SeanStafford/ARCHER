#!/usr/bin/env bash

# Exit immediately if a command exits with a non-zero status,
# if an undefined variable is used, or if any command in a pipeline fails
set -euo pipefail

# Assert that there are exactly 2 commandline arguments
if [ "$#" -ne 2 ]; then
  echo "Usage: $0 'pattern' /path/to/file" >&2
  exit 1
fi

# Grep pattern identifying lines to be removed
pattern="$1"
# Path to the target file
target_file="$2"

# Assert that the target file exists
if [ ! -f "$target_file" ]; then
  echo "Error: file '$target_file' not found" >&2
  exit 1
fi

# Creates unique temporary file
tmp_file="$(mktemp)"

# Force temp file removal upon any exit
trap 'rm -f "$tmp_file"' EXIT

# The command: "grep -v -E $pattern $target_file > $tmp_file"
# This grep command prints out all lines except those matching the pattern
# and stores the result in a temporary file

# A subshell runs the command and captures its exit status
status=$(grep -v -E "$pattern" "$target_file" > "$tmp_file"; echo "$?")

# Check the exit status of the command if it is not 0 or 1
# (Exit status 1 means no lines matched)
# If the exit status is not 0 or 1, exit with that status
if [ "$status" -gt 1 ]; then
  exit "$status"
fi

lines_before=$(awk 'END { print NR }' "$target_file")
lines_after=$(awk 'END { print NR }' "$tmp_file")
lines_removed=$((lines_before - lines_after))
echo "Removed $lines_removed lines matching pattern '$pattern' from '$target_file'."

# Replace the original file with the filtered temp file
mv -- "$tmp_file" "$target_file"