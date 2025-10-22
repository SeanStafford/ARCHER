#!/usr/bin/env bash

# Exit immediately on errors and treat unset variables as failures
set -euo pipefail

# Path to the single-file removal helper script
remove_script=~/ARCHER/scripts/remove_lines.sh

# Assert helper script is found and is executable
if [ ! -x "$remove_script" ]; then
  echo "Error: '$remove_script' not found or not executable" >&2
  exit 1
fi

# Assert a pattern and at least one file are provided
if [ "$#" -lt 2 ]; then
  echo "Usage: $0 'pattern' file1 [file2 ...]" >&2
  exit 1
fi

# Grep pattern identifying lines to be removed across files
pattern="$1"
shift

# Accumulate lines removed across all target files
total_removed=0

# Invoke single-file remover for each provided path, summing results
for target_file in "$@"; do
  output="$("$remove_script" "$pattern" "$target_file")"
  echo "$output"
  # Extract from output of one execution of the single-file script, the number of lines removed
  count=$(printf '%s\n' "$output" | sed -n 's/Removed \([0-9][0-9]*\) lines.*/\1/p')
  if [ -z "$count" ]; then
    count=0
  fi

  # Add to total removed count
  total_removed=$(($total_removed + $count))
done

# Report total deletions across all files
echo "Removed $total_removed lines in total."
