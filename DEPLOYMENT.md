# CourtSide Analytics: Deployment & Development Guide

This document provides instructions on how to move this project to a new Windows PC and set up a working environment for both testing and development.

---

## 1. Prerequisites

Before setting up the project, ensure the target PC has the following:

- **Python 3.10 or higher**: [Download from python.org](https://www.python.org/downloads/windows/)
  - *Note: Ensure "Add Python to PATH" is checked during installation.*
- **Node.js 18 or higher**: [Download from nodejs.org](https://nodejs.org/)
- **SQLite Browser (Optional)**: [DB Browser for SQLite](https://sqlitebrowser.org/) if you want to inspect data directly.

---

## 2. Fast Setup (Using Bootstrap)

The project includes a `bootstrap.bat` script that automates the dependency installation.

1.  **Transfer the Files**: Copy the project folder (or unzip the deployment package) to your desired location on the new PC.
2.  **Run Bootstrap**: Double-click `bootstrap.bat`.
    - It will create a Python virtual environment (`.venv`).
    - It will install all backend requirements from `requirements.txt`.
    - It will install all frontend dependencies in the `web-ui` folder.
    - It will initialize your `.env` file.
3.  **Copy the Database**: If `tennis_data.db` was not included in your package due to size, **manually copy it** to the root directory from your original source.

---

## 3. Running the Application

Once the setup is complete, you can use the provided batch files to manage the platform:

- **Start**: Run `start_website.bat`.
  - This opens two windows: one for the Python API (Port 8004) and one for the Vite UI (Port 5173).
  - Open your browser to: `http://localhost:5173`
- **Stop**: Run `stop_website.bat` to safely terminate all related processes.

---

## 4. Development Workflow

### Project Structure Overview
- `/api.py`: Main FastAPI server and routing.
- `/tennis_db.py`: Database schema, migrations, and CRUD operations.
- `/web-ui/src/App.jsx`: Main frontend entry point and UI logic.
- `/web-ui/src/components/`: Reusable UI elements (Scouts, Search, etc.).
- `/stats_engine.py`: Logic for advanced analytics and streaks calculation.

### Making Changes
1.  **Backend**: If you modify Python files, restart the backend server (the window titled `CourtSide_Backend`).
2.  **Frontend**: Changes to the UI will Hot-Reload automatically as long as the dev server is running.

---

## 5. Deployment Packaging

To create a clean package for another machine:
1.  Open terminal in the project root.
2.  Run: `python package_project.py`
3.  This creates a ZIP file excluding temporary files, logs, and `node_modules`.
4.  To include the database in the package, use: `python package_project.py --include-db`

---

## 6. Troubleshooting

- **CORS Errors**: Ensure the backend is running on port 8004. The UI is configured to proxy requests in `vite.config.js`.
- **Missing Data**: Verify that `tennis_data.db` is in the root directory and has a size > 0.
- **Node Errors**: If `npm install` fails, delete the `web-ui/node_modules` folder and try again.
