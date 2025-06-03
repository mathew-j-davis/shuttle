"""
Integration test for hierarchy logging using the TestShuttleWithValidator framework
"""

import os
import logging
import unittest
from test_shuttle_with_validator import TestShuttleWithValidator, TestParameters, ValidationResult


def validate_hierarchy_logging_in_debug(test_instance, params, result, context):
    """Validate that hierarchy logging appears in DEBUG mode"""
    
    # Find and read the log file
    log_files = [f for f in os.listdir(context['logs_dir']) 
                 if f.startswith('shuttle_') and f.endswith('.log')]
    
    if not log_files:
        return ValidationResult(False, "No shuttle log file found")
    
    # Read the most recent log file
    log_file_path = os.path.join(context['logs_dir'], sorted(log_files)[-1])
    with open(log_file_path, 'r') as f:
        log_contents = f.read()
    
    # Store log contents in context for debugging
    context['log_contents'] = log_contents
    context['log_file_path'] = log_file_path
    
    # Check for hierarchy logging markers
    if "[CALL STACK:" not in log_contents:
        # Print first few lines of log for debugging
        log_lines = log_contents.split('\n')[:10]
        return ValidationResult(
            False, 
            "Call stack not found in DEBUG logs",
            {
                'log_file': log_file_path,
                'first_lines': log_lines,
                'searched_for': '[CALL STACK:'
            }
        )
    
    # Count how many call stack entries we found
    call_stack_count = log_contents.count("[CALL STACK:")
    
    # Check for specific decorated methods
    expected_methods = ["Shuttle.run", "Shuttle._process_files"]
    missing_methods = []
    
    for method in expected_methods:
        if method not in log_contents:
            missing_methods.append(method)
    
    if missing_methods:
        return ValidationResult(
            False,
            f"Expected methods not found in call stacks: {missing_methods}",
            {'missing_methods': missing_methods}
        )
    
    return ValidationResult(
        True, 
        f"Found {call_stack_count} call stack entries with expected methods",
        {'call_stack_count': call_stack_count}
    )


def validate_hierarchy_logging_not_in_info(test_instance, params, result, context):
    """Validate that hierarchy logging does NOT appear in INFO mode"""
    
    # Find and read the log file
    log_files = [f for f in os.listdir(context['logs_dir']) 
                 if f.startswith('shuttle_') and f.endswith('.log')]
    
    if not log_files:
        return ValidationResult(False, "No shuttle log file found")
    
    # Read the most recent log file
    log_file_path = os.path.join(context['logs_dir'], sorted(log_files)[-1])
    with open(log_file_path, 'r') as f:
        log_contents = f.read()
    
    # Check that hierarchy logging is NOT present
    if "[CALL STACK:" in log_contents:
        # Find the offending lines
        offending_lines = [line for line in log_contents.split('\n') if '[CALL STACK:' in line]
        return ValidationResult(
            False,
            "Call stack found in INFO logs when it shouldn't be",
            {
                'log_file': log_file_path,
                'offending_lines': offending_lines[:5]  # Show first 5
            }
        )
    
    # But normal logging should still work
    if "Starting Shuttle" not in log_contents:
        return ValidationResult(
            False,
            "Normal logging not working - 'Starting Shuttle' not found",
            {'log_file': log_file_path}
        )
    
    return ValidationResult(True, "No call stack in INFO logs as expected")


def validate_log_file_has_debug_entries(test_instance, params, result, context):
    """Validate that DEBUG level logging is actually working"""
    
    # Find and read the log file
    log_files = [f for f in os.listdir(context['logs_dir']) 
                 if f.startswith('shuttle_') and f.endswith('.log')]
    
    if not log_files:
        return ValidationResult(False, "No shuttle log file found")
    
    log_file_path = os.path.join(context['logs_dir'], sorted(log_files)[-1])
    with open(log_file_path, 'r') as f:
        log_contents = f.read()
    
    # Check for DEBUG level entries
    debug_count = log_contents.count(" DEBUG ")
    
    if debug_count == 0:
        return ValidationResult(
            False,
            "No DEBUG level log entries found - log level may not be set correctly",
            {
                'log_file': log_file_path,
                'log_level_expected': 'DEBUG',
                'debug_entries_found': 0
            }
        )
    
    return ValidationResult(
        True,
        f"Found {debug_count} DEBUG level log entries",
        {'debug_count': debug_count}
    )


class TestHierarchyLoggingIntegration(unittest.TestCase):
    """Test hierarchy logging integration with Shuttle"""
    
    def test_hierarchy_logging_in_debug_mode(self):
        """Test that hierarchy logging appears when log level is DEBUG"""
        
        # Create test instance
        test_instance = TestShuttleWithValidator()
        test_instance.setUp()
        
        try:
            # Create parameters for DEBUG mode test
            # Note: We need to ensure DEBUG logging is enabled
            params = TestParameters(
                thread_count=1,
                clean_file_count=1,
                malware_file_count=0,
                file_size_kb=10,
                setup_throttling=False,
                max_files_per_day=0,
                max_volume_per_day_mb=0,
                min_free_space_mb=0,
                initial_files=0,
                initial_volume_mb=0,
                mock_free_space_mb=5000,
                use_simulator=True,
                expected_throttled=False,
                expected_files_processed=1,
                description="Hierarchy logging in DEBUG mode test"
            )
            
            # IMPORTANT: Need to modify the command to include log level
            # We'll need to override the _build_base_command method or add log_level to params
            
            # Store original method
            original_build_command = test_instance._build_base_command
            
            def build_command_with_debug(params):
                cmd = original_build_command(params)
                # Add log level DEBUG
                cmd.extend(['--log-level', 'DEBUG'])
                return cmd
            
            # Monkey patch the method
            test_instance._build_base_command = build_command_with_debug
            
            # Define validators
            validators = [
                validate_log_file_has_debug_entries,  # First check DEBUG is working
                validate_hierarchy_logging_in_debug,   # Then check hierarchy logging
            ]
            
            # Run test
            result = test_instance.run_test_scenario_with_validation(params, validators)
            
            # All validations should have passed
            for validation in result['validations']:
                self.assertTrue(
                    validation['result'].passed,
                    f"Validation {validation['validator']} failed: {validation['result'].message}"
                )
                
        finally:
            test_instance.tearDown()
    
    def test_hierarchy_logging_not_in_info_mode(self):
        """Test that hierarchy logging does NOT appear in INFO mode"""
        
        # Create test instance
        test_instance = TestShuttleWithValidator()
        test_instance.setUp()
        
        try:
            # Create parameters for INFO mode test (default)
            params = TestParameters(
                thread_count=1,
                clean_file_count=1,
                malware_file_count=0,
                file_size_kb=10,
                setup_throttling=False,
                max_files_per_day=0,
                max_volume_per_day_mb=0,
                min_free_space_mb=0,
                initial_files=0,
                initial_volume_mb=0,
                mock_free_space_mb=5000,
                use_simulator=True,
                expected_throttled=False,
                expected_files_processed=1,
                description="No hierarchy logging in INFO mode test"
            )
            
            # Need to explicitly set INFO to override config file which has DEBUG
            original_build_command = test_instance._build_base_command
            
            def build_command_with_info(params):
                cmd = original_build_command(params)
                # Add log level INFO explicitly
                cmd.extend(['--log-level', 'INFO'])
                return cmd
            
            # Monkey patch the method
            test_instance._build_base_command = build_command_with_info
            
            # Define validators
            validators = [
                validate_hierarchy_logging_not_in_info,
            ]
            
            # Run test
            result = test_instance.run_test_scenario_with_validation(params, validators)
            
            # All validations should have passed
            for validation in result['validations']:
                self.assertTrue(
                    validation['result'].passed,
                    f"Validation {validation['validator']} failed: {validation['result'].message}"
                )
                
        finally:
            test_instance.tearDown()


# Additional validator functions that could be useful

def validate_call_stack_shows_hierarchy(test_instance, params, result, context):
    """Validate that call stacks show proper hierarchy"""
    
    log_files = [f for f in os.listdir(context['logs_dir']) 
                 if f.startswith('shuttle_') and f.endswith('.log')]
    
    if not log_files:
        return ValidationResult(False, "No shuttle log file found")
    
    log_file_path = os.path.join(context['logs_dir'], sorted(log_files)[-1])
    with open(log_file_path, 'r') as f:
        log_contents = f.read()
    
    # Extract call stack lines
    call_stack_lines = [line for line in log_contents.split('\n') if '[CALL STACK:' in line]
    
    if not call_stack_lines:
        return ValidationResult(False, "No call stack lines found")
    
    # Check for hierarchical patterns (→ indicates hierarchy)
    hierarchical_stacks = [line for line in call_stack_lines if '→' in line]
    
    if not hierarchical_stacks:
        return ValidationResult(
            False,
            "Call stacks don't show hierarchy (no → found)",
            {'call_stack_lines': call_stack_lines[:5]}
        )
    
    # Check for reasonable depth (at least some stacks should show 2+ levels)
    multi_level_stacks = [line for line in hierarchical_stacks if line.count('→') >= 1]
    
    if not multi_level_stacks:
        return ValidationResult(
            False,
            "No multi-level call stacks found",
            {'hierarchical_stacks': hierarchical_stacks[:5]}
        )
    
    return ValidationResult(
        True,
        f"Found {len(hierarchical_stacks)} hierarchical call stacks",
        {
            'total_stacks': len(call_stack_lines),
            'hierarchical_stacks': len(hierarchical_stacks),
            'sample': hierarchical_stacks[:3]
        }
    )


def create_log_level_validator(expected_level: str):
    """Factory to create validator for specific log level"""
    
    def validate_log_level(test_instance, params, result, context):
        # Check that output contains expected log level
        level_marker = f" {expected_level} "
        
        if level_marker not in result['output']:
            return ValidationResult(
                False,
                f"No {expected_level} level entries found in output",
                {'expected_level': expected_level}
            )
        
        count = result['output'].count(level_marker)
        return ValidationResult(
            True,
            f"Found {count} {expected_level} level entries",
            {'count': count}
        )
    
    validate_log_level.__name__ = f"validate_log_level_{expected_level}"
    return validate_log_level


if __name__ == '__main__':
    unittest.main()