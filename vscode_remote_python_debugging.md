# Remote Python Debugging with Virtual Environments in VSCode

This guide explains how to configure VSCode on your Windows machine (C) to debug Python code running in a virtual environment on your remote Linux machine (R).

## Prerequisites

1. VSCode installed on your Windows machine (C)
2. Remote SSH extension installed in VSCode
3. Python and Python extension installed in VSCode
4. SSH connection established from C to R
5. A Python virtual environment set up on R

## Steps to Configure Debugging with a Virtual Environment

### 1. Connect to the Remote Machine

1. Open VSCode on your Windows machine (C)
2. Press `F1` or `Ctrl+Shift+P` to open the command palette
3. Type "Remote-SSH: Connect to Host" and select your Linux machine (R)
4. Wait for VSCode to connect and set up the environment

### 2. Open Your Project Folder

1. Once connected, go to "File > Open Folder" (or press `Ctrl+K Ctrl+O`)
2. Navigate to your project directory on R and click "OK"

### 3. Create or Modify launch.json

1. Switch to the Debug view by clicking on the Run and Debug icon in the sidebar or pressing `Ctrl+Shift+D`
2. Click on "create a launch.json file" or the gear icon to create/edit launch.json
3. Select "Python" as the environment
4. If prompted for a debug configuration, choose "Python File"

### 4. Configure launch.json for Virtual Environment

Edit your `launch.json` file with the following configuration:

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python: Remote Shuttle",
            "type": "python",
            "request": "launch",
            "program": "${workspaceFolder}/path/to/run_shuttle.py",
            "console": "integratedTerminal",
            "justMyCode": true,
            "python": "/absolute/path/to/venv/bin/python",
            "env": {
                "PYTHONPATH": "${workspaceFolder}"
            },
            "cwd": "${workspaceFolder}"
        }
    ]
}
```

**Important settings to customize:**

- `"program"`: Update the path to point to your run_shuttle.py file's location
- `"python"`: Set this to the absolute path of the Python interpreter in your virtual environment
  - To find this path, you can run `which python` from within your activated venv on R
- `"cwd"`: The working directory for running the program (usually your project root)

### 5. Find Your Python Interpreter Path

To get the correct path for your virtual environment's Python interpreter:

1. On your remote machine (R), activate your virtual environment:
   ```bash
   source /path/to/venv/bin/activate
   ```

2. Run the following command to get the absolute path to the Python interpreter:
   ```bash
   which python
   ```

3. Copy the output (e.g., `/home/username/project/venv/bin/python`) and use it for the `"python"` field in launch.json

### 6. Debug Your Application

1. Set breakpoints in your code by clicking in the gutter (to the left of line numbers)
2. Select your "Python: Remote Shuttle" configuration from the dropdown in the Debug view
3. Press F5 or click the green play button to start debugging

## Troubleshooting

### Python Interpreter Not Found

If VSCode cannot find your Python interpreter:

1. Make sure the path in launch.json is correct and absolute
2. Check if the virtual environment exists and the interpreter is at the specified location
3. Verify you have permissions to access the interpreter

### Module Import Errors

If you encounter import errors:

1. Ensure your PYTHONPATH includes the root directory of your project
2. Check if all dependencies are installed in your virtual environment:
   ```bash
   source /path/to/venv/bin/activate
   pip install -r requirements.txt
   ```

### SSH Connection Issues

If you have problems with the SSH connection:

1. Verify your SSH key is properly set up
2. Check that the remote server is accessible
3. Try reconnecting via VSCode's Remote-SSH extension

## Example Configuration for Shuttle Project

Here's a specific example for the Shuttle project:

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python: Shuttle",
            "type": "python",
            "request": "launch",
            "program": "${workspaceFolder}/1_deployment/shuttle/run_shuttle.py",
            "console": "integratedTerminal",
            "justMyCode": true,
            "python": "/home/username/forge/venv/bin/python",
            "args": [
                "--config", 
                "${workspaceFolder}/config.json"
            ],
            "env": {
                "PYTHONPATH": "${workspaceFolder}"
            },
            "cwd": "${workspaceFolder}"
        }
    ]
}
```

Replace `/home/username/forge/venv/bin/python` with the actual path to your virtual environment's Python interpreter.
