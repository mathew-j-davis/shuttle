"""
Enhanced run_test_scenario with custom validation support

This demonstrates how to extend run_test_scenario to support custom validation functions
that can check logs, file system state, or any other aspect of the test.
"""

import os
import sys
import unittest
from typing import Callable, Dict, Any, List, Optional
from datetime import datetime

# Import the base test class
from test_shuttle import TestShuttle, TestParameters


class ValidationResult:
    """Container for validation results"""
    def __init__(self, passed: bool, message: str = "", details: Dict[str, Any] = None):
        self.passed = passed
        self.message = message
        self.details = details or {}


class TestShuttleWithValidator(TestShuttle):
    """Enhanced version of TestShuttle with custom validation support"""
    
    def run_test_scenario_with_validation(self, params: TestParameters, 
                                     validators: Optional[List[Callable]] = None):
        """
        Run a test scenario with custom validation functions.
        
        Args:
            params: TestParameters object with test configuration
            validators: List of validation functions to run after shuttle execution.
                       Each function should accept (test_instance, params, result, context)
                       and return a ValidationResult
        
        Returns:
            dict: Test result with additional 'validations' key containing validation results
        """
        # Print test description
        print(f"\n=== Running Test: {params.description} ===")
        
        # Setup test environment
        self._setup_test_environment(params)
        
        # Create test files and track what was created
        clean_files, malware_files = self._create_test_files(
            clean_file_count=params.clean_file_count,
            malware_file_count=params.malware_file_count,
            file_size_kb=params.file_size_kb
        )
        
        print(f"Created {len(clean_files)} clean files and {len(malware_files)} malware files")
        
        # Build context for validators
        context = {
            'clean_files': clean_files,
            'malware_files': malware_files,
            'total_files': len(clean_files) + len(malware_files),
            'test_start_time': datetime.now(),
            'source_dir': self.source_dir,
            'destination_dir': self.destination_dir,
            'quarantine_dir': self.quarantine_dir,
            'hazard_dir': self.hazard_dir,
            'logs_dir': self.logs_dir,
        }
        
        # Print throttling prediction
        self._print_throttling_prediction(params)
        
        # Run shuttle with the appropriate throttling settings
        result = self._run_shuttle(params)
        
        # Add end time to context
        context['test_end_time'] = datetime.now()
        context['duration'] = (context['test_end_time'] - context['test_start_time']).total_seconds()
        
        # Run default verification
        self._verify_test_results(params, result)
        
        # Run custom validators if provided
        validation_results = []
        if validators:
            print("\nRunning custom validations...")
            for validator in validators:
                try:
                    validation_result = validator(self, params, result, context)
                    validation_results.append({
                        'validator': validator.__name__,
                        'result': validation_result
                    })
                    
                    status = "PASSED" if validation_result.passed else "FAILED"
                    print(f"  {validator.__name__}: {status} - {validation_result.message}")
                    
                    # If validation failed, assert to fail the test
                    if not validation_result.passed:
                        self.fail(f"Validation '{validator.__name__}' failed: {validation_result.message}")
                        
                except Exception as e:
                    print(f"  {validator.__name__}: ERROR - {str(e)}")
                    validation_results.append({
                        'validator': validator.__name__,
                        'result': ValidationResult(False, f"Exception: {str(e)}")
                    })
                    raise
        
        # Add validation results to the return value
        result['validations'] = validation_results
        result['context'] = context
        
        return result


# Example validation functions

def validate_file_integrity(test_instance: TestShuttleWithValidator, params: TestParameters, 
                           result: Dict[str, Any], context: Dict[str, Any]) -> ValidationResult:
    """Validate that all processed files maintain their integrity"""
    
    # Check that files in destination match expected content/size
    destination_files = os.listdir(context['destination_dir'])
    
    for file in destination_files:
        file_path = os.path.join(context['destination_dir'], file)
        file_size = os.path.getsize(file_path)
        expected_size = params.file_size_kb * 1024
        
        # Allow some tolerance for file size (metadata might add a few bytes)
        if abs(file_size - expected_size) > 100:
            return ValidationResult(
                False, 
                f"File {file} has unexpected size: {file_size} bytes (expected ~{expected_size})",
                {'file': file, 'actual_size': file_size, 'expected_size': expected_size}
            )
    
    return ValidationResult(True, f"All {len(destination_files)} files have correct size")


def validate_log_contains_patterns(test_instance: TestShuttleWithValidator, params: TestParameters,
                                  result: Dict[str, Any], context: Dict[str, Any]) -> ValidationResult:
    """Validate that logs contain expected patterns"""
    
    required_patterns = [
        "\"successful_files\": 5",
        "\"failed_files\": 0",
        "\"total_files\": 5"
    ]
    
    missing_patterns = []
    for pattern in required_patterns:
        if pattern not in result['output']:
            missing_patterns.append(pattern)
    
    if missing_patterns:
        return ValidationResult(
            False,
            f"Missing required log patterns: {missing_patterns}",
            {'missing_patterns': missing_patterns}
        )
    
    return ValidationResult(True, "All required log patterns found")


def validate_quarantine_cleaned(test_instance: TestShuttleWithValidator, params: TestParameters,
                               result: Dict[str, Any], context: Dict[str, Any]) -> ValidationResult:
    """Validate that quarantine directory is cleaned after processing"""
    
    quarantine_files = os.listdir(context['quarantine_dir'])
    
    if quarantine_files:
        return ValidationResult(
            False,
            f"Quarantine directory not cleaned: {len(quarantine_files)} files remaining",
            {'remaining_files': quarantine_files}
        )
    
    return ValidationResult(True, "Quarantine directory properly cleaned")


def validate_processing_time(test_instance: TestShuttleWithValidator, params: TestParameters,
                           result: Dict[str, Any], context: Dict[str, Any]) -> ValidationResult:
    """Validate that processing completed within reasonable time"""
    
    max_time_per_file = 10.0  # seconds
    total_files = context['total_files']
    max_expected_time = total_files * max_time_per_file
    
    actual_time = result.get('elapsed_time', 0)
    
    if actual_time > max_expected_time:
        return ValidationResult(
            False,
            f"Processing took too long: {actual_time:.2f}s (expected < {max_expected_time:.2f}s)",
            {'actual_time': actual_time, 'max_expected_time': max_expected_time}
        )
    
    return ValidationResult(
        True, 
        f"Processing completed in {actual_time:.2f}s ({actual_time/total_files:.2f}s per file)"
    )


def validate_daily_tracker_state(test_instance: TestShuttleWithValidator, params: TestParameters,
                               result: Dict[str, Any], context: Dict[str, Any]) -> ValidationResult:
    """Validate the daily processing tracker state after test"""
    
    # Find the tracker summary file
    tracker_files = [f for f in os.listdir(context['logs_dir']) 
                     if f.startswith('summary_') and f.endswith('.yaml')]
    
    if not tracker_files:
        return ValidationResult(False, "No daily processing tracker log found")
    
    # Read the latest tracker file
    import yaml
    tracker_path = os.path.join(context['logs_dir'], sorted(tracker_files)[-1])
    
    with open(tracker_path, 'r') as f:
        tracker_data = yaml.safe_load(f)
    
    # Validate tracker state
    if not tracker_data:
        return ValidationResult(False, "Tracker file is empty")
    
    # Check totals section exists
    if 'totals' not in tracker_data:
        return ValidationResult(False, "Tracker file missing totals section")
    
    totals = tracker_data['totals']
    
    # Check that pending files are cleared
    pending_count = totals.get('pending_files', 0)
    if pending_count > 0:
        return ValidationResult(
            False,
            f"Tracker still has {pending_count} pending files",
            {'pending_files': pending_count}
        )
    
    # Check file counts match expectations
    success_count = totals.get('successful_files', 0)
    failed_count = totals.get('failed_files', 0)
    suspect_count = totals.get('suspect_files', 0)
    
    return ValidationResult(
        True,
        f"Tracker shows {success_count} successful, {failed_count} failed, {suspect_count} suspect files, 0 pending",
        {'tracker_data': tracker_data}
    )


# Example test using custom validators
class TestCustomValidation(unittest.TestCase):
    """Example tests using custom validation"""
    
    def test_with_custom_validators(self):
        """Test scenario with multiple custom validators"""
        
        # Set up the enhanced test instance
        test_instance = TestShuttleWithValidator()
        test_instance.setUp()
        
        try:
            # Define test parameters
            params = TestParameters(
                thread_count=1,
                clean_file_count=5,
                malware_file_count=0,
                file_size_kb=100,
                setup_throttling=False,
                max_files_per_day=0,
                max_volume_per_day_mb=0,
                min_free_space_mb=0,
                initial_files=0,
                initial_volume_mb=0,
                mock_free_space_mb=5000,
                use_simulator=True,
                expected_throttled=False,
                expected_files_processed=5,
                description="Test with custom validators"
            )
            
            # Define validators to use
            validators = [
                validate_file_integrity,
                validate_log_contains_patterns,
                validate_quarantine_cleaned,
                validate_processing_time,
                validate_daily_tracker_state
            ]
            
            #                

            # Run test with validators
            result = test_instance.run_test_scenario_with_validation(params, validators)
            
            # Check that all validations passed
            for validation in result['validations']:
                self.assertTrue(
                    validation['result'].passed,
                    f"Validation {validation['validator']} failed: {validation['result'].message}"
                )
                
        finally:
            test_instance.tearDown()


# Example: Creating a custom validator on the fly
def create_file_count_validator(expected_count: int) -> Callable:
    """Factory function to create a validator that checks file count"""
    
    def validate_file_count(test_instance, params, result, context):
        actual_count = len(os.listdir(context['destination_dir']))
        if actual_count != expected_count:
            return ValidationResult(
                False,
                f"Expected {expected_count} files in destination, found {actual_count}"
            )
        return ValidationResult(True, f"Found expected {expected_count} files")
    
    # Set a meaningful name for the validator
    validate_file_count.__name__ = f"validate_file_count_{expected_count}"
    
    return validate_file_count


if __name__ == '__main__':
    # Example of running a test with custom validation
    test = TestShuttleWithValidator()
    test.setUp()
    
    try:
        params = TestParameters.with_defaults(
            clean_file_count=3,
            description="Example with dynamic validator"
        )
        
        # Create a custom validator for this specific test
        validators = [
            create_file_count_validator(3),  # Expect 3 files
            validate_quarantine_cleaned,
            validate_processing_time
        ]
        
        result = test.run_test_scenario_with_validation(params, validators)
        print("\nTest completed successfully with all validations passing!")
        
    finally:
        test.tearDown()