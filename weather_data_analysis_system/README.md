# Weather Data Analysis System

A beginner-friendly Flask + MySQL project that analyzes **recorded observations**, not weather forecasts.

## Features
- Upload CSV weather observations.
- Validate required columns, dates, numeric fields, humidity range (0–100), and non-negative rainfall.
- Save usable records to MySQL.
- Calculate daily and monthly min/max/average temperature, average humidity, and rainfall totals/averages.
- Plot a temperature trend and monthly rainfall totals.
- Report invalid dates, missing locations, missing numeric readings, and invalid ranges in the upload message.

## Technology
Python 3.10+, Flask, pandas, NumPy, Matplotlib, MySQL 8+.

## Folder structure
```text
weather_data_analysis_system/
├── app.py
├── requirements.txt
├── .env.example
├── .gitignore
├── schema.sql
├── README.md
├── data/
│   └── sample_weather.csv
├── templates/
│   └── index.html
├── static/
│   ├── style.css
│   └── charts/              # generated chart images
└── uploads/                 # reserved for local uploads; ignored by Git
```

## 1. Install prerequisites
- Python 3.10 or newer
- MySQL Server 8+ and a MySQL client (MySQL Workbench is optional)
- Git (for GitHub upload)

Check Python and Git:
```bash
python --version
git --version
```

## 2. Create the database
Start MySQL, then run the SQL in `schema.sql`. For example, from a terminal:
```bash
mysql -u root -p < schema.sql
```
Enter your MySQL password when prompted. You can also open `schema.sql` in MySQL Workbench and execute it.

## 3. Configure environment variables
Copy `.env.example` to `.env`:
- Windows PowerShell: `Copy-Item .env.example .env`
- macOS/Linux: `cp .env.example .env`

Edit `.env` and set `DB_USER`, `DB_PASSWORD`, and other values to match your local MySQL setup. Do not commit `.env` to GitHub.

## 4. Create a virtual environment and install packages
Windows PowerShell:
```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```
If PowerShell blocks activation, use Command Prompt:
```bat
.venv\Scripts\activate.bat
```

macOS/Linux:
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## 5. Run the app
Make sure MySQL is running and `.env` is configured:
```bash
python app.py
```
Open http://127.0.0.1:5000 in your browser. Select **Download sample CSV** or upload `data/sample_weather.csv`.

## CSV format
Required headers:
```csv
observation_date,location,temperature,humidity,rainfall
2025-01-01,Hyderabad,26.2,58,0
```
Aliases accepted: `date` for `observation_date`, `city` for `location`, `temperature_c` for `temperature`, `humidity_percent` for `humidity`, and `rainfall_mm` for `rainfall`.

Units: temperature in degrees Celsius (°C), relative humidity in percent (%), rainfall in millimetres (mm).

## Validation behavior
- Invalid dates and blank locations cause rows to be excluded.
- Blank/non-numeric temperature, humidity, or rainfall values are treated as missing, not as zero.
- Humidity outside 0–100 and negative rainfall are treated as invalid/missing.
- Valid rows with missing numeric values can still be stored; that field is omitted from its statistics.
- Duplicate observations are not automatically removed. If you upload the same file twice, records will be inserted twice.
- The upload message includes a data-quality report.

## Common problems
- **Can't connect to MySQL:** confirm the MySQL service is running, the DB name/user/password are correct, and the database was created.
- **`mysql` is not recognized:** run `schema.sql` from MySQL Workbench or add MySQL's `bin` directory to PATH.
- **Module not found:** activate `.venv` and run `pip install -r requirements.txt`.
- **Port 5000 is in use:** stop the other app or change the final `app.run(debug=True, port=5001)` line and use port 5001.
- **Charts missing:** upload valid rows; the dashboard regenerates chart images when records exist.

## Push to GitHub
1. Create a new **empty** repository on https://github.com/new. Do not initialize it with a README if you already have this one.
2. Open a terminal in this project folder:
```bash
git init
git add .
git commit -m "Build weather data analysis system"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/weather-data-analysis-system.git
git push -u origin main
```
3. Replace `YOUR-USERNAME` with your GitHub username. Authenticate using GitHub's browser sign-in or a supported credential manager when prompted. Never put a password or token directly in the remote URL.
4. Verify that `app.py`, `schema.sql`, `README.md`, `requirements.txt`, and the other project files appear in your repository.

### Before pushing
```bash
git status
```
Ensure `.env` is not listed. If it was accidentally staged before `.gitignore` was added, run `git rm --cached .env` before committing. Never upload database passwords or private datasets.
