# JobRadar - Flask Backend
from flask import Flask, jsonify, request, send_file, send_from_directory
from flask_cors import CORS
import requests, datetime, json, os, time, threading, schedule, pathlib

BASE_DIR = pathlib.Path(__file__).parent
FRONTEND = BASE_DIR / 'frontend'

app = Flask(__name__)
CORS(app)

ADZUNA_APP_ID  = os.environ.get("ADZUNA_APP_ID",  "1563122a")
ADZUNA_APP_KEY = os.environ.get("ADZUNA_APP_KEY", "a4e3eb7e12b27898eeac2244f9a198f7")
RAPIDAPI_KEY   = os.environ.get("RAPIDAPI_KEY",   "")
DATA_FILE      = str(BASE_DIR / "jobs_data.json")
LOG_FILE       = str(BASE_DIR / "search_log.json")

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
    return {"jobs":[], "last_updated":None, "stats":{}}

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
            sc       = score_job(title, desc, location)
            if sc >= 65:
                jobs.append({
                    "id": f"{country}-{abs(hash(title+company)) % 99999}",
                    "title":title,"company":company,"location":location,
                    "platform":f"Adzuna {country.upper()}","salary":salary,
                    "match":sc,"url":link,
                    "posted":datetime.date.today().isoformat(),
                    "status":"Pending","hot":sc>=90,
                    "tags":[],
                    "hrUrl":f"https://www.linkedin.com/search/results/people/?keywords=HR+Recruiter+{requests.utils.quote(company)}",
                    "description":desc[:300],
                })
    except Exception as e:
        print(f"Adzuna error ({country}): {e}")
    return jobs

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
    data = load_data()
    existing_ids = {j["id"] for j in data["jobs"]}
    new_jobs = [j for j in unique if j["id"] not in existing_ids]
    data["jobs"] = (new_jobs + data["jobs"])[:100]
    data["last_updated"] = datetime.datetime.now().isoformat()
    save_data(data)
    save_log({"date":datetime.date.today().isoformat(),"time":datetime.datetime.now().strftime("%H:%M"),
              "jobs_found":len(unique),"new_added":len(new_jobs),"status":"Success"})
    print(f"Done: {len(unique)} found, {len(new_jobs)} new")
    return len(unique), len(new_jobs)

# ── ROUTES ──

@app.route('/')
def index():
    index_file = FRONTEND / 'index.html'
    if index_file.exists():
        return send_file(str(index_file))
    return "<h1>JobRadar API Running</h1><p><a href='/api/jobs'>View Jobs API</a></p>"

@app.route('/dashboard')
def dashboard():
    dash_file = FRONTEND / 'dashboard.html'
    if dash_file.exists():
        return send_file(str(dash_file))
    return "Dashboard not found", 404

@app.route('/<path:filename>')
def static_files(filename):
    if (FRONTEND / filename).exists():
        return send_from_directory(str(FRONTEND), filename)
    return "Not found", 404

@app.route('/api/jobs', methods=['GET'])
def get_jobs():
    data = load_data()
    jobs = data.get("jobs", [])
    q = request.args.get('q','').lower()
    if q:
        jobs = [j for j in jobs if q in j['title'].lower() or q in j['company'].lower()]
    return jsonify({"jobs":jobs,"total":len(jobs),"last_updated":data.get("last_updated")})

@app.route('/api/jobs/<job_id>/status', methods=['PUT'])
def update_status(job_id):
    data = load_data()
    new_status = request.json.get('status')
    for job in data['jobs']:
        if str(job['id']) == str(job_id):
            job['status'] = new_status
            break
    save_data(data)
    return jsonify({"success":True})

@app.route('/api/search/run', methods=['POST'])
def trigger_search():
    found, added = run_job_search()
    return jsonify({"success":True,"found":found,"added":added})

@app.route('/api/stats', methods=['GET'])
def get_stats():
    data = load_data()
    jobs = data.get("jobs",[])
    status_counts = {}
    for j in jobs:
        s = j.get("status","Pending")
        status_counts[s] = status_counts.get(s,0)+1
    return jsonify({"total_jobs":len(jobs),"last_updated":data.get("last_updated"),"status_breakdown":status_counts})

@app.route('/api/logs', methods=['GET'])
def get_logs():
    return jsonify({"logs":load_log()})

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({"status":"ok","time":datetime.datetime.now().isoformat()})

def start_scheduler():
    schedule.every().day.at("09:00").do(run_job_search)
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    print(f"Starting JobRadar on port {port}")
    print(f"Frontend dir: {FRONTEND} (exists: {FRONTEND.exists()})")
    t = threading.Thread(target=run_job_search, daemon=True)
    t.start()
    s = threading.Thread(target=start_scheduler, daemon=True)
    s.start()
    app.run(debug=False, host='0.0.0.0', port=port)
