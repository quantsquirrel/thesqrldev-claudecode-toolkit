#!/usr/bin/env bash

# Handoff Markdown Validation Script
# Validates quality of handoff documentation

set -euo pipefail

# Colors (compatible with macOS and Linux)
if [[ -t 1 ]]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    BLUE='\033[0;34m'
    BOLD='\033[1m'
    NC='\033[0m' # No Color
else
    RED=''
    GREEN=''
    YELLOW=''
    BLUE=''
    BOLD=''
    NC=''
fi

# Usage
usage() {
    echo "Usage: $0 <handoff-file.md>"
    echo ""
    echo "Validates handoff markdown file quality and calculates a score (0-100)."
    echo ""
    echo "Checks:"
    echo "  - No incomplete [TODO: ...] placeholders (+20)"
    echo "  - No secrets detected (+20)"
    echo "  - All required sections present (+20)"
    echo "  - Referenced files exist (+20)"
    echo "  - Next Steps has at least 2 items (+20)"
    echo ""
    echo "Exit codes:"
    echo "  0 - PASS (score >= 70)"
    echo "  1 - FAIL (score < 70)"
    echo "  2 - Invalid usage"
    exit 2
}

# Check arguments
if [[ $# -ne 1 ]]; then
    usage
fi

HANDOFF_FILE="$1"

# Check file exists
if [[ ! -f "$HANDOFF_FILE" ]]; then
    echo -e "${RED}Error: File not found: $HANDOFF_FILE${NC}"
    exit 2
fi

# Initialize
SCORE=0
ISSUES=()

echo -e "${BOLD}Validating: $HANDOFF_FILE${NC}"
echo ""

# Get the directory containing the handoff file for relative path resolution
HANDOFF_DIR="$(cd "$(dirname "$HANDOFF_FILE")" && pwd)"

# Check 1: No TODO placeholders (+20)
echo -n "Checking for incomplete TODOs... "
if grep -q '\[TODO:' "$HANDOFF_FILE"; then
    echo -e "${RED}FAIL${NC}"
    ISSUES+=("Found incomplete [TODO: ...] placeholders")
else
    echo -e "${GREEN}PASS${NC}"
    ((SCORE += 20))
fi

# Check 2: No secrets (+20)
echo -n "Checking for secrets... "
SECRET_PATTERNS=(
    'API[_-]?KEY'
    'SECRET'
    'PASSWORD'
    'TOKEN'
    'PRIVATE[_-]?KEY'
    'Bearer [a-zA-Z0-9_-]+'
    '[a-zA-Z0-9_-]{32,}'
)

SECRETS_FOUND=false
for pattern in "${SECRET_PATTERNS[@]}"; do
    if grep -iE "$pattern" "$HANDOFF_FILE" | grep -v '^\s*#' | grep -q .; then
        SECRETS_FOUND=true
        break
    fi
done

if $SECRETS_FOUND; then
    echo -e "${RED}FAIL${NC}"
    ISSUES+=("Potential secrets detected (API_KEY, SECRET, PASSWORD, TOKEN, PRIVATE_KEY patterns)")
else
    echo -e "${GREEN}PASS${NC}"
    ((SCORE += 20))
fi

# Check 3: Required sections present (+20)
echo -n "Checking required sections... "
REQUIRED_SECTIONS=("Summary" "Completed" "Pending" "Next Step")
MISSING_SECTIONS=()

for section in "${REQUIRED_SECTIONS[@]}"; do
    if ! grep -q "^#.*$section" "$HANDOFF_FILE"; then
        MISSING_SECTIONS+=("$section")
    fi
done

if [[ ${#MISSING_SECTIONS[@]} -gt 0 ]]; then
    echo -e "${RED}FAIL${NC}"
    ISSUES+=("Missing required sections: ${MISSING_SECTIONS[*]}")
else
    echo -e "${GREEN}PASS${NC}"
    ((SCORE += 20))
fi

# Check 4: Referenced files exist (+20)
echo -n "Checking referenced files... "
MISSING_FILES=()

# Extract file paths from "Files Modified" or similar sections
# Look for markdown list items that look like file paths
while IFS= read -r line; do
    # Remove leading/trailing whitespace and list markers
    file_path=$(echo "$line" | sed -E 's/^[[:space:]]*[-*+][[:space:]]*`?//; s/`.*$//; s/[[:space:]]*$//')

    # Skip empty lines or lines that don't look like file paths
    if [[ -z "$file_path" ]] || [[ ! "$file_path" =~ ^[/.] ]]; then
        continue
    fi

    # Resolve relative paths
    if [[ "$file_path" =~ ^\. ]]; then
        # Relative path - check from handoff directory
        full_path="$HANDOFF_DIR/$file_path"
    else
        # Absolute path
        full_path="$file_path"
    fi

    # Check if file exists
    if [[ ! -e "$full_path" ]]; then
        MISSING_FILES+=("$file_path")
    fi
done < <(sed -n '/^##[^#].*Files Modified/,/^##[^#]/p' "$HANDOFF_FILE" | grep -E '^[[:space:]]*[-*+][[:space:]]')

if [[ ${#MISSING_FILES[@]} -gt 0 ]]; then
    echo -e "${YELLOW}WARNING${NC}"
    ISSUES+=("Referenced files not found: ${MISSING_FILES[*]}")
    # Give partial credit if only some files are missing
    if [[ ${#MISSING_FILES[@]} -le 2 ]]; then
        ((SCORE += 10))
    fi
else
    echo -e "${GREEN}PASS${NC}"
    ((SCORE += 20))
fi

# Check 5: Next Steps has at least 2 items (+20)
echo -n "Checking Next Steps... "
NEXT_STEPS_COUNT=$(sed -n '/^##[^#].*Next Step/,/^##[^#]/p' "$HANDOFF_FILE" | grep -c '^[[:space:]]*[-*+][[:space:]]' || true)

if [[ $NEXT_STEPS_COUNT -lt 2 ]]; then
    echo -e "${RED}FAIL${NC}"
    ISSUES+=("Next Steps section has fewer than 2 items (found: $NEXT_STEPS_COUNT)")
else
    echo -e "${GREEN}PASS${NC}"
    ((SCORE += 20))
fi

# Summary
echo ""
echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

if [[ ${#ISSUES[@]} -gt 0 ]]; then
    echo -e "${BOLD}Issues Found:${NC}"
    for issue in "${ISSUES[@]}"; do
        echo -e "  ${YELLOW}•${NC} $issue"
    done
    echo ""
fi

echo -e "${BOLD}Quality Score: ${BLUE}$SCORE${NC}${BOLD}/100${NC}"
echo ""

if [[ $SCORE -ge 70 ]]; then
    echo -e "${GREEN}${BOLD}✓ PASS${NC}"
    exit 0
else
    echo -e "${RED}${BOLD}✗ FAIL${NC} (minimum score: 70)"
    exit 1
fi
