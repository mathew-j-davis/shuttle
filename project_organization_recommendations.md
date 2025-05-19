# Project Organization Recommendations

Based on your project structure and requirements, I can see a few key challenges:

1. Dependencies between components that should be separately deployed
2. Shared code that needs to be accessible to different user roles
3. Mixed deployment vs. setup/test scripts
4. Different permission requirements for execution

Here's a reorganization plan that might better suit your needs:

## 1. Package-Based Structure

```
forge/
├── shared_lib/                  # Shared library code (was common)
│   ├── setup.py
│   └── shared/                  # Package directory
│       ├── __init__.py
│       ├── config.py
│       ├── files.py
│       └── ...
├── shuttle_app/                 # Shuttle as a standalone package
│   ├── setup.py
│   ├── shuttle/
│   │   ├── __init__.py
│   │   ├── scanning.py
│   │   └── ...
│   └── bin/
│       └── run_shuttle.py
├── defender_app/                # Defender test as a standalone package
│   ├── setup.py
│   ├── defender/
│   │   ├── __init__.py
│   │   ├── defender_test.py
│   │   └── ...
│   └── bin/
│       └── run_defender_test.py
├── deployment/                  # Deployment scripts
│   ├── install_shuttle.sh
│   ├── install_defender.sh
│   └── install_shared.sh
└── tests/                       # All tests in one place
    ├── unit/
    │   ├── test_shuttle.py
    │   ├── test_defender.py
    │   └── test_shared.py
    └── integration/
        └── ...
```

## 2. Dependency Management

- Make `shared_lib` a proper Python package that both `shuttle_app` and `defender_app` depend on
- Use `setup.py` in each package to manage dependencies and installation
- This way, when deploying, you can install packages in the appropriate locations with proper permissions

## 3. User Access Control

- Install `shared_lib` in a location accessible to both users
- Install `shuttle_app` and `defender_app` in separate locations with appropriate permissions
- Use environment variables or configuration files to specify paths to shared resources

## 4. Execution Environment

- Create wrapper scripts that set up the proper environment before execution
- Example wrapper (simplified):

```python
#!/usr/bin/env python3
import os
import sys

# Set up environment
os.environ["CONFIG_PATH"] = "/path/to/config"

# Execute the actual script
from shuttle.main import main
main()
```

## 5. Testing Strategy

- Separate unit tests from integration/deployment tests
- Use a test configuration that doesn't require special permissions for most tests
- Have specific tests that verify proper installation and permissions
```
