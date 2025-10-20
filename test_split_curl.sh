#!/bin/bash

# Quick curl test for Azure Function split endpoints
# Usage: ./test_split_curl.sh

# Configuration - UPDATE THESE VALUES

# PROD
#BASE_URL="https://<your-azure-function-api>.azurewebsites.net/api"
# DEV
#BASE_URL="https://<your-azure-function-api-dev>.azurewebsites.net/api"
# Local
BASE_URL="http://localhost:7071/api"

TEST_FILE_URL="https://docs.google.com/spreadsheets/d/1b_h7Wkd1y1-sNjkeR4izCowbRqLpeIS0FYm/edit?usp=sharing"

# Same key for entire function (host key level authentication)
CREATE_CHART_ID_API_KEY="Your-Azure-Function-Key"  # Replace with actual key for create_chart_id endpoint
UPDATE_CHART_API_KEY="Your-Azure-Function-Key"        # Replace with actual key for update_chart endpoint

echo "🧪 Testing Azure Function Split Endpoints with curl..."
echo "Base URL: $BASE_URL"
echo "File URL: $TEST_FILE_URL"
echo ""

# Step 1: Create chart ID and upload data
echo "📊 STEP 1: Creating chart ID and uploading data..."

# Prepare Step 1 data
CREATE_CHART_ID_DATA=$(cat <<EOF
{
  "file_url": "$TEST_FILE_URL",
  "chart_type": "d3-bars",
  "title": "Test Chart - Split Endpoints"
}
EOF
)

echo "📤 Sending Step 1 request..."
# Capture both the response body and the HTTP status separately
STEP1_RESPONSE=$(curl -s -X POST "$BASE_URL/create_chart_id?code=$CREATE_CHART_ID_API_KEY" \
  -H "Content-Type: application/json" \
  -d "$CREATE_CHART_ID_DATA" \
  -w "\nHTTP_STATUS:%{http_code}\nTOTAL_TIME:%{time_total}s" \
  -v 2>&1)

echo "$STEP1_RESPONSE"

# Extract chart_id from Step 1 response - look for JSON in the response
CHART_ID=""
# First try to find JSON response in the verbose output
JSON_RESPONSE=$(echo "$STEP1_RESPONSE" | grep -E '^{.*}$' | tail -1)

if [ -n "$JSON_RESPONSE" ]; then
    if command -v jq &> /dev/null; then
        CHART_ID=$(echo "$JSON_RESPONSE" | jq -r '.chart_id' 2>/dev/null)
    else
        CHART_ID=$(echo "$JSON_RESPONSE" | grep -o '"chart_id":"[^"]*"' | cut -d'"' -f4)
    fi
fi

# If still no chart_id, try alternative extraction methods
if [ -z "$CHART_ID" ] || [ "$CHART_ID" = "null" ]; then
    # Try to extract from the entire response
    CHART_ID=$(echo "$STEP1_RESPONSE" | grep -o '"chart_id": *"[^"]*"' | sed 's/.*: *"\([^"]*\)"/\1/')
   # CHART_ID=$(echo "$STEP1_RESPONSE" | grep -o '"chart_id":"[^"]*"' | cut -d'"' -f4 | head -1)
fi

if [ -z "$CHART_ID" ] || [ "$CHART_ID" = "null" ]; then
    echo "❌ Error: Could not extract chart_id from Step 1 response"
    echo "🔍 Debug: Full response was:"
    echo "$STEP1_RESPONSE"
    exit 1
fi

echo ""
echo "⏳ Waiting 2 seconds before Step 2..."
sleep 2

# Step 2: Update chart metadata and publish
echo ""
echo "📝 STEP 2: Updating chart metadata and publishing..."

echo "📋 Using chart_id: $CHART_ID"

# Prepare Step 2 data
UPDATE_CHART_DATA=$(cat <<EOF
{
  "chart_id": "$CHART_ID",
  "intro": "This is a test chart created using the split endpoints approach.",
  "byline": "Test Data",
  "source_name": "Test Source",
  "source_url": "https://example.com",
  "custom_colors": ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd"]
}
EOF
)

echo "📤 Sending Step 2 request..."
# Capture both the response body and the HTTP status separately
STEP2_RESPONSE=$(curl -s -X POST "$BASE_URL/update_chart?code=$UPDATE_CHART_API_KEY" \
  -H "Content-Type: application/json" \
  -d "$UPDATE_CHART_DATA" \
  -w "\nHTTP_STATUS:%{http_code}\nTOTAL_TIME:%{time_total}s" \
  -v 2>&1)

echo "$STEP2_RESPONSE"

# Extract chart_url from Step 2 response - look for JSON in the response
CHART_URL=""
# First try to find JSON response in the verbose output
JSON_RESPONSE=$(echo "$STEP2_RESPONSE" | grep -E '^{.*}$' | tail -1)

if [ -n "$JSON_RESPONSE" ]; then
    if command -v jq &> /dev/null; then
        CHART_URL=$(echo "$JSON_RESPONSE" | jq -r '.chart_url' 2>/dev/null)
    else
        CHART_URL=$(echo "$JSON_RESPONSE" | grep -o '"chart_url":"[^"]*"' | cut -d'"' -f4)
    fi
fi

# If still no chart_url, try alternative extraction methods
if [ -z "$CHART_URL" ] || [ "$CHART_URL" = "null" ]; then
    # Try to extract from the entire response
    CHART_URL=$(echo "$STEP2_RESPONSE" | grep -o '"chart_url": *"[^"]*"' | cut -d'"' -f4)
#    CHART_URL=$(echo "$STEP2_RESPONSE" | grep -o '"chart_url":"[^"]*"' | cut -d'"' -f4 | head -1)
fi

echo ""
echo "✅ Curl test completed!"

# Display results prominently
echo ""
echo "🎯 RESULTS:"
echo "  Chart ID: $CHART_ID"
if [ -n "$CHART_URL" ] && [ "$CHART_URL" != "null" ]; then
    echo "  Chart URL: $CHART_URL"
    echo ""
    echo "🔗 Open your chart: $CHART_URL"
else
    echo "  Chart URL: Could not extract from response"
fi

echo ""
echo "📝 Expected responses:"
echo "  Step 1: 200 - Success with chart_id"
echo "  Step 2: 200 - Success with chart_url"
echo "  - 400: Bad request (missing fields, invalid URL)"
echo "  - 401: Unauthorized (invalid function key)"
echo "  - 500: Server error (check Azure Function logs)" 