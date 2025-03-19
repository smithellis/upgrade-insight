# Package Version Checker

This application analyzes the dependencies in a pyproject.toml file and compares them with the latest versions available on PyPI. It provides a web interface that displays the results in a color-coded table.

## Features

- Reads package versions from pyproject.toml
- Fetches latest versions from PyPI
- Color-coded display:
  - Red: Major version difference
  - Yellow: Minor version difference
  - White: No difference or same version

## Setup

1. Install the required dependencies:
```bash
pip install -r requirements.txt
```

2. Run the application:
```bash
python package_version_checker.py
```

3. Open your web browser and navigate to:
```
http://localhost:5000
```

## Requirements

- Python 3.6 or higher
- Dependencies listed in requirements.txt 