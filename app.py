# JobRadar - Flask Backend with PostgreSQL
from flask import Flask, jsonify, request, Response
from flask_cors import CORS
import requests, datetime, json, os, time, threading, schedule

# PostgreSQL support
try:
    import psycopg2
    import psycopg2.extras
    HAS_PG = True
except ImportError:
    HAS_PG = False

app = Flask(__name__)
CORS(app)

ADZUNA_APP_ID  = os.environ.get("ADZUNA_APP_ID",  "1563122a")
ADZUNA_APP_KEY = os.environ.get("ADZUNA_APP_KEY", "a4e3eb7e12b27898eeac2244f9a198f7")
DATABASE_URL   = os.environ.get("DATABASE_URL", "")
DATA_FILE      = "/tmp/jobs_data.json"
LOG_FILE       = "/tmp/search_log.json"


# ── HTML FILES ──
import pathlib
_BASE = pathlib.Path(__file__).parent

def _read_html(name):
    """Read HTML file from disk - serves CIA theme files."""
    f = _BASE / name
    if f.exists():
        return f.read_text(encoding="utf-8")
    return f"<h1>Error: {name} not found</h1>"

# ── DATABASE ──

def get_db():
    if HAS_PG and DATABASE_URL:
        try:
            conn = psycopg2.connect(DATABASE_URL, sslmode="require")
            return conn
        except Exception as e:
            print(f"DB connect error: {e}")
    return None

def init_db():
    conn = get_db()
    if not conn: return False
    try:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                title TEXT, company TEXT, location TEXT,
                platform TEXT, salary TEXT, match_score INTEGER,
                url TEXT, posted DATE, status TEXT DEFAULT 'Pending',
                hot BOOLEAN DEFAULT FALSE, hr_url TEXT,
                description TEXT, created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS search_log (
                id SERIAL PRIMARY KEY,
                run_date DATE, run_time TEXT,
                jobs_found INTEGER, new_added INTEGER,
                status TEXT, created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        conn.commit()
        cur.close()
        conn.close()
        print("✅ Database initialized")
        return True
    except Exception as e:
        print(f"DB init error: {e}")
        return False

def save_jobs_db(jobs):
    conn = get_db()
    if not conn:
        print("save_jobs_db: no DB connection")
        return 0
    added = 0
    try:
        cur = conn.cursor()
        # Ensure table exists
        cur.execute("""CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY, title TEXT, company TEXT, location TEXT,
            platform TEXT, salary TEXT, match_score INTEGER,
            url TEXT, posted TEXT, status TEXT DEFAULT 'Pending',
            hot BOOLEAN DEFAULT FALSE, hr_url TEXT, description TEXT,
            created_at TIMESTAMP DEFAULT NOW())""")
        conn.commit()
        for job in jobs:
            try:
                cur.execute("""
                    INSERT INTO jobs (id, title, company, location, platform, salary,
                        match_score, url, posted, status, hot, hr_url, description)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT (id) DO NOTHING
                """, (
                    str(job["id"]), str(job["title"]), str(job["company"]),
                    str(job["location"]), str(job["platform"]), str(job["salary"]),
                    int(job["match"]), str(job["url"]), str(job.get("posted","")),
                    str(job.get("status","Pending")), bool(job.get("hot",False)),
                    str(job.get("hrUrl","")), str(job.get("description",""))[:500]
                ))
                if cur.rowcount > 0:
                    added += 1
            except Exception as e:
                print(f"Row insert error: {e} — {job.get('title','?')}")
                continue
        conn.commit()
        cur.close()
        conn.close()
        print(f"save_jobs_db: saved {added} new jobs")
    except Exception as e:
        print(f"DB save error: {e}")
        import traceback; traceback.print_exc()
    return added

def load_jobs_db(search=None):
    conn = get_db()
    if not conn: return []
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        if search:
            cur.execute("""SELECT * FROM jobs WHERE title ILIKE %s OR company ILIKE %s
                          ORDER BY match_score DESC, created_at DESC LIMIT 100""",
                       (f"%{search}%", f"%{search}%"))
        else:
            cur.execute("SELECT * FROM jobs ORDER BY match_score DESC, created_at DESC LIMIT 100")
        jobs = []
        for row in cur.fetchall():
            jobs.append({
                "id": row["id"], "title": row["title"], "company": row["company"],
                "location": row["location"], "platform": row["platform"],
                "salary": row["salary"], "match": row["match_score"],
                "url": row["url"], "posted": str(row["posted"]),
                "status": row["status"], "hot": row["hot"],
                "hrUrl": row["hr_url"], "description": row["description"],
                "tags": [],
            })
        cur.close()
        conn.close()
        return jobs
    except Exception as e:
        print(f"DB load error: {e}")
        return []

def update_job_status_db(job_id, status):
    conn = get_db()
    if not conn: return False
    try:
        cur = conn.cursor()
        cur.execute("UPDATE jobs SET status=%s WHERE id=%s", (status, job_id))
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"DB update error: {e}")
        return False

def save_log_db(entry):
    conn = get_db()
    if not conn:
        # fallback to file
        log = []
        if os.path.exists(LOG_FILE):
            try:
                with open(LOG_FILE) as f: log = json.load(f)
            except: pass
        log.append(entry)
        with open(LOG_FILE, "w") as f: json.dump(log[-90:], f)
        return
    try:
        cur = conn.cursor()
        cur.execute("""INSERT INTO search_log (run_date, run_time, jobs_found, new_added, status)
                      VALUES (%s,%s,%s,%s,%s)""",
                   (entry["date"], entry["time"], entry["jobs_found"], entry["new_added"], entry["status"]))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"DB log error: {e}")

def load_log_db():
    conn = get_db()
    if not conn:
        if os.path.exists(LOG_FILE):
            try:
                with open(LOG_FILE) as f: return json.load(f)
            except: pass
        return []
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM search_log ORDER BY created_at DESC LIMIT 30")
        logs = [dict(row) for row in cur.fetchall()]
        for l in logs:
            if "created_at" in l: l["created_at"] = str(l["created_at"])
            if "run_date" in l: l["run_date"] = str(l["run_date"])
        cur.close()
        conn.close()
        return logs
    except Exception as e:
        print(f"DB log load error: {e}")
        return []

# ── SCORING ──

def score_job(title, desc, location):
    text = (title+" "+desc+" "+location).lower()
    score = 50
    score += min(sum(1 for s in YOUR_SKILLS if s in text)*4, 30)
    if any(l in text for l in ["germany","berlin","munich","remote","europe"]): score += 10
    if any(w in title.lower() for w in ["senior","lead","manager","specialist","expert"]): score += 5
    if any(w in title.lower() for w in ["intern","trainee","junior","entry"]): score -= 30
    return max(0, min(100, score))

# ── ADZUNA ──

def fetch_adzuna(query, country="de", n=5):
    jobs = []
    url = (f"https://api.adzuna.com/v1/api/jobs/{country}/search/1"
           f"?app_id={ADZUNA_APP_ID}&app_key={ADZUNA_APP_KEY}"
           f"&results_per_page={n}&what={requests.utils.quote(query)}&sort_by=date&max_days_old=7")
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        for job in r.json().get("results", []):
            title    = job.get("title","")
            company  = job.get("company",{}).get("display_name","N/A")
            location = job.get("location",{}).get("display_name","")
            desc     = job.get("description","")
            link     = job.get("redirect_url","")
            s_min    = job.get("salary_min")
            s_max    = job.get("salary_max")
            salary   = f"EUR {int(s_min):,}-{int(s_max):,}" if s_min and s_max else "See listing"
            sc       = score_job(title, desc, location)
            if sc >= 65:
                jobs.append({
                    "id": f"{country}-{abs(hash(title+company)) % 999999}",
                    "title":title,"company":company,"location":location,
                    "platform":f"Adzuna {country.upper()}","salary":salary,
                    "match":sc,"url":link,
                    "posted":str(datetime.date.today()),
                    "status":"Pending","hot":sc>=90,"tags":[],
                    "hrUrl":f"https://www.linkedin.com/search/results/people/?keywords=HR+{requests.utils.quote(company)}",
                    "description":desc[:500],
                })
    except Exception as e:
        print(f"Adzuna error ({country}): {e}")
    return jobs

# ── JOB SEARCH ──

def run_job_search():
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

    # Save to DB (or fallback JSON)
    if DATABASE_URL and HAS_PG:
        added = save_jobs_db(unique)
    else:
        # JSON fallback
        data = {}
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE) as f: data = json.load(f)
            except: pass
        existing = {j["id"] for j in data.get("jobs",[])}
        new_jobs  = [j for j in unique if j["id"] not in existing]
        data["jobs"] = (new_jobs + data.get("jobs",[]))[:100]
        data["last_updated"] = datetime.datetime.now().isoformat()
        with open(DATA_FILE,"w") as f: json.dump(data, f)
        added = len(new_jobs)

    save_log_db({"date":datetime.date.today().isoformat(),
                 "time":datetime.datetime.now().strftime("%H:%M"),
                 "jobs_found":len(unique),"new_added":added,"status":"Success"})
    print(f"Done: {len(unique)} found, {added} new")
    return len(unique), added

# ── ROUTES ──

@app.route("/")
def index():
    return Response(_read_html("index.html"), mimetype="text/html")

@app.route("/dashboard")
def dashboard():
    return Response(_read_html("dashboard.html"), mimetype="text/html")

@app.route("/api/jobs")
def get_jobs():
    q = request.args.get("q","").lower()
    if DATABASE_URL and HAS_PG:
        jobs = load_jobs_db(q if q else None)
        last = datetime.datetime.now().isoformat()
    else:
        data = {}
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE) as f: data = json.load(f)
            except: pass
        jobs = data.get("jobs",[])
        if q: jobs = [j for j in jobs if q in j["title"].lower() or q in j["company"].lower()]
        last = data.get("last_updated")
    return jsonify({"jobs":jobs,"total":len(jobs),"last_updated":last})

@app.route("/api/jobs/<job_id>/status", methods=["PUT"])
def update_status(job_id):
    new_status = request.json.get("status")
    if DATABASE_URL and HAS_PG:
        update_job_status_db(job_id, new_status)
    return jsonify({"success":True})

@app.route("/api/search/run", methods=["GET","POST"])
def trigger_search():
    found, added = run_job_search()
    return jsonify({"success":True,"found":found,"added":added,
                    "message":f"{found} jobs found, {added} new added"})

@app.route("/api/stats")
def get_stats():
    if DATABASE_URL and HAS_PG:
        jobs = load_jobs_db()
        db_ok = get_db() is not None
    else:
        data = {}
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE) as f: data = json.load(f)
            except: pass
        jobs = data.get("jobs",[])
        db_ok = False
    status_counts = {}
    for j in jobs:
        s = j.get("status","Pending")
        status_counts[s] = status_counts.get(s,0)+1
    return jsonify({"total_jobs":len(jobs),"status_breakdown":status_counts,"db_connected":db_ok})

@app.route("/api/health")
def health():
    db_ok = False
    if DATABASE_URL and HAS_PG:
        conn = get_db()
        if conn:
            db_ok = True
            conn.close()
    return jsonify({
        "status":"ok",
        "time":datetime.datetime.now().isoformat(),
        "adzuna_configured": ADZUNA_APP_ID != "YOUR_ADZUNA_APP_ID",
        "db_connected": db_ok,
        "storage": "postgresql" if db_ok else "json_file",
        "frontend_dir": "/app",
        "index_exists": True,
        "dashboard_exists": True,
        "data_file_exists": os.path.exists(DATA_FILE),
    })

@app.route("/api/logs")
def get_logs():
    return jsonify({"logs":load_log_db()})

@app.route("/status")
def status_page():
    try:
        jobs = load_jobs_db() if (DATABASE_URL and HAS_PG) else []
        db_status = "PostgreSQL Connected" if (DATABASE_URL and HAS_PG) else "JSON file"
        rows = ""
        for j in jobs[:10]:
            rows += f"<tr><td><b>{j.get('match',0)}%</b></td><td>{j.get('title','')[:50]}</td><td>{j.get('company','')[:25]}</td><td>{j.get('location','')[:20]}</td><td>{j.get('posted','')}</td></tr>"
        html = f"""<!DOCTYPE html><html><head><title>JobRadar Status</title>
        <style>
        body{{font-family:Arial;background:#05080f;color:#e2e8f0;padding:40px;max-width:900px;margin:0 auto}}
        h1{{color:#3b82f6}} .card{{background:#0d1526;border:1px solid #1e3a5f;border-radius:12px;padding:20px;margin:16px 0}}
        .green{{color:#10b981}} .yellow{{color:#f59e0b}}
        .btn{{display:inline-block;padding:12px 24px;background:#3b82f6;color:white;border-radius:8px;text-decoration:none;margin:8px;font-weight:bold}}
        .btn2{{background:#10b981}}
        table{{width:100%;border-collapse:collapse;margin-top:12px}}
        td,th{{padding:10px 12px;border-bottom:1px solid #1e3a5f;text-align:left;font-size:13px}}
        th{{color:#64748b;font-size:11px;text-transform:uppercase}}
        </style></head><body>
        <h1>JobRadar Status</h1>
        <div class="card"><b>Database:</b> <span class="green">{db_status}</span></div>
        <div class="card"><b>Total Jobs Saved:</b> <span class="green">{len(jobs)}</span></div>
        <div class="card">
        <b>Latest Jobs:</b>
        <table><tr><th>Match</th><th>Title</th><th>Company</th><th>Location</th><th>Date</th></tr>
        {rows}
        </table></div>
        <a href="/api/search/run" class="btn">Run Job Search Now</a>
        <a href="/" class="btn btn2">Back to Job Board</a>
        </body></html>"""
        return html
    except Exception as e:
        return f"<h1>Status Error</h1><pre>{str(e)}</pre>", 500


@app.route("/api/test-insert")
def test_insert():
    conn = get_db()
    if not conn:
        return jsonify({"error": "no db connection"})
    results = {}
    try:
        cur = conn.cursor()
        # Create table fresh
        cur.execute("DROP TABLE IF EXISTS jobs")
        cur.execute("""CREATE TABLE jobs (
            id TEXT PRIMARY KEY,
            title TEXT, company TEXT, location TEXT,
            platform TEXT, salary TEXT, match_score INTEGER,
            url TEXT, posted TEXT, status TEXT DEFAULT 'Pending',
            hot BOOLEAN DEFAULT FALSE, hr_url TEXT, description TEXT,
            created_at TIMESTAMP DEFAULT NOW())""")
        conn.commit()
        results["table_created"] = True

        # Test insert
        cur.execute("""INSERT INTO jobs
            (id, title, company, location, platform, salary, match_score, url, posted, status, hot, hr_url, description)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            ("test-1", "SEO Manager", "Test GmbH", "Berlin", "Adzuna DE",
             "EUR 50,000", 90, "https://example.com", "2026-03-11",
             "Pending", False, "", "Test description"))
        conn.commit()
        results["test_insert"] = "success"

        # Verify
        cur.execute("SELECT COUNT(*) FROM jobs")
        results["count"] = cur.fetchone()[0]

        cur.close()
        conn.close()
    except Exception as e:
        results["error"] = str(e)
        import traceback
        results["traceback"] = traceback.format_exc()
    return jsonify(results)

@app.route("/api/debug")
def debug():
    results = {"db_url_set": bool(DATABASE_URL), "has_psycopg2": HAS_PG}
    conn = get_db()
    if conn:
        try:
            cur = conn.cursor()
            # Check if tables exist
            cur.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_name='jobs'")
            results["jobs_table_exists"] = cur.fetchone()[0] > 0
            if results["jobs_table_exists"]:
                cur.execute("SELECT COUNT(*) FROM jobs")
                results["jobs_count"] = cur.fetchone()[0]
            # Try creating tables
            cur.execute("""CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY, title TEXT, company TEXT, location TEXT,
                platform TEXT, salary TEXT, match_score INTEGER,
                url TEXT, posted TEXT, status TEXT DEFAULT 'Pending',
                hot BOOLEAN DEFAULT FALSE, hr_url TEXT, description TEXT,
                created_at TIMESTAMP DEFAULT NOW())""")
            conn.commit()
            results["table_created"] = True
            cur.close()
            conn.close()
            results["db_connected"] = True
        except Exception as e:
            results["db_error"] = str(e)
    else:
        results["db_connected"] = False
    return jsonify(results)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"JobRadar starting on port {port}")
    print(f"Database: {'PostgreSQL' if DATABASE_URL else 'JSON file'}")
    init_db()
    threading.Thread(target=run_job_search, daemon=True).start()
    threading.Thread(target=start_scheduler, daemon=True).start()
    app.run(debug=False, host="0.0.0.0", port=port)
