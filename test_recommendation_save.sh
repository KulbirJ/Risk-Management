#!/bin/bash
# Simple shell script to test recommendation save feature using curl

echo "=============================================="
echo "Recommendation Field Save Feature Test"
echo "=============================================="

# Configuration
BASE_URL="http://localhost:8000/api/v1"
TENANT_ID="00000000-0000-0000-0000-000000000001"  # Replace with actual tenant ID
USER_ID="00000000-0000-0000-0000-000000000001"    # Replace with actual user ID

# Check if IDs were provided as arguments
if [ $# -ge 1 ]; then
    TENANT_ID=$1
fi
if [ $# -ge 2 ]; then
    USER_ID=$2
fi
if [ $# -ge 3 ]; then
    ASSESSMENT_ID=$3
fi

echo ""
echo "Using:"
echo "  Tenant ID: $TENANT_ID"
echo "  User ID: $USER_ID"
echo ""

# Step 1: Create Assessment (if not provided)
if [ -z "$ASSESSMENT_ID" ]; then
    echo "Step 1: Creating Test Assessment..."
    echo "----------------------------------------------"
    
    ASSESSMENT_RESPONSE=$(curl -s -X POST "$BASE_URL/assessments/" \
        -H "X-Tenant-Id: $TENANT_ID" \
        -H "X-User-Id: $USER_ID" \
        -H "Content-Type: application/json" \
        -d '{
            "title": "Test Assessment for Recommendation",
            "description": "Testing recommendation save feature",
            "system_background": "Test system",
            "scope": "Testing",
            "tech_stack": ["Python", "FastAPI"],
            "overall_impact": "Medium"
        }')
    
    ASSESSMENT_ID=$(echo $ASSESSMENT_RESPONSE | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)
    echo "✓ Assessment created: $ASSESSMENT_ID"
    echo ""
fi

# Step 2: Create Threat
echo "Step 2: Creating Test Threat..."
echo "----------------------------------------------"

THREAT_RESPONSE=$(curl -s -X POST "$BASE_URL/threats/?assessment_id=$ASSESSMENT_ID" \
    -H "X-Tenant-Id: $TENANT_ID" \
    -H "X-User-Id: $USER_ID" \
    -H "Content-Type: application/json" \
    -d '{
        "title": "Test Threat for Recommendation",
        "description": "This is a test threat",
        "likelihood": "Medium",
        "impact": "High",
        "status": "identified"
    }')

THREAT_ID=$(echo $THREAT_RESPONSE | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)
echo "✓ Threat created: $THREAT_ID"
echo "Response: $THREAT_RESPONSE"
echo ""

# Step 3: Update Threat with Recommendation
echo "Step 3: Updating Threat with Recommendation..."
echo "----------------------------------------------"

RECOMMENDATION_TEXT="Implement multi-factor authentication and conduct regular security audits to mitigate this threat effectively."

UPDATE_RESPONSE=$(curl -s -X PATCH "$BASE_URL/threats/$THREAT_ID" \
    -H "X-Tenant-Id: $TENANT_ID" \
    -H "X-User-Id: $USER_ID" \
    -H "Content-Type: application/json" \
    -d "{
        \"title\": \"Test Threat (Updated)\",
        \"description\": \"Updated description\",
        \"recommendation\": \"$RECOMMENDATION_TEXT\",
        \"likelihood\": \"Medium\",
        \"impact\": \"High\"
    }")

echo "✓ Threat updated"
echo "Update Response:"
echo "$UPDATE_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$UPDATE_RESPONSE"
echo ""

# Step 4: Fetch and Verify
echo "Step 4: Fetching Threat to Verify Recommendation..."
echo "----------------------------------------------"

FETCH_RESPONSE=$(curl -s -X GET "$BASE_URL/threats/$THREAT_ID" \
    -H "X-Tenant-Id: $TENANT_ID" \
    -H "X-User-Id: $USER_ID")

echo "Fetched Threat:"
echo "$FETCH_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$FETCH_RESPONSE"
echo ""

# Check if recommendation is in the response
if echo "$FETCH_RESPONSE" | grep -q "recommendation"; then
    SAVED_RECOMMENDATION=$(echo "$FETCH_RESPONSE" | grep -o '"recommendation":"[^"]*"' | cut -d'"' -f4)
    echo "=============================================="
    echo "✓ SUCCESS: Recommendation field found!"
    echo "=============================================="
    echo "Saved Recommendation: $SAVED_RECOMMENDATION"
    echo ""
    
    if [ "$SAVED_RECOMMENDATION" = "$RECOMMENDATION_TEXT" ]; then
        echo "✓ Recommendation matches expected value!"
    else
        echo "⚠ Warning: Recommendation value differs from expected"
    fi
else
    echo "=============================================="
    echo "✗ FAILED: Recommendation field not found!"
    echo "=============================================="
fi

echo ""
echo "Test Data Created:"
echo "  Assessment ID: $ASSESSMENT_ID"
echo "  Threat ID: $THREAT_ID"
echo ""
echo "To clean up, run:"
echo "  curl -X DELETE \"$BASE_URL/threats/$THREAT_ID\" -H \"X-Tenant-Id: $TENANT_ID\" -H \"X-User-Id: $USER_ID\""
echo "  curl -X DELETE \"$BASE_URL/assessments/$ASSESSMENT_ID\" -H \"X-Tenant-Id: $TENANT_ID\" -H \"X-User-Id: $USER_ID\""
