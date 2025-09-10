import toml
import asyncio
import aiohttp
from packaging import version
from flask import Flask, render_template_string
import re

app = Flask(__name__)


def parse_version_constraint(constraint):
    """Parse version constraint from pyproject.toml format."""
    if isinstance(constraint, str):
        # Remove any extras like [css]
        constraint = constraint.split("[")[0]
        # Split on comma, take first part
        first = constraint.split(",")[0]
        # Remove any caret or other version specifiers
        parsed = re.sub(r"[\^~>=<]", "", first).strip()
        print(f"parse_version_constraint: {constraint} -> {parsed}")
        return parsed
    elif isinstance(constraint, dict):
        print(f"parse_version_constraint (dict): {constraint}")
        return parse_version_constraint(constraint["version"])
    print(f"parse_version_constraint: unknown format {constraint}")
    return None


async def get_pypi_info(session, package_name):
    """Get the latest version and description of a package from PyPI."""
    url = f"https://pypi.org/pypi/{package_name}/json"
    try:
        async with session.get(url) as response:
            print(
                f"get_pypi_info: Requesting {package_name} -> status {response.status}"
            )
            if response.status == 200:
                data = await response.json()
                latest = data["info"].get("version", "")
                description = data["info"].get("summary", "")
                print(
                    f"get_pypi_info: {package_name} latest version {latest}, description {description}"
                )
                return latest, description
            else:
                print(f"get_pypi_info: Failed to fetch {package_name}")
    except Exception as e:
        print(f"Error fetching info for {package_name}: {e}")
    return None, None


def compare_versions(current, latest):
    """Compare versions and return color code and upgrade level."""
    if not current or not latest:
        print(f"compare_versions: missing current ({current}) or latest ({latest})")
        return "white", 0

    try:
        current_v = version.parse(current)
        latest_v = version.parse(latest)
        print(f"compare_versions: current {current_v}, latest {latest_v}")
        if current_v.major != latest_v.major:
            print(f"compare_versions: Major update needed for {current} -> {latest}")
            return "red", 2
        elif current_v.minor != latest_v.minor:
            print(f"compare_versions: Minor update needed for {current} -> {latest}")
            return "yellow", 1
        print(f"compare_versions: No update needed for {current} -> {latest}")
        return "white", 0
    except Exception as e:
        print(f"compare_versions: Error comparing {current} and {latest}: {e}")
        return "white", 0


async def analyze_packages_async():
    """Analyze packages from pyproject.toml and get their versions and descriptions asynchronously."""
    print("analyze_packages_async: Reading pyproject.toml...")
    with open("package_lists/pyproject.toml", "r") as f:
        data = toml.load(f)

    packages = []
    dependencies = data.get("project", {}).get("dependencies", [])
    print(f"analyze_packages_async: Found dependencies: {dependencies}")

    async with aiohttp.ClientSession() as session:
        tasks = []
        for dep in dependencies:
            match = re.match(r"([A-Za-z0-9_.\-]+)(\[.*\])?(.*)", dep)
            if not match:
                print(f"analyze_packages_async: Could not parse dependency: {dep}")
                continue
            package = match.group(1)
            version_constraint = match.group(3).strip()
            print(
                f"analyze_packages_async: Processing {package} with constraint {version_constraint}"
            )
            current_version = parse_version_constraint(version_constraint)
            tasks.append((package, current_version, session, package))

        results = await asyncio.gather(
            *[get_pypi_info(session, pkg) for pkg, _, session, pkg in tasks]
        )

        for idx, (package, current_version, _, _) in enumerate(tasks):
            latest_version, description = results[idx]
            color, upgrade_level = compare_versions(current_version, latest_version)
            print(
                f"analyze_packages_async: {package}: current={current_version}, latest={latest_version}, color={color}, upgrade_level={upgrade_level}, description={description}"
            )
            packages.append(
                {
                    "name": package,
                    "current_version": current_version,
                    "latest_version": latest_version,
                    "color": color,
                    "upgrade_level": upgrade_level,
                    "description": description,
                }
            )

    print(f"analyze_packages_async: Final package list: {packages}")
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
    packages = asyncio.run(analyze_packages_async())
    return render_template_string(HTML_TEMPLATE, packages=packages)


if __name__ == "__main__":
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
                <th>Description</th>
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
                <td>{{ package.description }}</td>
            </tr>
            {% endfor %}
        </table>
    </body>
    </html>
    """
