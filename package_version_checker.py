import toml
import requests
from packaging import version
from flask import Flask, render_template_string, request
import re

app = Flask(__name__)


def parse_version_constraint(constraint):
    """Parse version constraint from pyproject.toml format."""
    if isinstance(constraint, str):
        # Remove any extras like [css]
        constraint = constraint.split("[")[0]
        # Remove any caret or other version specifiers
        return re.sub(r"[\^~>=<]", "", constraint)
    elif isinstance(constraint, dict):
        return parse_version_constraint(constraint["version"])
    return None


def get_pypi_version(package_name):
    """Get the latest version of a package from PyPI."""
    try:
        response = requests.get(f"https://pypi.org/pypi/{package_name}/json")
        if response.status_code == 200:
            return response.json()["info"]["version"]
    except Exception as e:
        print(f"Error fetching version for {package_name}: {e}")
    return None


def compare_versions(current, latest):
    """Compare versions and return color code and upgrade level."""
    if not current or not latest:
        return "white", 0

    try:
        current_v = version.parse(current)
        latest_v = version.parse(latest)

        if current_v.major != latest_v.major:
            return "red", 2
        elif current_v.minor != latest_v.minor:
            return "yellow", 1
        return "white", 0
    except:
        return "white", 0


def analyze_packages():
    """Analyze packages from pyproject.toml and get their versions."""
    with open("package_lists/pyproject.toml", "r") as f:
        data = toml.load(f)

    packages = []
    dependencies = data.get("tool", {}).get("poetry", {}).get("dependencies", {})

    for package, version_constraint in dependencies.items():
        if package == "python":  # Skip python version
            continue

        current_version = parse_version_constraint(version_constraint)
        latest_version = get_pypi_version(package)
        color, upgrade_level = compare_versions(current_version, latest_version)

        packages.append(
            {
                "name": package,
                "current_version": current_version,
                "latest_version": latest_version,
                "color": color,
                "upgrade_level": upgrade_level,
            }
        )

    return packages


# HTML template
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Package Version Checker</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            background-color: white;
            box-shadow: 0 1px 3px rgba(0,0,0,0.2);
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        th {
            background-color: #4CAF50;
            color: white;
            cursor: pointer;
        }
        th:hover {
            background-color: #45a049;
        }
        tr:nth-child(even) {
            background-color: #f9f9f9;
        }
        .red { background-color: #ffebee; }
        .yellow { background-color: #fff3e0; }
        .white { background-color: white; }
        .sort-icon {
            margin-left: 5px;
        }
    </style>
    <script>
        function sortTable(column, type) {
            const table = document.querySelector('table');
            const tbody = table.querySelector('tbody');
            const rows = Array.from(tbody.querySelectorAll('tr'));
            
            // Remove existing sort icons
            document.querySelectorAll('.sort-icon').forEach(icon => icon.remove());
            
            // Add sort icon to clicked header
            const header = table.querySelector(`th:nth-child(${column})`);
            const currentOrder = header.getAttribute('data-order') === 'asc' ? 'desc' : 'asc';
            header.setAttribute('data-order', currentOrder);
            header.innerHTML += `<span class="sort-icon">${currentOrder === 'asc' ? '↑' : '↓'}</span>`;
            
            // Sort rows
            rows.sort((a, b) => {
                let aValue, bValue;
                if (type === 'name') {
                    aValue = a.cells[0].textContent;
                    bValue = b.cells[0].textContent;
                } else if (type === 'upgrade') {
                    aValue = parseInt(a.cells[0].getAttribute('data-upgrade-level'));
                    bValue = parseInt(b.cells[0].getAttribute('data-upgrade-level'));
                }
                
                if (currentOrder === 'asc') {
                    return aValue > bValue ? 1 : -1;
                } else {
                    return aValue < bValue ? 1 : -1;
                }
            });
            
            // Reorder rows
            rows.forEach(row => tbody.appendChild(row));
        }
    </script>
</head>
<body>
    <h1>Package Version Checker</h1>
    <table>
        <tr>
            <th onclick="sortTable(1, 'name')">Package Name</th>
            <th>Current Version</th>
            <th>Latest Version</th>
            <th onclick="sortTable(4, 'upgrade')">Upgrade Level</th>
        </tr>
        {% for package in packages %}
        <tr>
            <td data-upgrade-level="{{ package.upgrade_level }}">{{ package.name }}</td>
            <td class="{{ package.color }}">{{ package.current_version }}</td>
            <td class="{{ package.color }}">{{ package.latest_version }}</td>
            <td class="{{ package.color }}">
                {% if package.upgrade_level == 2 %}
                    Major Update
                {% elif package.upgrade_level == 1 %}
                    Minor Update
                {% else %}
                    No Update
                {% endif %}
            </td>
        </tr>
        {% endfor %}
    </table>
</body>
</html>
"""


@app.route("/")
def index():
    packages = analyze_packages()
    return render_template_string(HTML_TEMPLATE, packages=packages)


if __name__ == "__main__":
    app.run(debug=True)
