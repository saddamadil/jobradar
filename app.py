# backend/app.py
# Flask API backend for JobRadar
# Run: python app.py

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import requests, datetime, json, os, time, threading, schedule, pathlib

import pathlib
BASE_DIR = pathlib.Path(__file__).parent
app = Flask(__name__, static_folder=str(BASE_DIR / 'frontend'), static_url_path='')
CORS(app)

# ── CONFIG ──
ADZUNA_APP_ID  = os.environ.get("ADZUNA_APP_ID",  "1563122a")
ADZUNA_APP_KEY = os.environ.get("ADZUNA_APP_KEY", "a4e3eb7e12b27898eeac2244f9a198f7")
RAPIDAPI_KEY   = os.environ.get("RAPIDAPI_KEY",   "")
DATA_FILE      = "jobs_data.json"
LOG_FILE       = "search_log.json"

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

# ── HELPERS ──
def score_job(title, desc, location):
    text = (title+" "+desc+" "+location).lower()
    score = 50
    score += min(sum(1 for s in YOUR_SKILLS if s in text)*4, 30)
    if any(l in text for l in ["germany","berlin","munich","remote","europe"]): score += 10
    if any(w in title.lower() for w in ["senior","lead","manager","specialist","expert"]): score += 5
    if any(w in title.lower() for w in ["intern","trainee","junior","entry"]): score -= 30
    return max(0, min(100, score))

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE) as f: return json.load(f)
        except: pass
    return {"jobs": [], "last_updated": None, "stats": {"total_applied":0,"interviews":0,"hr_contacted":0}}

def save_data(data):
    with open(DATA_FILE, "w") as f: json.dump(data, f, indent=2)

def load_log():
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE) as f: return json.load(f)
        except: pass
    return []

def save_log(entry):
    log = load_log()
    log.append(entry)
    with open(LOG_FILE, "w") as f: json.dump(log[-90:], f, indent=2)

# ── ADZUNA SEARCH ──
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
            salary   = f"€{int(s_min):,}–€{int(s_max):,}" if s_min and s_max else "See listing"
            score    = score_job(title, desc, location)
            if score >= 65:
                jobs.append({
                    "id": f"{country}-{hash(title+company) % 99999}",
                    "title": title, "company": company, "location": location,
                    "platform": f"Adzuna {country.upper()}", "salary": salary,
                    "match": score, "url": link,
                    "posted": datetime.date.today().isoformat(),
                    "status": "Pending", "hot": score >= 90,
                    "tags": [q.split()[0].title() for q in SEARCH_QUERIES[:3]],
                    "hrUrl": f"https://www.linkedin.com/search/results/people/?keywords=HR+Recruiter+{requests.utils.quote(company)}",
                    "description": desc[:300],
                })
    except Exception as e:
        print(f"Adzuna error ({country}): {e}")
    return jobs

def fetch_jsearch(query, n=5):
    if not RAPIDAPI_KEY: return []
    jobs = []
    url = "https://jsearch.p.rapidapi.com/search"
    headers = {"X-RapidAPI-Key": RAPIDAPI_KEY, "X-RapidAPI-Host": "jsearch.p.rapidapi.com"}
    params = {"query": f"{query} in Germany Europe Remote", "page":"1","num_pages":"1","date_posted":"week"}
    try:
        r = requests.get(url, headers=headers, params=params, timeout=12)
        r.raise_for_status()
        for job in r.json().get("data",[])[:n]:
            title    = job.get("job_title","")
            company  = job.get("employer_name","N/A")
            location = f"{job.get('job_city','')}, {job.get('job_country','')}".strip(", ")
            desc     = job.get("job_description","")
            link     = job.get("job_apply_link") or job.get("job_google_link","")
            score    = score_job(title, desc, location)
            if score >= 65:
                jobs.append({
                    "id": f"js-{hash(title+company) % 99999}",
                    "title": title, "company": company, "location": location,
                    "platform": "JSearch", "salary": "See listing",
                    "match": score, "url": link,
                    "posted": datetime.date.today().isoformat(),
                    "status": "Pending", "hot": score >= 90,
                    "tags": [], "hrUrl": "",
                    "description": desc[:300],
                })
    except Exception as e:
        print(f"JSearch error: {e}")
    return jobs

def run_job_search():
    print(f"\n[{datetime.datetime.now()}] Running job search...")
    all_jobs = []

    for q in SEARCH_QUERIES[:3]:
        all_jobs += fetch_adzuna(q, "de", 5)
        all_jobs += fetch_adzuna(q, "gb", 3)
        time.sleep(1)

    for q in SEARCH_QUERIES[:2]:
        all_jobs += fetch_jsearch(q, 5)
        time.sleep(1)

    # Deduplicate
    seen, unique = set(), []
    for job in all_jobs:
        k = f"{job['title'].lower()[:30]}|{job['company'].lower()[:20]}"
        if k not in seen:
            seen.add(k)
            unique.append(job)

    unique.sort(key=lambda x: x["match"], reverse=True)

    data = load_data()
    existing_ids = {j["id"] for j in data["jobs"]}
    new_jobs = [j for j in unique if j["id"] not in existing_ids]

    # Keep last 100 jobs
    data["jobs"] = (new_jobs + data["jobs"])[:100]
    data["last_updated"] = datetime.datetime.now().isoformat()
    save_data(data)

    log_entry = {
        "date": datetime.date.today().isoformat(),
        "time": datetime.datetime.now().strftime("%H:%M"),
        "sources": ["Adzuna DE", "Adzuna GB"] + (["JSearch"] if RAPIDAPI_KEY else []),
        "jobs_found": len(unique),
        "new_added": len(new_jobs),
        "status": "Success"
    }
    save_log(log_entry)
    print(f"  Done: {len(unique)} found, {len(new_jobs)} new")
    return len(unique), len(new_jobs)

# ── ROUTES ──

@app.route('/')
def index():
    return send_from_directory('../frontend', 'index.html')

@app.route('/dashboard')
def dashboard():
    return send_from_directory('../frontend', 'dashboard.html')

@app.route('/api/jobs', methods=['GET'])
def get_jobs():
    data = load_data()
    jobs = data.get("jobs", [])
    # Optional filters
    q = request.args.get('q','').lower()
    remote = request.args.get('remote','')
    if q:
        jobs = [j for j in jobs if q in j['title'].lower() or q in j['company'].lower()]
    if remote == 'true':
        jobs = [j for j in jobs if 'remote' in j['location'].lower() or 'remote' in j['type'].lower() if 'type' in j]
    return jsonify({
        "jobs": jobs,
        "total": len(jobs),
        "last_updated": data.get("last_updated"),
        "stats": data.get("stats", {})
    })

@app.route('/api/jobs/<job_id>/status', methods=['PUT'])
def update_status(job_id):
    data = load_data()
    new_status = request.json.get('status')
    for job in data['jobs']:
        if str(job['id']) == str(job_id):
            job['status'] = new_status
            break
    save_data(data)
    return jsonify({"success": True, "status": new_status})

@app.route('/api/search/run', methods=['POST'])
def trigger_search():
    found, added = run_job_search()
    return jsonify({"success": True, "found": found, "added": added,
                    "message": f"Search complete: {found} jobs found, {added} new"})

@app.route('/api/stats', methods=['GET'])
def get_stats():
    data = load_data()
    jobs = data.get("jobs", [])
    status_counts = {}
    for j in jobs:
        s = j.get("status","Pending")
        status_counts[s] = status_counts.get(s,0)+1
    return jsonify({
        "total_jobs": len(jobs),
        "last_updated": data.get("last_updated"),
        "status_breakdown": status_counts,
        "api_status": "connected" if ADZUNA_APP_ID != "YOUR_ADZUNA_APP_ID" else "not_configured",
    })

@app.route('/api/logs', methods=['GET'])
def get_logs():
    return jsonify({"logs": load_log()})

@app.route('/api/config', methods=['GET','POST'])
def config():
    if request.method == 'POST':
        cfg = request.json
        # In production: save to .env or config file
        return jsonify({"success": True, "message": "Config saved"})
    return jsonify({
        "adzuna_configured": ADZUNA_APP_ID != "YOUR_ADZUNA_APP_ID",
        "jsearch_configured": bool(RAPIDAPI_KEY),
        "search_queries": SEARCH_QUERIES,
        "schedule": "Daily at 9:00 AM"
    })

# ── SCHEDULER ──
def start_scheduler():
    schedule.every().day.at("09:00").do(run_job_search)
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == '__main__':
    print("="*50)
    print("  JobRadar Backend API")
    print(f"  Adzuna: {'✅ Connected' if ADZUNA_APP_ID != 'YOUR_ADZUNA_APP_ID' else '❌ Not configured'}")
    print(f"  Running at: http://localhost:5000")
    print("="*50)

    # Run initial search on startup
    t = threading.Thread(target=run_job_search, daemon=True)
    t.start()

    # Start scheduler in background
    s = threading.Thread(target=start_scheduler, daemon=True)
    s.start()

    app.run(debug=False, host='0.0.0.0', port=5000)
