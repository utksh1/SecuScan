#!/bin/bash

# SecuScan Backend Test Suite
# Tests all API endpoints and functionality

set -e

BASE_URL="${BASE_URL:-http://127.0.0.1:8000/api/v1}"
PASSED=0
FAILED=0

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "🧪 SecuScan Backend Test Suite"
echo "================================"
echo ""

# Helper functions
test_pass() {
    echo -e "${GREEN}✓${NC} $1"
    ((PASSED++))
}

test_fail() {
    echo -e "${RED}✗${NC} $1"
    ((FAILED++))
}

test_warn() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Test 1: Health Check
echo "Test 1: Health Check"
RESPONSE=$(curl -s "$BASE_URL/health")
if echo "$RESPONSE" | grep -q '"status":"operational"'; then
    test_pass "Health endpoint returns operational status"
else
    test_fail "Health endpoint failed"
    echo "Response: $RESPONSE"
fi
echo ""

# Test 2: Get Plugins List
echo "Test 2: Get Plugins List"
RESPONSE=$(curl -s "$BASE_URL/plugins")
if echo "$RESPONSE" | grep -q '"plugins"'; then
    PLUGIN_COUNT=$(echo "$RESPONSE" | grep -o '"id"' | wc -l)
    test_pass "Plugins endpoint returns $PLUGIN_COUNT plugins"
    
    # Check for expected plugins
    if echo "$RESPONSE" | grep -q '"http_inspector"'; then
        test_pass "HTTP Inspector plugin found"
    else
        test_fail "HTTP Inspector plugin missing"
    fi
    
    if echo "$RESPONSE" | grep -q '"nmap"'; then
        test_pass "Nmap plugin found"
    else
        test_fail "Nmap plugin missing"
    fi
else
    test_fail "Plugins endpoint failed"
fi
echo ""

# Test 3: Get Plugin Schema
echo "Test 3: Get Plugin Schema"
RESPONSE=$(curl -s "$BASE_URL/plugin/http_inspector/schema")
if echo "$RESPONSE" | grep -q '"fields"'; then
    test_pass "Plugin schema endpoint returns fields"
    
    if echo "$RESPONSE" | grep -q '"presets"'; then
        test_pass "Plugin schema includes presets"
    else
        test_fail "Plugin schema missing presets"
    fi
else
    test_fail "Plugin schema endpoint failed"
fi
echo ""

# Test 4: Get Presets
echo "Test 4: Get All Presets"
RESPONSE=$(curl -s "$BASE_URL/presets")
if echo "$RESPONSE" | grep -q '"presets"'; then
    PRESET_COUNT=$(echo "$RESPONSE" | grep -o '"id"' | wc -l | xargs)
    test_pass "Presets endpoint returns $PRESET_COUNT presets"
else
    test_fail "Presets endpoint failed"
fi
echo ""

# Test 5: Get Settings
echo "Test 5: Get Settings"
RESPONSE=$(curl -s "$BASE_URL/settings")
if echo "$RESPONSE" | grep -q '"version"'; then
    test_pass "Settings endpoint returns configuration"
    
    if echo "$RESPONSE" | grep -q '"safe_mode"'; then
        test_pass "Settings include safe_mode"
    else
        test_warn "Settings missing safe_mode"
    fi
else
    test_fail "Settings endpoint failed"
fi
echo ""

# Test 6: Create Task (HTTP Inspector)
echo "Test 6: Create Task"
RESPONSE=$(curl -s -X POST "$BASE_URL/task/start" \
  -H "Content-Type: application/json" \
  -d '{
    "plugin_id": "http_inspector",
    "preset": "quick",
    "inputs": {"url": "https://example.com"},
    "consent_granted": true
  }')

if echo "$RESPONSE" | grep -q '"task_id"'; then
    TASK_ID=$(echo "$RESPONSE" | grep -o '"task_id":"[^"]*' | cut -d'"' -f4)
    test_pass "Task created successfully: $TASK_ID"
    
    # Test 7: Get Task Status
    echo ""
    echo "Test 7: Get Task Status"
    sleep 1
    RESPONSE=$(curl -s "$BASE_URL/task/$TASK_ID/status")
    if echo "$RESPONSE" | grep -q '"status"'; then
        STATUS=$(echo "$RESPONSE" | grep -o '"status":"[^"]*' | cut -d'"' -f4)
        test_pass "Task status retrieved: $STATUS"
    else
        test_fail "Task status endpoint failed"
    fi
    
    # Test 8: Get Task Result
    echo ""
    echo "Test 8: Get Task Result"
    sleep 2
    RESPONSE=$(curl -s "$BASE_URL/task/$TASK_ID/result")
    if echo "$RESPONSE" | grep -q '"output"'; then
        test_pass "Task result retrieved"
    else
        test_warn "Task result may not be ready yet"
    fi
    
    # Test 9: Get Tasks List
    echo ""
    echo "Test 9: Get Tasks List"
    RESPONSE=$(curl -s "$BASE_URL/tasks")
    if echo "$RESPONSE" | grep -q '"tasks"'; then
        TASK_COUNT=$(echo "$RESPONSE" | grep -o '"task_id"' | wc -l | xargs)
        test_pass "Tasks list retrieved: $TASK_COUNT task(s)"
    else
        test_fail "Tasks list endpoint failed"
    fi
    
    # Test 10: Delete Task
    echo ""
    echo "Test 10: Delete Task"
    RESPONSE=$(curl -s -X DELETE "$BASE_URL/task/$TASK_ID")
    if echo "$RESPONSE" | grep -q '"message"' || echo "$RESPONSE" | grep -q '"detail"'; then
        test_pass "Task deletion endpoint responded"
    else
        test_fail "Task deletion endpoint failed"
    fi
else
    test_fail "Task creation failed"
    echo "Response: $RESPONSE"
fi
echo ""

# Test 11: Invalid Plugin ID
echo "Test 11: Error Handling - Invalid Plugin"
RESPONSE=$(curl -s -X POST "$BASE_URL/task/start" \
  -H "Content-Type: application/json" \
  -d '{
    "plugin_id": "invalid_plugin",
    "preset": "quick",
    "inputs": {},
    "consent_granted": true
  }')
if echo "$RESPONSE" | grep -q '"detail"'; then
    test_pass "Invalid plugin ID returns error"
else
    test_fail "Invalid plugin error handling failed"
fi
echo ""

# Test 12: Missing Consent
echo "Test 12: Error Handling - Missing Consent"
RESPONSE=$(curl -s -X POST "$BASE_URL/task/start" \
  -H "Content-Type: application/json" \
  -d '{
    "plugin_id": "http_inspector",
    "preset": "quick",
    "inputs": {"url": "https://example.com"},
    "consent_granted": false
  }')
if echo "$RESPONSE" | grep -q '"detail"'; then
    test_pass "Missing consent returns error"
else
    test_fail "Missing consent error handling failed"
fi
echo ""

# Summary
echo "================================"
echo "Test Summary"
echo "================================"
echo -e "Passed: ${GREEN}$PASSED${NC}"
echo -e "Failed: ${RED}$FAILED${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}✗ Some tests failed${NC}"
    exit 1
fi
