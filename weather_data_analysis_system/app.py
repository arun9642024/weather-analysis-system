import os
from io import BytesIO
from datetime import datetime
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from flask import Flask, render_template, request, redirect, url_for, flash, send_file
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import mysql.connector
from mysql.connector import Error

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "change-this-development-key")
UPLOAD_FOLDER = "uploads"
CHART_FOLDER = os.path.join("static", "charts")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(CHART_FOLDER, exist_ok=True)
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024
ALLOWED_EXTENSIONS = {"csv"}
REQUIRED_COLUMNS = ["observation_date", "location", "temperature", "humidity", "rainfall"]

def db_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "weather_analysis")
    )

def prepare_data(frame):
    """Normalize supported headers and return cleaned data plus a quality report."""
    df = frame.copy()
    df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]
    aliases = {"date": "observation_date", "temperature_c": "temperature",
               "humidity_percent": "humidity", "rainfall_mm": "rainfall",
               "city": "location"}
    df = df.rename(columns={k: v for k, v in aliases.items() if k in df.columns})
    missing_columns = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing_columns:
        raise ValueError("Missing required column(s): " + ", ".join(missing_columns))
    original_count = len(df)
    df["observation_date"] = pd.to_datetime(df["observation_date"], errors="coerce")
    for col in ["temperature", "humidity", "rainfall"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["location"] = df["location"].astype("string").str.strip()
    invalid_date = int(df["observation_date"].isna().sum())
    missing_location = int(df["location"].isna().sum() + (df["location"] == "").sum())
    missing_numeric = {c: int(df[c].isna().sum()) for c in ["temperature", "humidity", "rainfall"]}
    invalid_ranges = {
        "humidity_out_of_range": int(((df["humidity"] < 0) | (df["humidity"] > 100)).fillna(False).sum()),
        "negative_rainfall": int((df["rainfall"] < 0).fillna(False).sum())
    }
    # Treat out-of-range readings as invalid values; preserve rows and report them as missing.
    df.loc[(df["humidity"] < 0) | (df["humidity"] > 100), "humidity"] = np.nan
    df.loc[df["rainfall"] < 0, "rainfall"] = np.nan
    df = df.dropna(subset=["observation_date", "location"])
    df = df[df["location"] != ""].copy()
    df["observation_date"] = df["observation_date"].dt.date
    report = {
        "uploaded_rows": original_count,
        "usable_rows": len(df),
        "dropped_rows": original_count - len(df),
        "invalid_dates": invalid_date,
        "missing_locations": missing_location,
        "missing_numeric": missing_numeric,
        "invalid_ranges": invalid_ranges,
        "notes": "Missing or invalid numeric readings remain blank and are excluded from that field's statistics. Rows with invalid dates or missing locations are excluded."
    }
    return df, report

def save_to_mysql(df):
    conn = db_connection()
    try:
        cursor = conn.cursor()
        sql = """INSERT INTO weather_records
        (observation_date, location, temperature, humidity, rainfall)
        VALUES (%s, %s, %s, %s, %s)"""
        rows = []
        for _, r in df.iterrows():
            rows.append((
                r["observation_date"].isoformat(),
                str(r["location"]),
                None if pd.isna(r["temperature"]) else float(r["temperature"]),
                None if pd.isna(r["humidity"]) else float(r["humidity"]),
                None if pd.isna(r["rainfall"]) else float(r["rainfall"])
            ))
        if rows:
            cursor.executemany(sql, rows)
            conn.commit()
        return len(rows)
    finally:
        conn.close()

def load_from_mysql():
    conn = db_connection()
    try:
        return pd.read_sql(
            "SELECT observation_date, location, temperature, humidity, rainfall FROM weather_records ORDER BY observation_date",
            conn
        )
    finally:
        conn.close()

def build_summary(df):
    if df.empty:
        return [], []
    data = df.copy()
    data["observation_date"] = pd.to_datetime(data["observation_date"], errors="coerce")
    data = data.dropna(subset=["observation_date"])
    data["month"] = data["observation_date"].dt.to_period("M").astype(str)
    monthly = data.groupby(["month", "location"], dropna=False).agg(
        days=("observation_date", "nunique"),
        temp_min=("temperature", "min"),
        temp_max=("temperature", "max"),
        temp_avg=("temperature", "mean"),
        humidity_avg=("humidity", "mean"),
        rainfall_total=("rainfall", "sum"),
        rainfall_avg=("rainfall", "mean")
    ).reset_index()
    daily = data.groupby(["observation_date", "location"], dropna=False).agg(
        temp_min=("temperature", "min"), temp_max=("temperature", "max"),
        temp_avg=("temperature", "mean"), humidity_avg=("humidity", "mean"),
        rainfall_total=("rainfall", "sum")
    ).reset_index()
    return monthly.round(2).to_dict("records"), daily.round(2).to_dict("records")

def create_charts(df):
    if df.empty:
        return
    data = df.copy()
    data["observation_date"] = pd.to_datetime(data["observation_date"], errors="coerce")
    data = data.dropna(subset=["observation_date"])
    for filename in ["temperature_trend.png", "monthly_rainfall.png"]:
        path = os.path.join(CHART_FOLDER, filename)
        if os.path.exists(path):
            os.remove(path)
    for location, group in data.groupby("location"):
        group = group.sort_values("observation_date")
        plt.figure(figsize=(9, 4.5))
        plt.plot(group["observation_date"], group["temperature"], marker="o", linewidth=1.8)
        plt.title(f"Temperature trend — {location}")
        plt.xlabel("Observation date")
        plt.ylabel("Temperature (°C)")
        plt.grid(True, alpha=.3)
        plt.tight_layout()
        plt.savefig(os.path.join(CHART_FOLDER, "temperature_trend.png"), dpi=140)
        plt.close()
        break
    data["month"] = data["observation_date"].dt.to_period("M").astype(str)
    monthly = data.groupby(["month", "location"], as_index=False).agg(
        rainfall=("rainfall", "sum"), temperature=("temperature", "mean"))
    if not monthly.empty:
        plt.figure(figsize=(9, 4.5))
        for location, group in monthly.groupby("location"):
            plt.bar(group["month"], group["rainfall"], label=location, alpha=.8)
        plt.title("Monthly rainfall comparison by location")
        plt.xlabel("Month")
        plt.ylabel("Total rainfall (mm)")
        plt.xticks(rotation=35, ha="right")
        plt.legend()
        plt.tight_layout()
        plt.savefig(os.path.join(CHART_FOLDER, "monthly_rainfall.png"), dpi=140)
        plt.close()

@app.route("/", methods=["GET"])
def index():
    try:
        df = load_from_mysql()
        monthly, daily = build_summary(df)
        create_charts(df)
        return render_template("index.html", monthly=monthly, daily=daily,
                               total=len(df), locations=sorted(df["location"].dropna().unique().tolist()),
                               has_data=not df.empty)
    except Error as exc:
        flash(f"Database connection failed: {exc}. Check your .env settings and run schema.sql.", "error")
        return render_template("index.html", monthly=[], daily=[], total=0, locations=[], has_data=False)

@app.route("/upload", methods=["POST"])
def upload():
    file = request.files.get("file")
    if not file or file.filename == "":
        flash("Choose a CSV file first.", "error")
        return redirect(url_for("index"))
    if not file.filename.lower().endswith(".csv"):
        flash("Only .csv files are accepted.", "error")
        return redirect(url_for("index"))
    try:
        frame = pd.read_csv(file)
        cleaned, report = prepare_data(frame)
        if cleaned.empty:
            raise ValueError("No usable rows remain after validating dates and locations.")
        inserted = save_to_mysql(cleaned)
        flash(f"Imported {inserted} row(s). Quality report: {report}", "success")
    except (ValueError, pd.errors.ParserError, Error, UnicodeDecodeError) as exc:
        flash(f"Upload failed: {exc}", "error")
    return redirect(url_for("index"))

@app.route("/sample")
def sample():
    path = os.path.join("data", "sample_weather.csv")
    return send_file(path, as_attachment=True)

@app.route("/clear-charts", methods=["POST"])
def clear_charts():
    # Does not delete database records; this route simply refreshes the dashboard.
    flash("Dashboard refreshed. Database records were not deleted.", "success")
    return redirect(url_for("index"))

@app.errorhandler(413)
def too_large(_):
    flash("File is too large. Maximum upload size is 10 MB.", "error")
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True)
