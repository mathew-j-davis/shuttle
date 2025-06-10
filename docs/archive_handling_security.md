# Secure Archive Handling Guide for Shuttle

This guide provides comprehensive strategies for safely handling compressed files and preventing zip bomb attacks in the Shuttle file processing system.

## Table of Contents
- [Overview](#overview)
- [Detection Before Extraction](#detection-before-extraction)
- [Safe Extraction with Resource Limits](#safe-extraction-with-resource-limits)
- [Process-Level Isolation](#process-level-isolation)
- [Integration with Shuttle](#integration-with-shuttle)
- [Best Practices](#best-practices)

## Overview

Compressed files pose unique security challenges:
- **Zip bombs**: Small files that expand to enormous sizes
- **Nested archives**: Deeply nested compression to exhaust resources
- **Resource exhaustion**: CPU, memory, and disk space attacks
- **Hidden malware**: Executable content concealed within archives

## Detection Before Extraction

### Check Compression Ratio

Detect potential zip bombs by analyzing compression ratios before extraction:

```python
import zipfile
import os

def check_zip_bomb(zip_path, max_ratio=100):
    """
    Check if a zip file might be a zip bomb by comparing
    compressed vs uncompressed sizes
    """
    with zipfile.ZipFile(zip_path, 'r') as zf:
        total_compressed = sum(info.compress_size for info in zf.infolist())
        total_uncompressed = sum(info.file_size for info in zf.infolist())
        
        if total_compressed == 0:
            return False, 1.0
            
        ratio = total_uncompressed / total_compressed
        
        if ratio > max_ratio:
            return True, ratio
            
        # Also check individual files
        for info in zf.infolist():
            if info.compress_size > 0:
                file_ratio = info.file_size / info.compress_size
                if file_ratio > max_ratio:
                    return True, file_ratio
                    
    return False, ratio
```

### Check Nested Archive Depth

Detect deeply nested archives commonly used in zip bombs:

```python
def check_nested_archives(zip_path, max_depth=3):
    """
    Detect deeply nested archives (common in zip bombs)
    """
    def count_depth(path, current_depth=0):
        if current_depth > max_depth:
            return current_depth
            
        max_found = current_depth
        
        with zipfile.ZipFile(path, 'r') as zf:
            for info in zf.infolist():
                if info.filename.lower().endswith(('.zip', '.rar', '.7z', '.tar.gz')):
                    # This is a nested archive
                    max_found = max(max_found, current_depth + 1)
                    
        return max_found
    
    depth = count_depth(zip_path)
    return depth > max_depth, depth
```

## Safe Extraction with Resource Limits

### Memory-Limited Extraction

Extract files with strict size and count limits:

```python
import resource
import tempfile
import shutil

def extract_with_limits(zip_path, extract_to, max_size_mb=1000, max_files=1000):
    """
    Extract with strict resource limits
    """
    extracted_size = 0
    extracted_count = 0
    max_size_bytes = max_size_mb * 1024 * 1024
    
    # Use a temporary directory first
    with tempfile.TemporaryDirectory() as temp_dir:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            for member in zf.infolist():
                # Check file count limit
                if extracted_count >= max_files:
                    raise Exception(f"Archive contains too many files (>{max_files})")
                
                # Check cumulative size limit
                if extracted_size + member.file_size > max_size_bytes:
                    raise Exception(f"Archive exceeds size limit ({max_size_mb}MB)")
                
                # Check individual file size
                if member.file_size > max_size_bytes:
                    raise Exception(f"Single file too large: {member.filename}")
                
                # Extract to temp location first
                zf.extract(member, temp_dir)
                extracted_size += member.file_size
                extracted_count += 1
        
        # If we got here, extraction was safe - move to final location
        shutil.move(temp_dir, extract_to)
```

## Process-Level Isolation

### Using Subprocess with ulimit

Run archive inspection in a resource-limited subprocess:

```python
import subprocess
import json

def scan_archive_isolated(archive_path, timeout=30):
    """
    Scan archive in a resource-limited subprocess
    """
    script = """
import sys
import zipfile
import json

try:
    with zipfile.ZipFile(sys.argv[1], 'r') as zf:
        info = {
            'file_count': len(zf.infolist()),
            'total_compressed': sum(f.compress_size for f in zf.infolist()),
            'total_uncompressed': sum(f.file_size for f in zf.infolist()),
            'files': [
                {
                    'name': f.filename,
                    'size': f.file_size,
                    'compressed': f.compress_size
                }
                for f in zf.infolist()[:100]  # Limit preview
            ]
        }
        print(json.dumps(info))
except Exception as e:
    print(json.dumps({'error': str(e)}))
"""
    
    # Run with resource limits
    result = subprocess.run(
        [
            'bash', '-c',
            f'ulimit -v 524288; ulimit -t 5; python3 -c "{script}" {archive_path}'
        ],
        capture_output=True,
        text=True,
        timeout=timeout
    )
    
    return json.loads(result.stdout)
```

## Integration with Shuttle

### Configuration Options

Add these options to your Shuttle configuration:

```ini
[archive_handling]
# Enable archive inspection
inspect_archives = true

# Maximum compression ratio (uncompressed/compressed)
max_compression_ratio = 100

# Maximum uncompressed size (MB)
max_uncompressed_size = 1000

# Maximum number of files in archive
max_archive_files = 1000

# Maximum nesting depth
max_nesting_depth = 3

# Action on suspicious archive (quarantine, reject, scan_only)
suspicious_archive_action = quarantine
```

### Archive Handler Class

Comprehensive archive safety checking:

```python
import magic

class ArchiveHandler:
    def __init__(self, config):
        self.max_ratio = config.get('max_compression_ratio', 100)
        self.max_size_mb = config.get('max_uncompressed_size', 1000)
        self.max_files = config.get('max_archive_files', 1000)
        self.max_depth = config.get('max_nesting_depth', 3)
        
    def check_archive_safety(self, file_path):
        """
        Comprehensive archive safety check
        """
        issues = []
        
        # Check if it's actually an archive
        mime_type = magic.from_file(file_path, mime=True)
        if 'zip' not in mime_type and 'compressed' not in mime_type:
            return True, []
        
        # Check compression ratio
        is_bomb, ratio = check_zip_bomb(file_path, self.max_ratio)
        if is_bomb:
            issues.append(f"Dangerous compression ratio: {ratio:.1f}:1")
        
        # Check nesting
        too_deep, depth = check_nested_archives(file_path, self.max_depth)
        if too_deep:
            issues.append(f"Nested archives too deep: {depth} levels")
        
        # Quick size check without extraction
        try:
            info = scan_archive_isolated(file_path)
            if 'error' not in info:
                total_mb = info['total_uncompressed'] / (1024 * 1024)
                if total_mb > self.max_size_mb:
                    issues.append(f"Uncompressed size too large: {total_mb:.1f}MB")
                
                if info['file_count'] > self.max_files:
                    issues.append(f"Too many files: {info['file_count']}")
        except:
            issues.append("Failed to inspect archive safely")
        
        return len(issues) == 0, issues
```

## Best Practices

### 1. Never Extract in Production Paths
Always use isolated temporary directories for extraction and validation before moving to final locations.

### 2. Let AV Scanners Handle Inspection
Many antivirus scanners have built-in zip bomb detection. Configure your scanners appropriately:
- ClamAV: Use `--max-filesize`, `--max-scansize`, `--max-files`, `--max-recursion`
- Defender: Configure archive scanning limits in policy

### 3. Set Conservative Limits
It's better to reject suspicious files than risk system compromise:
- Maximum compression ratio: 100:1
- Maximum uncompressed size: 1GB
- Maximum files: 1000
- Maximum nesting: 3 levels

### 4. Monitor Resource Usage
Track CPU, memory, and disk usage during archive processing:
```python
import psutil
import os

def monitor_extraction():
    process = psutil.Process(os.getpid())
    return {
        'cpu_percent': process.cpu_percent(interval=0.1),
        'memory_mb': process.memory_info().rss / 1024 / 1024,
        'open_files': len(process.open_files())
    }
```

### 5. Log All Rejections
Maintain an audit trail of blocked archives:
```python
import logging

logger = logging.getLogger('shuttle.archive_security')

def log_rejection(file_path, issues):
    logger.warning(
        f"Archive rejected: {file_path}",
        extra={
            'file_path': file_path,
            'issues': issues,
            'timestamp': datetime.utcnow().isoformat()
        }
    )
```

## Additional Security Measures

### File Type Restrictions
Consider implementing a whitelist of allowed compressed formats:
```python
ALLOWED_ARCHIVE_TYPES = {
    'application/zip',
    'application/x-gzip',
    'application/x-tar',
    'application/x-7z-compressed'
}
```

### Sandboxing Options
For high-security environments, consider:
- Docker containers with resource limits
- Virtual machines for archive processing
- Dedicated archive processing servers
- Cloud-based scanning services

### Performance Considerations
Balance security with performance:
- Cache inspection results by file hash
- Process archives asynchronously
- Implement tiered inspection (quick checks first)
- Use parallel processing for multiple archives

## Conclusion

Secure archive handling requires a multi-layered approach:
1. Pre-extraction validation
2. Resource-limited processing
3. Process isolation
4. Comprehensive logging
5. Conservative configuration

By implementing these measures, Shuttle can safely process compressed files while protecting against zip bombs and other archive-based attacks.