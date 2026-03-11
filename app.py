# JobRadar - Flask Backend (PostgreSQL Edition)
# ─────────────────────────────────────────────────────────────
# Storage: Railway PostgreSQL (persistent across redeploys)
# Fallback: JSON files if DATABASE_URL is not set (local dev)
# ─────────────────────────────────────────────────────────────

from flask import Flask, jsonify, request, send_file, send_from_directory
from flask_cors import CORS
import requests, datetime, json, os, time, threading, schedule, pathlib

BASE_DIR  = pathlib.Path(__file__).parent
FRONTEND  = BASE_DIR

app = Flask(__name__)
CORS(app)

ADZUNA_APP_ID  = os.environ.get("ADZUNA_APP_ID",  "")
ADZUNA_APP_KEY = os.environ.get("ADZUNA_APP_KEY", "")
RAPIDAPI_KEY   = os.environ.get("RAPIDAPI_KEY",   "")
DATABASE_URL   = os.environ.get("DATABASE_URL",   "")  # Railway sets this automatically

DATA_FILE = str(BASE_DIR / "jobs_data.json")   # fallback for local dev
LOG_FILE  = str(BASE_DIR / "search_log.json")  # fallback for local dev

YOUR_SKILLS = [
    "seo","google ads","meta ads","performance marketing","ga4","google analytics",
    "looker studio","semrush","ahrefs","python","ai","automation","b2b","saas",
    "fmcg","ecommerce","cro","roas","cpa","cpc","gtm","hubspot","wordpress",
    "shopify","technical seo","link building","content strategy","multilingual",
]

SEARCH_QUERIES = [
    "performance marketing manager",
    "SEO manager",
    "digital marketing manager",
    "growth marketing manager",
    "AI marketing specialist",
]

# ── DATABASE SETUP ──

def get_db_connection():
    """Return a psycopg2 connection using DATABASE_URL from Railway."""
    try:
        import psycopg2
        import psycopg2.extras
        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        return conn
    except Exception as e:
        print(f"[DB] Connection error: {e}")
        return None

def init_db():
    """Create tables if they don't exist yet."""
    if not DATABASE_URL:
        print("[DB] No DATABASE_URL — using JSON file fallback.")
        return
    conn = get_db_connection()
    if not conn:
        return
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    id          TEXT PRIMARY KEY,
                    title       TEXT,
                    company     TEXT,
                    location    TEXT,
                    platform    TEXT,
                    salary      TEXT,
                    match       INTEGER,
                    url         TEXT,
                    posted      TEXT,
                    status      TEXT DEFAULT 'Pending',
                    hot         BOOLEAN DEFAULT FALSE,
                    tags        JSONB DEFAULT '[]',
                    hr_url      TEXT,
                    description TEXT,
                    created_at  TIMESTAMP DEFAULT NOW()
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS search_logs (
                    id         SERIAL PRIMARY KEY,
                    date       TEXT,
                    time       TEXT,
                    jobs_found INTEGER,
                    new_added  INTEGER,
                    status     TEXT,
                    created_at TIMESTAMP DEFAULT NOW()
                );
            """)
            conn.commit()
        print("[DB] Tables ready.")
    except Exception as e:
        print(f"[DB] init_db error: {e}")
    finally:
        conn.close()

# ── DATA LAYER: PostgreSQL with JSON fallback ──

def load_data():
    """Load jobs from PostgreSQL or fallback to JSON file."""
    if DATABASE_URL:
        conn = get_db_connection()
        if conn:
            try:
                import psycopg2.extras
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute(
                        "SELECT * FROM jobs ORDER BY match DESC, created_at DESC LIMIT 100"
                    )
                    jobs = [dict(row) for row in cur.fetchall()]
                    for j in jobs:
                        j['hrUrl'] = j.pop('hr_url', '')
                        j['hot']   = bool(j.get('hot', False))
                        j['tags']  = j.get('tags') or []
                    cur.execute("SELECT MAX(created_at) AS last FROM jobs")
                    row  = cur.fetchone()
                    last = str(row['last']) if row and row['last'] else None
                return {"jobs": jobs, "last_updated": last, "stats": {}}
            except Exception as e:
                print(f"[load_data] DB error: {e}")
            finally:
                conn.close()
    # JSON fallback
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE) as f:
                return json.load(f)
        except Exception as e:
            print(f"[load_data] JSON error: {e}")
    return {"jobs": [], "last_updated": None, "stats": {}}

def save_jobs_to_db(new_jobs):
    """Upsert new jobs into PostgreSQL."""
    if not DATABASE_URL or not new_jobs:
        return
    conn = get_db_connection()
    if not conn:
        return
    try:
        with conn.cursor() as cur:
            for job in new_jobs:
                cur.execute("""
                    INSERT INTO jobs
                        (id, title, company, location, platform, salary, match,
                         url, posted, status, hot, tags, hr_url, description)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT (id) DO NOTHING
                """, (
                    job['id'], job['title'], job['company'], job['location'],
                    job['platform'], job['salary'], job['match'],
                    job['url'], job['posted'], job.get('status', 'Pending'),
                    job.get('hot', False),
                    json.dumps(job.get('tags', [])),
                    job.get('hrUrl', ''), job.get('description', '')
                ))
            # Keep only latest 100 jobs
            cur.execute("""
                DELETE FROM jobs WHERE id NOT IN (
                    SELECT id FROM jobs ORDER BY created_at DESC LIMIT 100
                )
            """)
            conn.commit()
        print(f"[DB] Saved {len(new_jobs)} jobs.")
    except Exception as e:
        print(f"[save_jobs_to_db] Error: {e}")
    finally:
        conn.close()

def update_job_status_db(job_id, new_status):
    """Update a single job's status in PostgreSQL."""
    if not DATABASE_URL:
        return False
    conn = get_db_connection()
    if not conn:
        return False
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE jobs SET status=%s WHERE id=%s", (new_status, job_id))
            conn.commit()
        return True
    except Exception as e:
        print(f"[update_job_status_db] Error: {e}")
        return False
    finally:
        conn.close()

def save_log_to_db(entry):
    """Append a search log entry to PostgreSQL."""
    if not DATABASE_URL:
        return
    conn = get_db_connection()
    if not conn:
        return
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO search_logs (date, time, jobs_found, new_added, status)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                entry['date'], entry['time'],
                entry['jobs_found'], entry['new_added'], entry['status']
            ))
            cur.execute("""
                DELETE FROM search_logs WHERE id NOT IN (
                    SELECT id FROM search_logs ORDER BY created_at DESC LIMIT 90
                )
            """)
            conn.commit()
    except Exception as e:
        print(f"[save_log_to_db] Error: {e}")
    finally:
        conn.close()

def load_logs_from_db():
    """Load search logs from PostgreSQL or JSON fallback."""
    if DATABASE_URL:
        conn = get_db_connection()
        if conn:
            try:
                import psycopg2.extras
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute(
                        "SELECT * FROM search_logs ORDER BY created_at DESC LIMIT 90"
                    )
                    return [dict(row) for row in cur.fetchall()]
            except Exception as e:
                print(f"[load_logs_from_db] Error: {e}")
            finally:
                conn.close()
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE) as f:
                return json.load(f)
        except:
            pass
    return []

# ── JSON FILE FALLBACK (local dev / no DB) ──

def save_data_json(data):
    try:
        with open(DATA_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"[save_data_json] Error: {e}")

def save_log_json(entry):
    try:
        logs = []
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE) as f:
                logs = json.load(f)
        logs.append(entry)
        with open(LOG_FILE, "w") as f:
            json.dump(logs[-90:], f, indent=2)
    except Exception as e:
        print(f"[save_log_json] Error: {e}")

# ── SCORING ──

def score_job(title, desc, location):
    text = (title + " " + desc + " " + location).lower()
    score = 50
    score += min(sum(1 for s in YOUR_SKILLS if s in text) * 4, 30)
    if any(l in text for l in ["germany","berlin","munich","remote","europe"]):
        score += 10
    if any(w in title.lower() for w in ["senior","lead","manager","specialist","expert"]):
        score += 5
    if any(w in title.lower() for w in ["intern","trainee","junior","entry"]):
        score -= 30
    return max(0, min(100, score))

# ── ADZUNA FETCH ──

def fetch_adzuna(query, country="de", n=5):
    jobs = []
    if not ADZUNA_APP_ID or not ADZUNA_APP_KEY:
        print("[fetch_adzuna] WARNING: Adzuna credentials not configured.")
        return jobs
    url = (
        f"https://api.adzuna.com/v1/api/jobs/{country}/search/1"
        f"?app_id={ADZUNA_APP_ID}&app_key={ADZUNA_APP_KEY}"
        f"&results_per_page={n}&what={requests.utils.quote(query)}"
        f"&sort_by=date&max_days_old=7"
    )
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        for job in r.json().get("results", []):
            title    = job.get("title", "")
            company  = job.get("company", {}).get("display_name", "N/A")
            location = job.get("location", {}).get("display_name", "")
            desc     = job.get("description", "")
            link     = job.get("redirect_url", "")
            s_min    = job.get("salary_min")
            s_max    = job.get("salary_max")
            salary   = f"€{int(s_min):,}–€{int(s_max):,}" if s_min and s_max else "See listing"
            sc       = score_job(title, desc, location)
            if sc >= 65:
                jobs.append({
                    "id":          f"{country}-{abs(hash(title + company)) % 99999}",
                    "title":       title,
                    "company":     company,
                    "location":    location,
                    "platform":    f"Adzuna {country.upper()}",
                    "salary":      salary,
                    "match":       sc,
                    "url":         link,
                    "posted":      datetime.date.today().isoformat(),
                    "status":      "Pending",
                    "hot":         sc >= 90,
                    "tags":        [],
                    "hrUrl":       (
                        f"https://www.linkedin.com/search/results/people/"
                        f"?keywords=HR+Recruiter+{requests.utils.quote(company)}"
                    ),
                    "description": desc[:300],
                })
    except Exception as e:
        print(f"[fetch_adzuna] Error ({country}): {e}")
    return jobs

# ── JOB SEARCH ──

def run_job_search():
    try:
        print(f"[{datetime.datetime.now()}] Running job search...")
        all_jobs = []
        for q in SEARCH_QUERIES[:3]:
            all_jobs += fetch_adzuna(q, "de", 5)
            all_jobs += fetch_adzuna(q, "gb", 3)
            time.sleep(1)

        seen, unique = set(), []
        for job in all_jobs:
            k = f"{job['title'].lower()[:30]}|{job['company'].lower()[:20]}"
            if k not in seen:
                seen.add(k)
                unique.append(job)
        unique.sort(key=lambda x: x["match"], reverse=True)

        log_entry = {
            "date":       datetime.date.today().isoformat(),
            "time":       datetime.datetime.now().strftime("%H:%M"),
            "jobs_found": len(unique),
            "new_added":  0,
            "status":     "Success",
        }

        if DATABASE_URL:
            existing     = load_data()
            existing_ids = {j["id"] for j in existing["jobs"]}
            new_jobs     = [j for j in unique if j["id"] not in existing_ids]
            save_jobs_to_db(new_jobs)
            log_entry["new_added"] = len(new_jobs)
            save_log_to_db(log_entry)
            print(f"[DB] Done: {len(unique)} found, {len(new_jobs)} new")
        else:
            data = {}
            if os.path.exists(DATA_FILE):
                try:
                    with open(DATA_FILE) as f:
                        data = json.load(f)
                except:
                    pass
            data.setdefault("jobs", [])
            existing_ids = {j["id"] for j in data["jobs"]}
            new_jobs     = [j for j in unique if j["id"] not in existing_ids]
            data["jobs"] = (new_jobs + data["jobs"])[:100]
            data["last_updated"] = datetime.datetime.now().isoformat()
            save_data_json(data)
            log_entry["new_added"] = len(new_jobs)
            save_log_json(log_entry)
            print(f"[JSON] Done: {len(unique)} found, {len(new_jobs)} new")

        return len(unique), log_entry["new_added"]
    except Exception as e:
        print(f"[run_job_search] EXCEPTION: {e}")
        return 0, 0

def start_scheduler():
    try:
        schedule.every().day.at("09:00").do(run_job_search)
        while True:
            schedule.run_pending()
            time.sleep(60)
    except Exception as e:
        print(f"[start_scheduler] EXCEPTION: {e}")

def _delayed_start():
    print("[JobRadar] Waiting 30s before first search...")
    time.sleep(30)
    run_job_search()
    start_scheduler()

_threads_started = False

def _start_background_tasks():
    global _threads_started
    if not _threads_started:
        _threads_started = True
        try:
            threading.Thread(target=_delayed_start, daemon=True).start()
            print("[JobRadar] Background thread started.")
        except Exception as e:
            print(f"[JobRadar] Thread start failed: {e}")

# ── ROUTES ──

@app.route('/')
def index():
    try:
        f = FRONTEND / 'index.html'
        if f.exists():
            return send_file(str(f))
    except Exception as e:
        print(f"[index] {e}")
    return "<h1>JobRadar API Running</h1><p><a href='/api/jobs'>View Jobs API</a></p>"

@app.route('/dashboard')
def dashboard():
    try:
        f = FRONTEND / 'dashboard.html'
        if f.exists():
            return send_file(str(f))
    except Exception as e:
        print(f"[dashboard] {e}")
    return "Dashboard not found", 404

@app.route('/<path:filename>')
def static_files(filename):
    if filename.startswith('api/'):
        return "Not found", 404
    try:
        if (FRONTEND / filename).exists():
            return send_from_directory(str(FRONTEND), filename)
    except Exception as e:
        print(f"[static_files] {e}")
    return "Not found", 404

@app.route('/api/jobs', methods=['GET'])
def get_jobs():
    data = load_data()
    jobs = data.get("jobs", [])
    q = request.args.get('q', '').lower()
    if q:
        jobs = [j for j in jobs if q in j['title'].lower() or q in j['company'].lower()]
    return jsonify({"jobs": jobs, "total": len(jobs), "last_updated": data.get("last_updated")})

@app.route('/api/jobs/<job_id>/status', methods=['PUT'])
def update_status(job_id):
    new_status = request.json.get('status')
    if DATABASE_URL:
        success = update_job_status_db(job_id, new_status)
        return jsonify({"success": success})
    data = load_data()
    for job in data['jobs']:
        if str(job['id']) == str(job_id):
            job['status'] = new_status
            break
    save_data_json(data)
    return jsonify({"success": True})

@app.route('/api/search/run', methods=['POST'])
def trigger_search():
    found, added = run_job_search()
    return jsonify({"success": True, "found": found, "added": added})

@app.route('/api/stats', methods=['GET'])
def get_stats():
    data = load_data()
    jobs = data.get("jobs", [])
    status_counts = {}
    for j in jobs:
        s = j.get("status", "Pending")
        status_counts[s] = status_counts.get(s, 0) + 1
    return jsonify({
        "total_jobs":       len(jobs),
        "last_updated":     data.get("last_updated"),
        "status_breakdown": status_counts,
        "storage":          "postgresql" if DATABASE_URL else "json_file",
    })

@app.route('/api/logs', methods=['GET'])
def get_logs():
    return jsonify({"logs": load_logs_from_db()})

@app.route('/api/health', methods=['GET'])
def health():
    db_ok = False
    if DATABASE_URL:
        conn = get_db_connection()
        if conn:
            db_ok = True
            conn.close()
    return jsonify({
        "status":            "ok",
        "time":              datetime.datetime.now().isoformat(),
        "frontend_dir":      str(FRONTEND),
        "index_exists":      (FRONTEND / 'index.html').exists(),
        "dashboard_exists":  (FRONTEND / 'dashboard.html').exists(),
        "data_file_exists":  os.path.exists(DATA_FILE),
        "adzuna_configured": bool(ADZUNA_APP_ID and ADZUNA_APP_KEY),
        "storage":           "postgresql" if DATABASE_URL else "json_file",
        "db_connected":      db_ok,
    })

# ── STARTUP ──
init_db()
_start_background_tasks()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    print(f"Starting JobRadar on port {port}")
    app.run(debug=False, host='0.0.0.0', port=port)
