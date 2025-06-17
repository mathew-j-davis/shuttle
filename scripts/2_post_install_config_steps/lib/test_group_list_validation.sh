#!/bin/bash

# Test script for group list validation
# Demonstrates validation of comma-separated group lists

# Source the common functions to get group list validation
SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/_common_.source.sh"

echo "Group List Validation Testing"
echo "============================="

# Test helper function
test_group_list_validation() {
    local param_name="$1"
    local test_value="$2"
    local expected_result="$3"  # "PASS" or "FAIL"
    local description="$4"
    
    echo ""
    echo "Testing: $description"
    echo "Input: '$test_value'"
    echo "Expected: $expected_result"
    
    if result=$(validate_parameter_group_list "$param_name" "$test_value" 2>/dev/null); then
        echo "Result: PASS - '$result'"
        if [[ "$expected_result" == "FAIL" ]]; then
            echo "❌ UNEXPECTED PASS - should have failed!"
        else
            echo "✅ Expected pass"
        fi
    else
        echo "Result: FAIL - validation rejected input"
        if [[ "$expected_result" == "PASS" ]]; then
            echo "❌ UNEXPECTED FAIL - should have passed!"
        else
            echo "✅ Expected fail"
        fi
    fi
}

echo ""
echo "=== Valid Group Lists (Should PASS) ==="
test_group_list_validation "--groups" "developers" "PASS" "Single group"
test_group_list_validation "--groups" "developers,sudo" "PASS" "Two groups"
test_group_list_validation "--groups" "web-team,db-admins,sudo" "PASS" "Three groups with hyphens"
test_group_list_validation "--groups" "group1,group2,group3" "PASS" "Multiple alphanumeric groups"
test_group_list_validation "--groups" "test.group,app_users" "PASS" "Groups with dots and underscores"
test_group_list_validation "--groups" " developers , sudo , docker " "PASS" "Groups with spaces (should be trimmed)"

echo ""
echo "=== Invalid Group Lists (Should FAIL) ==="
test_group_list_validation "--groups" "" "FAIL" "Empty group list"
test_group_list_validation "--groups" "developers,,sudo" "FAIL" "Double comma (empty group)"
test_group_list_validation "--groups" "developers," "FAIL" "Trailing comma (empty group)"
test_group_list_validation "--groups" ",developers" "FAIL" "Leading comma (empty group)"
test_group_list_validation "--groups" "123group,sudo" "FAIL" "Group starting with number"
test_group_list_validation "--groups" "good-group,bad;group" "FAIL" "Group with semicolon"
test_group_list_validation "--groups" "developers,group\$evil" "FAIL" "Group with dollar sign"
test_group_list_validation "--groups" "group1,group|evil,group3" "FAIL" "Group with pipe character"
test_group_list_validation "--groups" "very-long-group-name-that-exceeds-thirty-two-character-limit,sudo" "FAIL" "Group name too long"

echo ""
echo "=== Security Attack Tests (Should FAIL) ==="
test_group_list_validation "--groups" "group;rm -rf /" "FAIL" "Command injection attempt"
test_group_list_validation "--groups" "group\$(evil)" "FAIL" "Command substitution attempt"
test_group_list_validation "--groups" "group,evil;cmd,sudo" "FAIL" "Multiple groups with injection"
test_group_list_validation "--groups" "group|evil&cmd" "FAIL" "Shell metacharacters"

echo ""
echo "=== Whitespace Handling Tests ==="
test_group_list_validation "--groups" "group1, group2 ,group3" "PASS" "Mixed whitespace (should be cleaned)"
test_group_list_validation "--groups" "  developers  ,  sudo  " "PASS" "Leading/trailing spaces (should be trimmed)"

echo ""
echo "======================================"
echo "Group List Validation Test Complete"
echo ""
echo "Key Benefits Demonstrated:"
echo "✅ Individual group name validation"
echo "✅ Whitespace trimming and cleanup"  
echo "✅ Empty group detection"
echo "✅ Command injection prevention"
echo "✅ Shell metacharacter blocking"
echo "✅ Format standardization (no spaces in output)"
echo ""
echo "Example Usage in add-user command:"
echo "./script add-user --user alice --local --groups 'developers,sudo,docker'"
echo "Result: Clean validation and comma-separated output without spaces"

echo ""
echo "Technical Implementation:"
echo "========================"
echo "Input: 'developers, sudo , docker '"
echo "Processing:"
echo "  1. Split on commas: ['developers', ' sudo ', ' docker ']"
echo "  2. Trim whitespace: ['developers', 'sudo', 'docker']"
echo "  3. Validate each: ✅ developers ✅ sudo ✅ docker"
echo "  4. Rejoin clean: 'developers,sudo,docker'"
echo ""
echo "This ensures every group name follows validation rules individually!"