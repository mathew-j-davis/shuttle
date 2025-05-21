#!/usr/bin/env python3

import os
import subprocess
import argparse

def set_defender_exclusions(directory_path):
    """Add specified directory to Microsoft Defender exclusions"""
    if not os.path.exists(directory_path):
        print(f"Directory does not exist: {directory_path}")
        return False
    
    try:
        # Try to add the exclusion
        result = subprocess.run(
            ["mdatp", "exclusion", "folder", "add", "--path", directory_path, "--scope", "global"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False
        )
        
        if result.returncode == 0:
            print(f"Added exclusion for: {directory_path}")
            return True
        else:
            print(f"Failed to add exclusion: {result.stderr}")
            return False
    
    except FileNotFoundError:
        print("Microsoft Defender command line tool (mdatp) not found")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Set Microsoft Defender exclusions for Shuttle directories")
    parser.add_argument(
        "path",
        type=str,
        help="Path to add to Microsoft Defender exclusions"
    )
    
    args = parser.parse_args()
    
    # Check if mdatp command is available
    check_cmd = subprocess.run(
        ["which", "mdatp"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False
    )
    
    if check_cmd.returncode != 0:
        print("Microsoft Defender CLI tool not found")
        exit(1)
    
    # Set exclusion for the specified path
    success = set_defender_exclusions(args.path)
    
    if success:
        print("Exclusion added successfully")
    else:
        print("Failed to add exclusion")
        exit(1)
