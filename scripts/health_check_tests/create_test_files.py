#!/usr/bin/env python3

import os
import random
import string
import argparse

def get_random_content(length=1000):
    """Generate random text content of specified length"""
    return ''.join(random.choices(string.ascii_letters, k=length))

def create_test_files(target_dir):
    """Create test files in the specified directory"""
    # Ensure directory exists
    os.makedirs(target_dir, exist_ok=True)
    
    # Create inner directory for nested test files
    inner_dir = os.path.join(target_dir, 'inner')
    os.makedirs(inner_dir, exist_ok=True)
    
    # Create files in main directory
    main_files = ['a.txt', 'b.txt', 'c.txt']
    for filename in main_files:
        file_path = os.path.join(target_dir, filename)
        content = get_random_content()
        with open(file_path, 'w') as file:
            file.write(content)
    
    # Create files in inner directory
    inner_files = ['d.txt', 'e.txt', 'f.txt']
    for filename in inner_files:
        file_path = os.path.join(inner_dir, filename)
        content = get_random_content()
        with open(file_path, 'w') as file:
            file.write(content)
    
    print(f"Created test files in {target_dir}:")
    print(f"  Main directory: {', '.join(main_files)}")
    print(f"  Inner directory: {', '.join(inner_files)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create test files for Shuttle testing")
    parser.add_argument(
        "--path", 
        type=str, 
        help="Path where test files should be created (defaults to SHUTTLE_TEST_WORK_DIR/in)"
    )
    
    args = parser.parse_args()
    
    # Use provided path or default to SHUTTLE_TEST_WORK_DIR/in
    if args.path:
        target_dir = args.path
    else:
        # Get SHUTTLE_TEST_WORK_DIR from environment or use a default
        work_dir = os.environ.get("SHUTTLE_TEST_WORK_DIR", os.path.expanduser("~/.local/share/shuttle/work"))
        target_dir = os.path.join(work_dir, "in")
    
    create_test_files(target_dir)
