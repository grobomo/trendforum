#!/usr/bin/env bash
# Extract a CDT .zip or .tar.gz bundle into a working directory.
# Usage: extract_cdt.sh <cdt_archive> [output_dir]
#
# CDT bundles come as .zip files from the IMSVA admin UI.
# This script extracts them and validates the expected directory structure.

set -euo pipefail

ARCHIVE="${1:?Usage: extract_cdt.sh <cdt_archive> [output_dir]}"
OUTPUT_DIR="${2:-$(dirname "$ARCHIVE")/$(basename "$ARCHIVE" | sed 's/\.\(zip\|tar\.gz\|tgz\)$//')}"

if [[ ! -f "$ARCHIVE" ]]; then
    echo "Error: Archive not found: $ARCHIVE" >&2
    exit 1
fi

echo "Extracting CDT: $ARCHIVE → $OUTPUT_DIR" >&2
mkdir -p "$OUTPUT_DIR"

case "$ARCHIVE" in
    *.zip)
        unzip -o -q "$ARCHIVE" -d "$OUTPUT_DIR"
        ;;
    *.tar.gz|*.tgz)
        tar xzf "$ARCHIVE" -C "$OUTPUT_DIR"
        ;;
    *)
        echo "Error: Unsupported archive format. Expected .zip or .tar.gz" >&2
        exit 1
        ;;
esac

# Validate CDT structure
EXPECTED_DIRS=("IMSVA/LogFile/Event1" "IMSVA/LogFile/Event3" "IMSVA/LogFile/Event5")
CDT_ROOT="$OUTPUT_DIR"

# CDT might have a nested directory (e.g., CDT-YYYYMMDD-HHMMSS/)
if [[ ! -d "$CDT_ROOT/IMSVA" ]]; then
    # Check one level deep
    NESTED=$(find "$CDT_ROOT" -maxdepth 1 -type d -name "CDT-*" | head -1)
    if [[ -n "$NESTED" && -d "$NESTED/IMSVA" ]]; then
        CDT_ROOT="$NESTED"
    fi
fi

VALID=true
for dir in "${EXPECTED_DIRS[@]}"; do
    if [[ ! -d "$CDT_ROOT/$dir" ]]; then
        echo "Warning: Missing expected directory: $dir" >&2
        VALID=false
    fi
done

if $VALID; then
    echo "✅ CDT structure validated" >&2
else
    echo "⚠️  CDT structure incomplete — analysis may be partial" >&2
fi

echo "$CDT_ROOT"
