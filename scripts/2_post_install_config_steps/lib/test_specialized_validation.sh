#!/bin/bash

# Test script for specialized validation functions
# This demonstrates the new cleanse-at-input approach

# Source the common functions to get the specialized validation
SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/_common_.source.sh"

echo "Testing Specialized Parameter Validation Functions"
echo "=================================================="

# Test helper function
test_validation() {
    local func_name="$1"
    local param_name="$2"
    local test_value="$3"
    local expected_result="$4"  # "PASS" or "FAIL"
    
    echo ""
    echo "Testing: $func_name '$param_name' '$test_value'"
    echo "Expected: $expected_result"
    
    if result=$($func_name "$param_name" "$test_value" 2>/dev/null); then
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
echo "=== Testing validate_parameter_group ==="
test_validation "validate_parameter_group" "--group" "developers" "PASS"
test_validation "validate_parameter_group" "--group" "test-group" "PASS" 
test_validation "validate_parameter_group" "--group" "test_group" "PASS"
test_validation "validate_parameter_group" "--group" "test.group" "PASS"
test_validation "validate_parameter_group" "--group" "123group" "FAIL"  # Can't start with number
test_validation "validate_parameter_group" "--group" "group;rm" "FAIL"  # Shell metacharacter
test_validation "validate_parameter_group" "--group" "" "FAIL"           # Empty
test_validation "validate_parameter_group" "--group" "very-long-group-name-that-exceeds-thirty-two-characters" "FAIL"  # Too long

echo ""
echo "=== Testing validate_parameter_user ==="
test_validation "validate_parameter_user" "--user" "alice" "PASS"
test_validation "validate_parameter_user" "--user" "test-user" "PASS"
test_validation "validate_parameter_user" "--user" "test_user" "PASS" 
test_validation "validate_parameter_user" "--user" "test.user" "PASS"
test_validation "validate_parameter_user" "--user" "123user" "FAIL"      # Can't start with number
test_validation "validate_parameter_user" "--user" "user;evil" "FAIL"    # Shell metacharacter
test_validation "validate_parameter_user" "--user" "" "FAIL"             # Empty

echo ""
echo "=== Testing validate_parameter_numeric ==="
test_validation "validate_parameter_numeric" "--uid" "1000" "PASS"
test_validation "validate_parameter_numeric" "--uid" "0" "PASS"
test_validation "validate_parameter_numeric" "--uid" "65535" "PASS"
test_validation "validate_parameter_numeric" "--uid" "abc" "FAIL"        # Not numeric
test_validation "validate_parameter_numeric" "--uid" "-1" "FAIL"         # Negative
test_validation "validate_parameter_numeric" "--uid" "99999" "FAIL"      # Too large
test_validation "validate_parameter_numeric" "--uid" "" "FAIL"           # Empty

echo ""
echo "=== Testing validate_parameter_path ==="
test_validation "validate_parameter_path" "--home" "/home/alice" "PASS"
test_validation "validate_parameter_path" "--home" "/opt/app" "PASS"
test_validation "validate_parameter_path" "--home" "relative/path" "FAIL"    # Not absolute
test_validation "validate_parameter_path" "--home" "/home/../etc" "FAIL"     # Path traversal
test_validation "validate_parameter_path" "--home" "/home;rm" "FAIL"        # Shell metacharacter
test_validation "validate_parameter_path" "--home" "" "FAIL"                # Empty

echo ""
echo "=== Testing validate_parameter_shell ==="
test_validation "validate_parameter_shell" "--shell" "/bin/bash" "PASS"
test_validation "validate_parameter_shell" "--shell" "/bin/sh" "PASS"
test_validation "validate_parameter_shell" "--shell" "/sbin/nologin" "PASS"
test_validation "validate_parameter_shell" "--shell" "bash" "FAIL"          # Not absolute
test_validation "validate_parameter_shell" "--shell" "/bin/bash;rm" "FAIL"  # Shell metacharacter
test_validation "validate_parameter_shell" "--shell" "" "FAIL"              # Empty

echo ""
echo "=== Testing validate_parameter_password ==="
test_validation "validate_parameter_password" "--password" "SecurePass123" "PASS"
test_validation "validate_parameter_password" "--password" "simple" "PASS"
test_validation "validate_parameter_password" "--password" "" "FAIL"        # Empty
# Note: We don't test passwords with single quotes here as it would break the test

echo ""
echo "=== Testing Command Injection Prevention ==="
echo ""
echo "The following malicious inputs should all be REJECTED:"
test_validation "validate_parameter_user" "--user" "alice;rm -rf /" "FAIL"
test_validation "validate_parameter_group" "--group" "group\$(evil)" "FAIL"
test_validation "validate_parameter_path" "--path" "/home;cat /etc/passwd" "FAIL"
test_validation "validate_parameter_numeric" "--uid" "1000;evil" "FAIL"

echo ""
echo "=================================================="
echo "Specialized Validation Test Complete"
echo ""
echo "Key Benefits:"
echo "✅ Input validated immediately at parameter parsing"
echo "✅ Consistent error messages with help integration"
echo "✅ Format constraints clearly communicated to users"
echo "✅ Shell metacharacters and injection attempts blocked"
echo "✅ No need for redundant validation later in functions"