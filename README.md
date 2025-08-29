````markdown
# LC Dashboard

A Flask-based dashboard to analyze Local Chapter (LC) activity over time.

## Features
- View how many LCs are currently active in the latest year.
- Identify inactive LCs (were active in the past but not in the latest year).
- Year-wise trends of active vs inactive LCs.
- Filter/search by LC ID.
- Export inactive LC details as CSV.

## Tech Stack
- **Backend:** Flask, SQLAlchemy
- **Database:** MySQL (configurable to SQLite/Postgres)
- **Frontend:** HTML, Bootstrap (Jinja templates)

## Setup Instructions

1. **Clone the repo:**
   ```bash
   git clone https://github.com/Sagankaur/Local-Chapter-NPTEL
   cd <repo-name>
   ```

2. **Create a virtual environment:**

   ```bash
   python -m venv .venv
   .venv\Scripts\activate   # On Windows
   source .venv/bin/activate  # On Linux/Mac
   ```

3. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

6. **Run the app:**

   ```bash
    flask --app app.py init-db
    (Optional sample data) flask --app app.py seed
    flask --app app.py run
    Then open http://127.0.0.1:5000/.
   ```
## **Main Pages**

### 1. `GET /` - **Dashboard/Homepage**
- **Purpose**: Main dashboard showing LC activity overview
- **Features**: 
  - Displays latest year's active LC count
  - Shows inactive LCs from latest year
  - Includes trend visualization
  - Search functionality for specific LC timelines

### 2. `GET /upload` - **Data Upload Form**
- **Purpose**: Form for uploading CSV data files
- **Features**: 
  - File upload interface
  - Handles POST requests for file processing
  - Validates CSV structure and required columns

## **API Endpoints**

### 3. `GET /api/active_lcs` - **Active LCs API**
- **Returns**: JSON with active LCs in latest year
- **Data**: Latest year, count of active LCs, list of active LC IDs

### 4. `GET /api/inactive_lcs` - **Inactive LCs API**
- **Returns**: JSON with LCs that were active previously but inactive in latest year
- **Data**: Latest year, count of inactive LCs, list of inactive LC IDs

### 5. `GET /api/trend` - **Trend Data API**
- **Returns**: JSON with yearly trend of active vs inactive LCs
- **Data**: Year-by-year breakdown of active and inactive counts

### 6. `GET /api/lc/<lc_id>` - **LC Timeline API**
- **Purpose**: Get historical data for a specific LC
- **Returns**: JSON array of yearly records for the specified LC
- **Data**: Year, enrollments, registrations, and active status

## **Data Export**

### 7. `GET /export_inactive` - **Inactive LCs Export**
- **Purpose**: Download inactive LCs as CSV file
- **Returns**: CSV file with inactive LC IDs and notes
- **Features**: Direct file download for data export

## **Data Ingestion**

### 8. `POST /upload` - **Data Upload Handler**
- **Purpose**: Process uploaded CSV files
- **Features**: 
  - Validates and parses CSV data
  - Performs upsert operations (update existing or insert new records)
  - Provides feedback via flash messages

## **CLI Commands** (Not web routes, but available via command line)

### 9. `flask init-db` - **Database Initialization**
- **Purpose**: Create database tables

### 10. `flask seed` - **Sample Data Seeding**
- **Purpose**: Populate database with demo data for testing

## **Key Functionality Summary**
- **Dashboard**: Overview with search and visualization
- **Data Management**: Upload and export capabilities  
- **APIs**: Programmatic access to LC activity data
- **Reporting**: Active/inactive tracking and trend analysis
- **Search**: Individual LC timeline exploration

```