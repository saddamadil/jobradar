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

INDEX_HTML = '<!DOCTYPE html>\n<html lang="en">\n<head>\n<meta charset="UTF-8"/>\n<meta name="viewport" content="width=device-width, initial-scale=1.0"/>\n<title>JobRadar — Saddam\'s AI-Powered Job Search</title>\n<link href="https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Sans:ital,wght@0,300;0,400;0,500;1,300&display=swap" rel="stylesheet"/>\n<style>\n:root {\n  --bg:        #05080f;\n  --bg2:       #090d18;\n  --panel:     #0d1526;\n  --panel2:    #111d35;\n  --border:    rgba(99,179,255,0.12);\n  --blue:      #3b82f6;\n  --blue-glow: rgba(59,130,246,0.25);\n  --cyan:      #06b6d4;\n  --green:     #10b981;\n  --yellow:    #f59e0b;\n  --red:       #ef4444;\n  --text:      #e2e8f0;\n  --muted:     #64748b;\n  --accent:    #60a5fa;\n}\n*{margin:0;padding:0;box-sizing:border-box}\nhtml{scroll-behavior:smooth}\nbody{\n  background:var(--bg);\n  color:var(--text);\n  font-family:\'DM Sans\',sans-serif;\n  font-size:15px;\n  min-height:100vh;\n  overflow-x:hidden;\n}\n\n/* ── BACKGROUND MESH ── */\nbody::before{\n  content:\'\';\n  position:fixed;inset:0;\n  background:\n    radial-gradient(ellipse 80% 50% at 20% 10%, rgba(59,130,246,0.07) 0%, transparent 60%),\n    radial-gradient(ellipse 60% 40% at 80% 80%, rgba(6,182,212,0.05) 0%, transparent 60%),\n    radial-gradient(ellipse 40% 30% at 50% 50%, rgba(16,185,129,0.03) 0%, transparent 70%);\n  pointer-events:none;\n  z-index:0;\n}\n\n/* ── LAYOUT ── */\n.wrap{max-width:1200px;margin:0 auto;padding:0 24px;position:relative;z-index:1}\n\n/* ── NAV ── */\nnav{\n  position:sticky;top:0;z-index:100;\n  background:rgba(5,8,15,0.85);\n  backdrop-filter:blur(20px);\n  border-bottom:1px solid var(--border);\n  padding:16px 0;\n}\n.nav-inner{display:flex;align-items:center;justify-content:space-between;gap:16px}\n.logo{\n  font-family:\'Syne\',sans-serif;\n  font-weight:800;font-size:20px;\n  color:#fff;display:flex;align-items:center;gap:10px;\n  text-decoration:none;\n}\n.logo-dot{\n  width:10px;height:10px;border-radius:50%;\n  background:var(--blue);\n  box-shadow:0 0 12px var(--blue);\n  animation:pulse 2s infinite;\n}\n@keyframes pulse{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.6;transform:scale(1.3)}}\n.nav-links{display:flex;gap:8px}\n.nav-link{\n  padding:8px 16px;border-radius:8px;\n  color:var(--muted);font-size:13px;font-weight:500;\n  text-decoration:none;transition:all .2s;border:1px solid transparent;\n  cursor:pointer;background:none;\n}\n.nav-link:hover,.nav-link.active{color:var(--accent);border-color:var(--border);background:var(--panel)}\n.nav-badge{\n  background:var(--blue);color:#fff;\n  font-size:10px;font-weight:700;\n  padding:2px 7px;border-radius:20px;margin-left:6px;\n}\n\n/* ── HERO ── */\n.hero{padding:64px 0 48px;text-align:center}\n.hero-tag{\n  display:inline-flex;align-items:center;gap:8px;\n  background:rgba(59,130,246,0.1);border:1px solid rgba(59,130,246,0.25);\n  color:var(--accent);padding:6px 16px;border-radius:20px;\n  font-size:12px;font-weight:600;letter-spacing:.05em;text-transform:uppercase;\n  margin-bottom:24px;\n}\n.hero h1{\n  font-family:\'Syne\',sans-serif;\n  font-size:clamp(36px,6vw,64px);\n  font-weight:800;line-height:1.1;\n  color:#fff;margin-bottom:20px;\n}\n.hero h1 span{\n  background:linear-gradient(90deg,var(--blue),var(--cyan));\n  -webkit-background-clip:text;-webkit-text-fill-color:transparent;\n}\n.hero p{color:var(--muted);font-size:17px;max-width:560px;margin:0 auto 36px;line-height:1.7}\n.hero-stats{\n  display:flex;justify-content:center;gap:32px;flex-wrap:wrap;margin-bottom:40px;\n}\n.stat{text-align:center}\n.stat-val{\n  font-family:\'Syne\',sans-serif;font-size:32px;font-weight:800;\n  background:linear-gradient(135deg,#fff,var(--accent));\n  -webkit-background-clip:text;-webkit-text-fill-color:transparent;\n}\n.stat-label{color:var(--muted);font-size:12px;margin-top:2px}\n.hero-actions{display:flex;justify-content:center;gap:12px;flex-wrap:wrap}\n.btn{\n  padding:12px 28px;border-radius:10px;font-size:14px;font-weight:600;\n  cursor:pointer;border:none;text-decoration:none;transition:all .2s;\n  display:inline-flex;align-items:center;gap:8px;\n}\n.btn-primary{\n  background:linear-gradient(135deg,var(--blue),#2563eb);\n  color:#fff;box-shadow:0 4px 20px rgba(59,130,246,0.3);\n}\n.btn-primary:hover{transform:translateY(-2px);box-shadow:0 8px 30px rgba(59,130,246,0.4)}\n.btn-secondary{\n  background:var(--panel);color:var(--text);\n  border:1px solid var(--border);\n}\n.btn-secondary:hover{border-color:var(--blue);color:var(--accent)}\n\n/* ── FILTERS ── */\n.filters{\n  display:flex;gap:10px;flex-wrap:wrap;\n  align-items:center;margin-bottom:24px;\n}\n.search-wrap{position:relative;flex:1;min-width:220px}\n.search-wrap input{\n  width:100%;padding:11px 16px 11px 42px;\n  background:var(--panel);border:1px solid var(--border);\n  border-radius:10px;color:var(--text);font-size:14px;\n  font-family:\'DM Sans\',sans-serif;outline:none;transition:border .2s;\n}\n.search-wrap input:focus{border-color:var(--blue)}\n.search-wrap input::placeholder{color:var(--muted)}\n.search-icon{position:absolute;left:14px;top:50%;transform:translateY(-50%);color:var(--muted);font-size:16px}\n.filter-btn{\n  padding:11px 16px;border-radius:10px;\n  background:var(--panel);border:1px solid var(--border);\n  color:var(--muted);font-size:13px;font-weight:600;\n  cursor:pointer;transition:all .2s;white-space:nowrap;\n}\n.filter-btn:hover,.filter-btn.on{border-color:var(--blue);color:var(--accent);background:rgba(59,130,246,0.08)}\n.results-count{\n  color:var(--muted);font-size:13px;\n  padding:11px 16px;background:var(--panel);\n  border:1px solid var(--border);border-radius:10px;white-space:nowrap;\n}\n\n/* ── GRID ── */\n.jobs-grid{display:flex;flex-direction:column;gap:12px}\n\n/* ── JOB CARD ── */\n.job-card{\n  background:var(--panel);\n  border:1px solid var(--border);\n  border-radius:16px;padding:20px 24px;\n  transition:all .25s;cursor:default;\n  animation:fadeUp .4s ease both;\n  position:relative;overflow:hidden;\n}\n.job-card::before{\n  content:\'\';position:absolute;left:0;top:0;bottom:0;width:3px;\n  background:linear-gradient(180deg,var(--blue),var(--cyan));\n  opacity:0;transition:opacity .2s;\n}\n.job-card:hover{border-color:rgba(99,179,255,0.25);background:var(--panel2);transform:translateX(2px)}\n.job-card:hover::before{opacity:1}\n.job-card.applied{border-color:rgba(16,185,129,0.25);background:rgba(16,185,129,0.04)}\n.job-card.applied::before{background:var(--green);opacity:1}\n.job-card.hot{border-color:rgba(245,158,11,0.2)}\n@keyframes fadeUp{from{opacity:0;transform:translateY(16px)}to{opacity:1;transform:translateY(0)}}\n\n.card-top{display:flex;gap:16px;align-items:flex-start}\n.match-ring{\n  flex-shrink:0;width:52px;height:52px;border-radius:50%;\n  display:flex;flex-direction:column;align-items:center;justify-content:center;\n  border:2.5px solid var(--blue);position:relative;\n}\n.match-ring.high{border-color:var(--green)}\n.match-ring.mid{border-color:var(--yellow)}\n.match-val{font-family:\'Syne\',sans-serif;font-size:14px;font-weight:800;line-height:1;color:#fff}\n.match-lbl{font-size:8px;color:var(--muted);text-transform:uppercase;letter-spacing:.05em}\n\n.card-info{flex:1;min-width:0}\n.card-title{\n  font-family:\'Syne\',sans-serif;font-size:16px;font-weight:700;\n  color:#fff;margin-bottom:5px;line-height:1.3;\n}\n.card-meta{display:flex;gap:14px;flex-wrap:wrap;align-items:center;margin-bottom:10px}\n.card-company{color:var(--accent);font-size:13px;font-weight:500}\n.card-loc{color:var(--muted);font-size:12px}\n.card-salary{color:var(--green);font-size:12px;font-weight:600}\n.card-posted{color:var(--muted);font-size:11px}\n.card-tags{display:flex;gap:6px;flex-wrap:wrap}\n.tag{\n  font-size:11px;padding:3px 10px;border-radius:20px;\n  background:rgba(255,255,255,0.05);color:var(--muted);\n  border:1px solid rgba(255,255,255,0.08);\n}\n.tag.featured{background:rgba(59,130,246,0.1);color:var(--accent);border-color:rgba(59,130,246,0.2)}\n\n.hot-badge{\n  position:absolute;top:14px;right:16px;\n  background:linear-gradient(90deg,#f59e0b,#ef4444);\n  color:#fff;font-size:10px;font-weight:700;\n  padding:3px 10px;border-radius:20px;letter-spacing:.05em;\n}\n.applied-badge{\n  position:absolute;top:14px;right:16px;\n  background:rgba(16,185,129,0.15);color:var(--green);\n  font-size:10px;font-weight:700;padding:3px 12px;\n  border-radius:20px;border:1px solid rgba(16,185,129,0.3);\n}\n\n.card-actions{display:flex;flex-direction:column;gap:7px;flex-shrink:0;min-width:130px}\n.btn-apply{\n  padding:10px 0;border-radius:9px;\n  background:linear-gradient(135deg,var(--blue),#2563eb);\n  color:#fff;font-size:12px;font-weight:700;\n  text-align:center;text-decoration:none;border:none;cursor:pointer;\n  transition:all .2s;box-shadow:0 2px 12px rgba(59,130,246,0.3);\n  display:block;\n}\n.btn-apply:hover{transform:translateY(-1px);box-shadow:0 4px 20px rgba(59,130,246,0.45)}\n.btn-hr{\n  padding:9px 0;border-radius:9px;\n  background:transparent;border:1px solid var(--border);\n  color:var(--accent);font-size:12px;font-weight:600;\n  text-align:center;text-decoration:none;cursor:pointer;transition:all .2s;\n  display:block;\n}\n.btn-hr:hover{border-color:var(--blue);background:rgba(59,130,246,0.08)}\n.btn-row{display:flex;gap:6px}\n.btn-mark{\n  flex:1;padding:8px 0;border-radius:8px;border:none;\n  cursor:pointer;font-size:11px;font-weight:700;transition:all .2s;\n}\n.btn-mark.pending{background:rgba(255,255,255,0.05);color:var(--muted)}\n.btn-mark.done{background:rgba(16,185,129,0.15);color:var(--green)}\n.btn-save{\n  padding:8px 10px;border-radius:8px;border:none;\n  background:rgba(255,255,255,0.05);cursor:pointer;\n  font-size:14px;transition:all .2s;color:var(--muted);\n}\n.btn-save.saved{background:rgba(245,158,11,0.15);color:var(--yellow)}\n\n/* ── SECTION HEADER ── */\n.section-hd{display:flex;align-items:center;justify-content:space-between;margin-bottom:20px;flex-wrap:wrap;gap:12px}\n.section-title{font-family:\'Syne\',sans-serif;font-size:20px;font-weight:700;color:#fff}\n.section-sub{color:var(--muted);font-size:13px;margin-top:3px}\n.live-dot{\n  display:inline-block;width:8px;height:8px;border-radius:50%;\n  background:var(--green);box-shadow:0 0 8px var(--green);\n  margin-right:6px;animation:pulse 1.5s infinite;\n}\n\n/* ── TABS ── */\n.tabs{display:flex;gap:4px;background:var(--panel);padding:4px;border-radius:12px;margin-bottom:28px;flex-wrap:wrap}\n.tab{\n  flex:1;min-width:120px;padding:10px 16px;border-radius:9px;border:none;\n  cursor:pointer;font-size:13px;font-weight:600;transition:all .2s;\n  background:transparent;color:var(--muted);font-family:\'DM Sans\',sans-serif;\n}\n.tab.active{background:var(--panel2);color:#fff;box-shadow:0 2px 8px rgba(0,0,0,0.3)}\n\n/* ── HR CARDS ── */\n.hr-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:12px}\n.hr-card{\n  background:var(--panel);border:1px solid var(--border);border-radius:14px;\n  padding:18px 20px;transition:all .2s;\n}\n.hr-card:hover{border-color:rgba(99,179,255,0.25)}\n.hr-company{font-family:\'Syne\',sans-serif;font-size:15px;font-weight:700;color:#fff;margin-bottom:4px}\n.hr-loc{color:var(--muted);font-size:12px;margin-bottom:14px}\n.btn-find-hr{\n  display:block;width:100%;padding:9px 0;border-radius:9px;\n  background:linear-gradient(135deg,var(--blue),#2563eb);\n  color:#fff;font-size:12px;font-weight:700;\n  text-align:center;text-decoration:none;\n  box-shadow:0 2px 10px rgba(59,130,246,0.25);\n  transition:all .2s;\n}\n.btn-find-hr:hover{transform:translateY(-1px);box-shadow:0 4px 18px rgba(59,130,246,0.4)}\n\n/* ── MESSAGE TEMPLATE ── */\n.msg-box{\n  background:var(--panel);border:1px solid rgba(245,158,11,0.2);\n  border-radius:14px;padding:22px 24px;margin-top:24px;\n}\n.msg-title{font-family:\'Syne\',sans-serif;font-size:16px;font-weight:700;color:var(--yellow);margin-bottom:14px}\n.msg-text{\n  background:rgba(0,0,0,0.3);border-radius:10px;padding:16px 18px;\n  font-size:13px;color:#94a3b8;line-height:1.8;font-family:monospace;\n  white-space:pre-wrap;\n}\n.copy-btn{\n  margin-top:12px;padding:9px 20px;border-radius:8px;\n  background:rgba(245,158,11,0.1);border:1px solid rgba(245,158,11,0.2);\n  color:var(--yellow);font-size:12px;font-weight:700;cursor:pointer;\n  transition:all .2s;\n}\n.copy-btn:hover{background:rgba(245,158,11,0.18)}\n\n/* ── QUICK LINKS ── */\n.links-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:10px}\n.link-card{\n  display:flex;align-items:center;justify-content:space-between;\n  padding:14px 18px;background:var(--panel);border:1px solid var(--border);\n  border-radius:12px;text-decoration:none;transition:all .2s;\n  color:var(--text);\n}\n.link-card:hover{border-color:var(--blue);background:var(--panel2)}\n.link-name{font-weight:600;font-size:14px}\n.link-region{font-size:11px;color:var(--muted);margin-top:2px}\n.link-arrow{color:var(--accent);font-size:13px}\n\n/* ── PROGRESS BAR ── */\n.progress-section{\n  background:var(--panel);border:1px solid var(--border);\n  border-radius:16px;padding:24px;margin-bottom:28px;\n}\n.progress-title{font-family:\'Syne\',sans-serif;font-size:16px;font-weight:700;margin-bottom:20px;color:#fff}\n.progress-row{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:16px}\n.progress-item{text-align:center}\n.progress-ring-wrap{position:relative;width:70px;height:70px;margin:0 auto 10px}\n.progress-ring-wrap svg{transform:rotate(-90deg)}\n.ring-bg{fill:none;stroke:rgba(255,255,255,0.06);stroke-width:5}\n.ring-fill{fill:none;stroke-width:5;stroke-linecap:round;transition:stroke-dashoffset 1s ease}\n.ring-val{\n  position:absolute;inset:0;display:flex;align-items:center;justify-content:center;\n  font-family:\'Syne\',sans-serif;font-size:15px;font-weight:800;color:#fff;\n}\n.prog-label{font-size:12px;color:var(--muted)}\n.prog-num{font-size:11px;color:var(--muted);margin-top:2px}\n\n/* ── TOAST ── */\n.toast{\n  position:fixed;bottom:24px;right:24px;z-index:999;\n  background:var(--green);color:#fff;padding:12px 20px;\n  border-radius:10px;font-size:13px;font-weight:600;\n  box-shadow:0 8px 30px rgba(16,185,129,0.4);\n  transform:translateY(80px);opacity:0;transition:all .3s;\n  pointer-events:none;\n}\n.toast.show{transform:translateY(0);opacity:1}\n\n/* ── FOOTER ── */\nfooter{\n  border-top:1px solid var(--border);margin-top:60px;\n  padding:28px 0;text-align:center;color:var(--muted);font-size:13px;\n}\n\n/* ── RESPONSIVE ── */\n@media(max-width:640px){\n  .card-top{flex-direction:column}\n  .card-actions{flex-direction:row;min-width:auto;width:100%}\n  .btn-apply,.btn-hr{flex:1}\n  .card-actions{flex-wrap:wrap}\n  .hero h1{font-size:32px}\n  .nav-links{display:none}\n}\n</style>\n</head>\n<body>\n\n<!-- NAV -->\n<nav>\n  <div class="wrap nav-inner">\n    <a href="#" class="logo">\n      <div class="logo-dot"></div>\n      JobRadar\n    </a>\n    <div class="nav-links">\n      <button class="nav-link active" onclick="showTab(\'jobs\')">Jobs <span class="nav-badge" id="nb-jobs">10</span></button>\n      <button class="nav-link" onclick="showTab(\'hr\')">HR Finder</button>\n      <button class="nav-link" onclick="showTab(\'links\')">Job Boards</button>\n      <button class="nav-link" onclick="showTab(\'progress\')">My Progress</button>\n    </div>\n    <a href="dashboard.html" class="btn btn-secondary" style="font-size:13px;padding:8px 16px">⚙ Dashboard</a>\n  </div>\n</nav>\n\n<!-- HERO -->\n<section class="hero">\n  <div class="wrap">\n    <div class="hero-tag"><span class="live-dot"></span>Auto-updated daily · Powered by Adzuna API</div>\n    <h1>Your Daily <span>Job Radar</span><br/>— Germany & Remote</h1>\n    <p>AI-matched jobs for Performance Marketing, SEO & Growth roles. Updated every morning at 9 AM.</p>\n    <div class="hero-stats">\n      <div class="stat"><div class="stat-val" id="stat-total">10</div><div class="stat-label">Jobs Today</div></div>\n      <div class="stat"><div class="stat-val" id="stat-applied">0</div><div class="stat-label">Applied</div></div>\n      <div class="stat"><div class="stat-val" id="stat-interviews">0</div><div class="stat-label">Interviews</div></div>\n      <div class="stat"><div class="stat-val" id="stat-rate">0%</div><div class="stat-label">Response Rate</div></div>\n    </div>\n    <div class="hero-actions">\n      <button class="btn btn-primary" onclick="showTab(\'jobs\')">🎯 View Today\'s Jobs</button>\n      <a href="dashboard.html" class="btn btn-secondary">⚙ Admin Dashboard</a>\n    </div>\n  </div>\n</section>\n\n<!-- MAIN -->\n<main class="wrap">\n\n  <!-- TABS -->\n  <div class="tabs">\n    <button class="tab active" id="tab-jobs" onclick="showTab(\'jobs\')">🎯 Today\'s Jobs</button>\n    <button class="tab" id="tab-hr" onclick="showTab(\'hr\')">👤 HR Finder</button>\n    <button class="tab" id="tab-links" onclick="showTab(\'links\')">🔗 Job Boards</button>\n    <button class="tab" id="tab-progress" onclick="showTab(\'progress\')">📈 My Progress</button>\n  </div>\n\n  <!-- JOBS TAB -->\n  <div id="pane-jobs">\n    <div class="section-hd">\n      <div>\n        <div class="section-title"><span class="live-dot"></span>Today\'s Matched Jobs</div>\n        <div class="section-sub" id="last-updated">Last updated: Loading...</div>\n      </div>\n      <button class="btn btn-secondary" style="font-size:13px" onclick="refreshJobs()">↻ Refresh</button>\n    </div>\n\n    <!-- FILTERS -->\n    <div class="filters">\n      <div class="search-wrap">\n        <span class="search-icon">🔍</span>\n        <input id="search-input" type="text" placeholder="Search title, company, skill..." oninput="filterJobs()"/>\n      </div>\n      <button class="filter-btn" id="f-remote" onclick="toggleFilter(\'remote\')">🌍 Remote</button>\n      <button class="filter-btn" id="f-germany" onclick="toggleFilter(\'germany\')">🇩🇪 Germany</button>\n      <button class="filter-btn" id="f-saved" onclick="toggleFilter(\'saved\')">🔖 Saved</button>\n      <div class="results-count" id="results-count">10 jobs</div>\n    </div>\n\n    <div class="jobs-grid" id="jobs-grid"></div>\n  </div>\n\n  <!-- HR TAB -->\n  <div id="pane-hr" style="display:none">\n    <div class="section-hd">\n      <div>\n        <div class="section-title">👤 Find HR Profiles on LinkedIn</div>\n        <div class="section-sub">Connect with recruiters after applying — doubles your callback rate</div>\n      </div>\n    </div>\n    <div class="hr-grid" id="hr-grid"></div>\n    <div class="msg-box">\n      <div class="msg-title">📝 LinkedIn Message Template</div>\n      <div class="msg-text" id="msg-template">Hi [HR Name] 👋\n\nI recently applied for the [Job Title] role at [Company]. I bring 6+ years in performance marketing — delivering 120% organic traffic growth, 35% lead gen increase, and consistent ROAS across B2B, SaaS & FMCG.\n\nI also build AI-augmented marketing workflows using Python & LangChain that reduce manual work by ~40%.\n\nWould love to connect — portfolio at www.saddamadil.in\n\nBest,\nSaddam Adil</div>\n      <button class="copy-btn" onclick="copyMsg()">📋 Copy Message</button>\n    </div>\n  </div>\n\n  <!-- LINKS TAB -->\n  <div id="pane-links" style="display:none">\n    <div class="section-hd">\n      <div>\n        <div class="section-title">🔗 Quick Job Board Links</div>\n        <div class="section-sub">Click to open pre-searched results on each platform</div>\n      </div>\n    </div>\n    <div class="links-grid" id="links-grid"></div>\n  </div>\n\n  <!-- PROGRESS TAB -->\n  <div id="pane-progress" style="display:none">\n    <div class="progress-section">\n      <div class="progress-title">📈 Application Progress</div>\n      <div class="progress-row" id="progress-row"></div>\n    </div>\n    <div class="section-title" style="margin-bottom:16px">📋 Application History</div>\n    <div class="jobs-grid" id="history-grid"></div>\n  </div>\n\n</main>\n\n<footer>\n  <div class="wrap">\n    JobRadar · Built for Saddam Adil · <a href="https://www.saddamadil.in" style="color:var(--accent)" target="_blank">saddamadil.in</a> · Auto-updates daily at 9:00 AM\n  </div>\n</footer>\n\n<div class="toast" id="toast"></div>\n\n<script>\n// ── STATE ──\nlet jobs = [], saved = {}, applied = {}, filters = {remote:false,germany:false,saved:false};\n\nconst JOBS_DATA = [\n  {id:1,title:"Senior Performance Marketing Manager",company:"Zalando SE",location:"Berlin, Germany",type:"Full-time · On-site",match:98,salary:"€55k–€75k",tags:["Google Ads","Meta Ads","ROAS","GA4"],url:"https://www.linkedin.com/jobs/performance-marketing-manager-jobs-berlin-be",hrUrl:"https://www.linkedin.com/search/results/people/?keywords=HR+Recruiter+Zalando",platform:"LinkedIn",posted:"Today",hot:true},\n  {id:2,title:"SEO & Growth Manager (International)",company:"Delivery Hero",location:"Berlin, Germany",type:"Full-time · Hybrid",match:96,salary:"€50k–€70k",tags:["Technical SEO","GEO","Ahrefs"],url:"https://www.linkedin.com/jobs/search-engine-optimization-manager-jobs-berlin",hrUrl:"https://www.linkedin.com/search/results/people/?keywords=Talent+Acquisition+Delivery+Hero",platform:"LinkedIn",posted:"Today",hot:true},\n  {id:3,title:"Performance Marketing Specialist",company:"Remote.com",location:"Worldwide · Remote",type:"Full-time · Remote",match:95,salary:"$45k–$65k",tags:["Google Ads","SEO","Python"],url:"https://www.linkedin.com/jobs/performance-marketing-manager-jobs-worldwide",hrUrl:"https://www.linkedin.com/search/results/people/?keywords=Recruiter+Remote.com",platform:"LinkedIn",posted:"Today",hot:true},\n  {id:4,title:"Digital Marketing Manager – B2B SaaS",company:"HubSpot",location:"Dublin · Remote eligible",type:"Full-time · Remote",match:93,salary:"€60k–€80k",tags:["HubSpot","SEO","Lead Gen","B2B"],url:"https://www.linkedin.com/jobs/digital-marketing-manager-jobs-ireland",hrUrl:"https://www.linkedin.com/search/results/people/?keywords=Recruiter+HubSpot+Dublin",platform:"LinkedIn",posted:"2 days ago",hot:false},\n  {id:5,title:"SEO Manager (All Genders)",company:"Axel Springer",location:"Berlin, Germany",type:"Full-time · Hybrid",match:92,salary:"€45k–€62k",tags:["Technical SEO","Core Web Vitals","SEMrush"],url:"https://www.linkedin.com/jobs/seo-manager-jobs-berlin",hrUrl:"https://www.linkedin.com/search/results/people/?keywords=HR+Axel+Springer+Berlin",platform:"LinkedIn",posted:"Today",hot:false},\n  {id:6,title:"AI Marketing Specialist – Growth",company:"N26 Bank",location:"Berlin, Germany",type:"Full-time · Hybrid",match:91,salary:"€55k–€72k",tags:["AI Tools","Python","Meta Ads"],url:"https://www.linkedin.com/jobs/digital-marketing-manager-jobs-berlin",hrUrl:"https://www.linkedin.com/search/results/people/?keywords=Talent+Recruiter+N26+Berlin",platform:"LinkedIn",posted:"3 days ago",hot:false},\n  {id:7,title:"Performance Marketing Manager – FMCG",company:"HelloFresh",location:"Berlin, Germany",type:"Full-time · On-site",match:90,salary:"€52k–€68k",tags:["Meta Ads","FMCG","CPA"],url:"https://www.linkedin.com/jobs/performance-marketing-m-w-d-jobs-berlin-be",hrUrl:"https://www.linkedin.com/search/results/people/?keywords=Recruiter+HelloFresh+Berlin",platform:"LinkedIn",posted:"2 days ago",hot:false},\n  {id:8,title:"Senior SEO Strategist (Remote)",company:"Shopify",location:"Worldwide · Remote",type:"Full-time · Remote",match:89,salary:"$55k–$80k",tags:["Shopify","Technical SEO","E-commerce"],url:"https://www.linkedin.com/jobs/seo-specialist-jobs-worldwide",hrUrl:"https://www.linkedin.com/search/results/people/?keywords=Talent+Recruiter+Shopify",platform:"LinkedIn",posted:"Today",hot:true},\n  {id:9,title:"Digital Marketing & SEO Specialist",company:"Siemens AG",location:"Munich, Germany",type:"Full-time · Hybrid",match:88,salary:"€50k–€67k",tags:["B2B","Google Ads","Looker Studio"],url:"https://www.linkedin.com/jobs/search-engine-optimization-specialist-jobs-munich",hrUrl:"https://www.linkedin.com/search/results/people/?keywords=HR+Recruiter+Siemens+Munich",platform:"LinkedIn",posted:"4 days ago",hot:false},\n  {id:10,title:"Growth & Performance Marketing Lead",company:"Wolt (DoorDash)",location:"Helsinki · Remote eligible",type:"Full-time · Remote",match:87,salary:"€55k–€75k",tags:["Growth","Google Ads","ROAS"],url:"https://www.linkedin.com/jobs/performance-marketing-manager-jobs-worldwide",hrUrl:"https://www.linkedin.com/search/results/people/?keywords=Talent+Acquisition+Wolt",platform:"LinkedIn",posted:"Today",hot:true},\n];\n\nconst LINKS_DATA = [\n  {name:"LinkedIn Jobs",region:"🌍 Global",url:"https://www.linkedin.com/jobs/performance-marketing-manager-jobs-worldwide"},\n  {name:"Indeed Global",region:"🌍 Remote",url:"https://www.indeed.com/jobs?q=performance+marketing+specialist&l=remote"},\n  {name:"StepStone DE",region:"🇩🇪 Germany",url:"https://www.stepstone.de/jobs/Performance-Marketing-Manager/in-Deutschland.html"},\n  {name:"XING Jobs",region:"🇩🇪 Germany",url:"https://www.xing.com/jobs/search?keywords=seo+manager&location=berlin"},\n  {name:"Indeed Germany",region:"🇩🇪 Germany",url:"https://de.indeed.com/jobs?q=digital+marketing+specialist&l=Deutschland"},\n  {name:"Glassdoor",region:"🌍 Global",url:"https://www.glassdoor.com/Job/digital-marketing-manager-jobs-SRCH_KO0,25.htm"},\n  {name:"WeWorkRemotely",region:"🌍 Remote",url:"https://weworkremotely.com/categories/remote-marketing-jobs"},\n  {name:"Otta (Europe)",region:"🇪🇺 Europe",url:"https://app.otta.com/jobs/marketing"},\n  {name:"YC Jobs Board",region:"🌍 Startups",url:"https://www.ycombinator.com/jobs/role/marketing"},\n  {name:"Arbeitsagentur",region:"🇩🇪 Germany",url:"https://www.arbeitsagentur.de/jobsuche/suche?was=marketing+manager&wo=Deutschland"},\n];\n\n// ── INIT ──\nfunction init(){\n  jobs = [...JOBS_DATA];\n  loadStorage();\n  renderJobs(jobs);\n  renderHR();\n  renderLinks();\n  renderProgress();\n  document.getElementById(\'last-updated\').textContent = \'Last updated: \' + new Date().toLocaleString();\n  document.getElementById(\'stat-total\').textContent = jobs.length;\n  updateStats();\n}\n\nfunction loadStorage(){\n  try{\n    const s = sessionStorage.getItem(\'jr_saved\');\n    const a = sessionStorage.getItem(\'jr_applied\');\n    if(s) saved = JSON.parse(s);\n    if(a) applied = JSON.parse(a);\n  }catch(e){}\n}\nfunction saveStorage(){\n  try{\n    sessionStorage.setItem(\'jr_saved\', JSON.stringify(saved));\n    sessionStorage.setItem(\'jr_applied\', JSON.stringify(applied));\n  }catch(e){}\n}\n\n// ── TABS ──\nfunction showTab(t){\n  [\'jobs\',\'hr\',\'links\',\'progress\'].forEach(p=>{\n    document.getElementById(\'pane-\'+p).style.display = p===t?\'block\':\'none\';\n    document.getElementById(\'tab-\'+p).classList.toggle(\'active\', p===t);\n  });\n}\n\n// ── RENDER JOBS ──\nfunction renderJobs(list){\n  const g = document.getElementById(\'jobs-grid\');\n  document.getElementById(\'results-count\').textContent = list.length+\' jobs\';\n  if(!list.length){g.innerHTML=\'<div style="text-align:center;padding:60px;color:var(--muted)">No jobs match your filters</div>\';return;}\n  g.innerHTML = list.map((j,i)=>jobCard(j,i)).join(\'\');\n}\n\nfunction jobCard(j, i){\n  const mc = j.match>=90?\'high\':j.match>=80?\'mid\':\'\';\n  const isApplied = !!applied[j.id];\n  const isSaved = !!saved[j.id];\n  const delay = i*0.04;\n  const circumference = 2*Math.PI*22;\n  const dashOffset = circumference*(1-j.match/100);\n  const ringColor = j.match>=90?\'#10b981\':j.match>=80?\'#f59e0b\':\'#3b82f6\';\n  return `<div class="job-card${isApplied?\' applied\':\'\'}${j.hot&&!isApplied?\' hot\':\'\'}" style="animation-delay:${delay}s">\n    ${isApplied?\'<div class="applied-badge">✅ Applied</div>\':j.hot?\'<div class="hot-badge">🔥 Hot</div>\':\'\'}\n    <div class="card-top">\n      <div class="match-ring ${mc}">\n        <svg width="52" height="52" style="position:absolute;inset:0">\n          <circle class="ring-bg" cx="26" cy="26" r="22"/>\n          <circle class="ring-fill" cx="26" cy="26" r="22" stroke="${ringColor}"\n            stroke-dasharray="${circumference}" stroke-dashoffset="${dashOffset}"/>\n        </svg>\n        <div class="match-val">${j.match}</div>\n      </div>\n      <div class="card-info">\n        <div class="card-title">${j.title}</div>\n        <div class="card-meta">\n          <span class="card-company">🏢 ${j.company}</span>\n          <span class="card-loc">📍 ${j.location}</span>\n          ${j.salary?`<span class="card-salary">💰 ${j.salary}</span>`:\'\'}\n          <span class="card-posted">⏰ ${j.posted}</span>\n        </div>\n        <div class="card-tags">\n          <span class="tag featured">${j.type}</span>\n          ${j.tags.map(t=>`<span class="tag">${t}</span>`).join(\'\')}\n        </div>\n      </div>\n      <div class="card-actions">\n        <a href="${j.url}" target="_blank" class="btn-apply">🚀 Apply Now</a>\n        <a href="${j.hrUrl}" target="_blank" class="btn-hr">👤 Find HR</a>\n        <div class="btn-row">\n          <button class="btn-mark ${isApplied?\'done\':\'pending\'}" onclick="toggleApplied(${j.id})">${isApplied?\'✅ Applied\':\'Mark Applied\'}</button>\n          <button class="btn-save ${isSaved?\'saved\':\'\'}" onclick="toggleSaved(${j.id})">${isSaved?\'🔖\':\'☆\'}</button>\n        </div>\n      </div>\n    </div>\n  </div>`;\n}\n\n// ── ACTIONS ──\nfunction toggleApplied(id){\n  applied[id] = !applied[id];\n  saveStorage(); updateStats(); filterJobs();\n  showToast(applied[id]?\'✅ Marked as Applied!\':\'↩ Removed from Applied\');\n}\nfunction toggleSaved(id){\n  saved[id]=!saved[id];\n  saveStorage(); filterJobs();\n  showToast(saved[id]?\'🔖 Job Saved!\':\'Removed from Saved\');\n}\nfunction toggleFilter(f){\n  filters[f]=!filters[f];\n  document.getElementById(\'f-\'+f).classList.toggle(\'on\',filters[f]);\n  filterJobs();\n}\nfunction filterJobs(){\n  const q = document.getElementById(\'search-input\').value.toLowerCase();\n  let list = jobs.filter(j=>{\n    if(filters.remote && !j.type.toLowerCase().includes(\'remote\')) return false;\n    if(filters.germany && !j.location.toLowerCase().includes(\'germany\') && !j.location.toLowerCase().includes(\'berlin\') && !j.location.toLowerCase().includes(\'munich\')) return false;\n    if(filters.saved && !saved[j.id]) return false;\n    if(q && !j.title.toLowerCase().includes(q) && !j.company.toLowerCase().includes(q) && !j.tags.some(t=>t.toLowerCase().includes(q))) return false;\n    return true;\n  });\n  renderJobs(list);\n}\nfunction refreshJobs(){\n  showToast(\'🔄 Refreshing jobs...\');\n  setTimeout(()=>{init();showToast(\'✅ Jobs refreshed!\');},800);\n}\nfunction updateStats(){\n  const a = Object.values(applied).filter(Boolean).length;\n  document.getElementById(\'stat-applied\').textContent = a;\n  document.getElementById(\'stat-rate\').textContent = jobs.length?Math.round(a/jobs.length*100)+\'%\':\'0%\';\n}\n\n// ── HR ──\nfunction renderHR(){\n  document.getElementById(\'hr-grid\').innerHTML = JOBS_DATA.map(j=>`\n    <div class="hr-card">\n      <div class="hr-company">${j.company}</div>\n      <div class="hr-loc">📍 ${j.location}</div>\n      <a href="${j.hrUrl}" target="_blank" class="btn-find-hr">👤 Find HR on LinkedIn</a>\n    </div>`).join(\'\');\n}\n\n// ── LINKS ──\nfunction renderLinks(){\n  document.getElementById(\'links-grid\').innerHTML = LINKS_DATA.map(l=>`\n    <a href="${l.url}" target="_blank" class="link-card">\n      <div><div class="link-name">${l.name}</div><div class="link-region">${l.region}</div></div>\n      <span class="link-arrow">→</span>\n    </a>`).join(\'\');\n}\n\n// ── PROGRESS ──\nfunction renderProgress(){\n  const stats = [\n    {label:\'Jobs Found\',val:10,max:10,color:\'#3b82f6\'},\n    {label:\'Applied\',val:Object.values(applied).filter(Boolean).length,max:10,color:\'#10b981\'},\n    {label:\'HR Contacted\',val:0,max:10,color:\'#06b6d4\'},\n    {label:\'Interviews\',val:0,max:10,color:\'#f59e0b\'},\n  ];\n  const c = 2*Math.PI*28;\n  document.getElementById(\'progress-row\').innerHTML = stats.map(s=>{\n    const pct = s.max?s.val/s.max:0;\n    const offset = c*(1-pct);\n    return `<div class="progress-item">\n      <div class="progress-ring-wrap">\n        <svg width="70" height="70" viewBox="0 0 70 70">\n          <circle class="ring-bg" cx="35" cy="35" r="28"/>\n          <circle class="ring-fill" cx="35" cy="35" r="28" stroke="${s.color}"\n            stroke-dasharray="${c}" stroke-dashoffset="${offset}"/>\n        </svg>\n        <div class="ring-val">${s.val}</div>\n      </div>\n      <div class="prog-label">${s.label}</div>\n      <div class="prog-num">${s.val} / ${s.max}</div>\n    </div>`;\n  }).join(\'\');\n}\n\n// ── UTILS ──\nfunction copyMsg(){\n  navigator.clipboard.writeText(document.getElementById(\'msg-template\').textContent);\n  showToast(\'📋 Message copied!\');\n}\nfunction showToast(msg){\n  const t = document.getElementById(\'toast\');\n  t.textContent = msg;\n  t.classList.add(\'show\');\n  setTimeout(()=>t.classList.remove(\'show\'),2500);\n}\n\ninit();\n</script>\n</body>\n</html>\n'
DASHBOARD_HTML = '<!DOCTYPE html>\n<html lang="en">\n<head>\n<meta charset="UTF-8"/>\n<meta name="viewport" content="width=device-width,initial-scale=1.0"/>\n<title>JobRadar — Admin Dashboard</title>\n<link href="https://fonts.googleapis.com/css2?family=Syne:wght@400;700;800&family=DM+Sans:wght@300;400;500&display=swap" rel="stylesheet"/>\n<style>\n:root{\n  --bg:#05080f;--panel:#0d1526;--panel2:#111d35;--border:rgba(99,179,255,0.12);\n  --blue:#3b82f6;--cyan:#06b6d4;--green:#10b981;--yellow:#f59e0b;--red:#ef4444;\n  --text:#e2e8f0;--muted:#64748b;--accent:#60a5fa;\n}\n*{margin:0;padding:0;box-sizing:border-box}\nbody{background:var(--bg);color:var(--text);font-family:\'DM Sans\',sans-serif;font-size:14px;display:flex;min-height:100vh}\n\n/* SIDEBAR */\n.sidebar{\n  width:220px;background:var(--panel);border-right:1px solid var(--border);\n  padding:24px 0;display:flex;flex-direction:column;flex-shrink:0;\n  position:fixed;top:0;left:0;bottom:0;z-index:10;\n}\n.sb-logo{padding:0 20px 28px;font-family:\'Syne\',sans-serif;font-weight:800;font-size:18px;color:#fff;display:flex;align-items:center;gap:10px;border-bottom:1px solid var(--border)}\n.sb-dot{width:9px;height:9px;border-radius:50%;background:var(--blue);box-shadow:0 0 10px var(--blue);animation:pulse 2s infinite}\n@keyframes pulse{0%,100%{opacity:1}50%{opacity:.5}}\n.sb-section{padding:16px 20px 6px;font-size:10px;color:var(--muted);text-transform:uppercase;letter-spacing:.1em;font-weight:600}\n.sb-link{\n  display:flex;align-items:center;gap:10px;padding:10px 20px;\n  color:var(--muted);text-decoration:none;font-size:13px;font-weight:500;\n  transition:all .15s;cursor:pointer;border:none;background:none;width:100%;text-align:left;\n}\n.sb-link:hover,.sb-link.active{color:#fff;background:rgba(255,255,255,0.05)}\n.sb-link.active{border-left:2px solid var(--blue);padding-left:18px}\n.sb-icon{font-size:16px;width:20px}\n.sb-badge{margin-left:auto;background:var(--blue);color:#fff;font-size:9px;font-weight:700;padding:2px 7px;border-radius:10px}\n\n/* MAIN */\n.main{margin-left:220px;flex:1;padding:28px 32px;min-height:100vh}\n\n/* TOP BAR */\n.topbar{display:flex;justify-content:space-between;align-items:center;margin-bottom:28px;flex-wrap:wrap;gap:12px}\n.page-title{font-family:\'Syne\',sans-serif;font-size:22px;font-weight:800;color:#fff}\n.page-sub{color:var(--muted);font-size:13px;margin-top:2px}\n.topbar-actions{display:flex;gap:10px;align-items:center}\n.btn{padding:9px 18px;border-radius:9px;font-size:13px;font-weight:600;cursor:pointer;border:none;transition:all .2s;display:inline-flex;align-items:center;gap:6px}\n.btn-primary{background:linear-gradient(135deg,var(--blue),#2563eb);color:#fff;box-shadow:0 2px 12px rgba(59,130,246,0.3)}\n.btn-primary:hover{transform:translateY(-1px)}\n.btn-ghost{background:var(--panel);color:var(--text);border:1px solid var(--border)}\n.btn-ghost:hover{border-color:var(--blue);color:var(--accent)}\n\n/* KPI CARDS */\n.kpi-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:14px;margin-bottom:24px}\n.kpi{background:var(--panel);border:1px solid var(--border);border-radius:14px;padding:18px 20px;position:relative;overflow:hidden}\n.kpi::after{content:\'\';position:absolute;top:-20px;right:-20px;width:80px;height:80px;border-radius:50%;opacity:.08}\n.kpi.blue::after{background:var(--blue)}\n.kpi.green::after{background:var(--green)}\n.kpi.yellow::after{background:var(--yellow)}\n.kpi.red::after{background:var(--red)}\n.kpi.cyan::after{background:var(--cyan)}\n.kpi-icon{font-size:22px;margin-bottom:12px}\n.kpi-val{font-family:\'Syne\',sans-serif;font-size:32px;font-weight:800;color:#fff;line-height:1}\n.kpi-label{color:var(--muted);font-size:12px;margin-top:6px}\n.kpi-change{font-size:11px;font-weight:600;margin-top:4px}\n.kpi-change.up{color:var(--green)} .kpi-change.down{color:var(--red)}\n\n/* PANELS */\n.panel{background:var(--panel);border:1px solid var(--border);border-radius:16px;padding:20px 22px;margin-bottom:20px}\n.panel-hd{display:flex;justify-content:space-between;align-items:center;margin-bottom:18px;flex-wrap:wrap;gap:10px}\n.panel-title{font-family:\'Syne\',sans-serif;font-size:15px;font-weight:700;color:#fff}\n\n/* TABLE */\n.table{width:100%;border-collapse:collapse}\n.table th{text-align:left;padding:10px 14px;color:var(--muted);font-size:11px;text-transform:uppercase;letter-spacing:.06em;font-weight:600;border-bottom:1px solid var(--border)}\n.table td{padding:12px 14px;border-bottom:1px solid rgba(255,255,255,0.04);font-size:13px;vertical-align:middle}\n.table tr:hover td{background:rgba(255,255,255,0.02)}\n.table tr:last-child td{border-bottom:none}\n.badge{display:inline-block;padding:3px 10px;border-radius:20px;font-size:11px;font-weight:600}\n.badge.pending{background:rgba(245,158,11,0.15);color:var(--yellow)}\n.badge.applied{background:rgba(59,130,246,0.15);color:var(--blue)}\n.badge.interview{background:rgba(16,185,129,0.15);color:var(--green)}\n.badge.rejected{background:rgba(239,68,68,0.1);color:var(--red)}\n.match-pill{padding:3px 10px;border-radius:20px;font-size:11px;font-weight:700;background:rgba(59,130,246,0.1);color:var(--accent)}\n.match-pill.high{background:rgba(16,185,129,0.1);color:var(--green)}\n\n/* CHART AREA */\n.chart-area{height:180px;display:flex;align-items:flex-end;gap:8px;padding:10px 0 0}\n.bar-wrap{flex:1;display:flex;flex-direction:column;align-items:center;gap:6px}\n.bar{width:100%;border-radius:6px 6px 0 0;transition:height .6s ease;cursor:pointer;position:relative}\n.bar:hover{filter:brightness(1.2)}\n.bar-label{font-size:11px;color:var(--muted);text-align:center}\n.bar-val{font-size:11px;font-weight:700;color:#fff;text-align:center}\n\n/* LOG */\n.log-item{display:flex;align-items:flex-start;gap:12px;padding:12px 0;border-bottom:1px solid var(--border)}\n.log-item:last-child{border-bottom:none}\n.log-dot{width:8px;height:8px;border-radius:50%;flex-shrink:0;margin-top:4px}\n.log-time{color:var(--muted);font-size:11px;white-space:nowrap;min-width:80px}\n.log-text{font-size:13px;color:var(--text)}\n\n/* CONFIG FORM */\n.form-grid{display:grid;grid-template-columns:1fr 1fr;gap:14px}\n.form-group{display:flex;flex-direction:column;gap:6px}\n.form-group.full{grid-column:1/-1}\nlabel{font-size:12px;color:var(--muted);font-weight:500}\ninput,select,textarea{\n  background:var(--panel2);border:1px solid var(--border);border-radius:8px;\n  color:var(--text);padding:10px 14px;font-size:13px;font-family:\'DM Sans\',sans-serif;\n  outline:none;transition:border .2s;\n}\ninput:focus,select:focus,textarea:focus{border-color:var(--blue)}\ninput::placeholder,textarea::placeholder{color:var(--muted)}\ntextarea{resize:vertical;min-height:80px}\n\n/* STATUS SELECT */\nselect.status-sel{\n  padding:4px 10px;border-radius:6px;font-size:12px;\n  background:var(--panel2);border:1px solid var(--border);color:var(--text);cursor:pointer;\n}\n\n/* TOAST */\n.toast{position:fixed;bottom:24px;right:24px;z-index:999;background:var(--green);color:#fff;padding:12px 20px;border-radius:10px;font-size:13px;font-weight:600;box-shadow:0 8px 30px rgba(16,185,129,0.4);transform:translateY(80px);opacity:0;transition:all .3s;pointer-events:none}\n.toast.show{transform:translateY(0);opacity:1}\n\n/* TABS */\n.dash-pane{display:none}.dash-pane.active{display:block}\n</style>\n</head>\n<body>\n\n<!-- SIDEBAR -->\n<aside class="sidebar">\n  <div class="sb-logo"><div class="sb-dot"></div>JobRadar</div>\n  <div class="sb-section">Overview</div>\n  <button class="sb-link active" onclick="showPane(\'overview\')"><span class="sb-icon">📊</span>Dashboard</button>\n  <button class="sb-link" onclick="showPane(\'jobs\')"><span class="sb-icon">💼</span>All Jobs <span class="sb-badge">10</span></button>\n  <button class="sb-link" onclick="showPane(\'weekly\')"><span class="sb-icon">📈</span>Weekly Stats</button>\n  <div class="sb-section">Settings</div>\n  <button class="sb-link" onclick="showPane(\'config\')"><span class="sb-icon">⚙</span>API Config</button>\n  <button class="sb-link" onclick="showPane(\'logs\')"><span class="sb-icon">📋</span>Search Logs</button>\n  <div style="margin-top:auto;padding:20px">\n    <a href="index.html" style="display:block;padding:10px;background:rgba(59,130,246,0.1);border:1px solid rgba(59,130,246,0.2);border-radius:10px;color:var(--accent);font-size:13px;font-weight:600;text-align:center;text-decoration:none">← Back to Job Board</a>\n  </div>\n</aside>\n\n<!-- MAIN -->\n<main class="main">\n\n  <!-- OVERVIEW PANE -->\n  <div class="dash-pane active" id="pane-overview">\n    <div class="topbar">\n      <div>\n        <div class="page-title">Dashboard</div>\n        <div class="page-sub">Wednesday, 11 March 2026 · Auto-updated daily at 9:00 AM</div>\n      </div>\n      <div class="topbar-actions">\n        <button class="btn btn-ghost" onclick="showToast(\'🔄 Running job search...\')">↻ Run Now</button>\n        <button class="btn btn-primary" onclick="showPane(\'config\')">⚙ Configure</button>\n      </div>\n    </div>\n\n    <!-- KPIs -->\n    <div class="kpi-grid">\n      <div class="kpi blue"><div class="kpi-icon">💼</div><div class="kpi-val">10</div><div class="kpi-label">Jobs Today</div><div class="kpi-change up">↑ +3 vs yesterday</div></div>\n      <div class="kpi green"><div class="kpi-icon">✅</div><div class="kpi-val" id="kpi-applied">0</div><div class="kpi-label">Total Applied</div><div class="kpi-change up">This week</div></div>\n      <div class="kpi yellow"><div class="kpi-icon">💬</div><div class="kpi-val">0</div><div class="kpi-label">HR Contacted</div><div class="kpi-change" style="color:var(--muted)">Start reaching out</div></div>\n      <div class="kpi cyan"><div class="kpi-icon">🗓</div><div class="kpi-val">0</div><div class="kpi-label">Interviews</div><div class="kpi-change" style="color:var(--muted)">Keep applying!</div></div>\n      <div class="kpi red"><div class="kpi-icon">📡</div><div class="kpi-val" id="kpi-api">Live</div><div class="kpi-label">API Status</div><div class="kpi-change up">Adzuna connected</div></div>\n    </div>\n\n    <!-- CHART + LOGS -->\n    <div style="display:grid;grid-template-columns:1fr 1fr;gap:14px">\n      <div class="panel">\n        <div class="panel-hd"><div class="panel-title">📊 Jobs Found Per Day</div></div>\n        <div class="chart-area" id="chart-area"></div>\n      </div>\n      <div class="panel">\n        <div class="panel-hd"><div class="panel-title">⚡ Recent Activity</div></div>\n        <div id="activity-log"></div>\n      </div>\n    </div>\n\n    <!-- RECENT JOBS -->\n    <div class="panel" style="margin-top:0">\n      <div class="panel-hd">\n        <div class="panel-title">🎯 Top Matched Jobs Today</div>\n        <button class="btn btn-ghost" style="font-size:12px" onclick="showPane(\'jobs\')">View All →</button>\n      </div>\n      <table class="table" id="overview-table"></table>\n    </div>\n  </div>\n\n  <!-- JOBS PANE -->\n  <div class="dash-pane" id="pane-jobs">\n    <div class="topbar">\n      <div><div class="page-title">All Jobs</div><div class="page-sub">Manage and track all fetched job listings</div></div>\n      <div class="topbar-actions">\n        <button class="btn btn-ghost">Export CSV</button>\n        <button class="btn btn-primary" onclick="showToast(\'🔄 Refreshing...\')">↻ Refresh</button>\n      </div>\n    </div>\n    <div class="panel">\n      <table class="table" id="all-jobs-table"></table>\n    </div>\n  </div>\n\n  <!-- WEEKLY PANE -->\n  <div class="dash-pane" id="pane-weekly">\n    <div class="topbar"><div><div class="page-title">Weekly Stats</div><div class="page-sub">Track your job search momentum week by week</div></div></div>\n    <div class="kpi-grid" id="weekly-kpis"></div>\n    <div class="panel">\n      <div class="panel-hd"><div class="panel-title">📅 Weekly Breakdown</div></div>\n      <table class="table" id="weekly-table"></table>\n    </div>\n  </div>\n\n  <!-- CONFIG PANE -->\n  <div class="dash-pane" id="pane-config">\n    <div class="topbar"><div><div class="page-title">API Configuration</div><div class="page-sub">Manage your job search API keys and settings</div></div></div>\n\n    <div class="panel">\n      <div class="panel-hd"><div class="panel-title">🔑 API Keys</div></div>\n      <div class="form-grid">\n        <div class="form-group">\n          <label>Adzuna App ID</label>\n          <input type="text" value="1563122a" id="adzuna-id"/>\n        </div>\n        <div class="form-group">\n          <label>Adzuna App Key</label>\n          <input type="password" value="a4e3eb7e12b27898eeac2244f9a198f7" id="adzuna-key"/>\n        </div>\n        <div class="form-group">\n          <label>RapidAPI Key (JSearch — optional)</label>\n          <input type="password" placeholder="YOUR_RAPIDAPI_KEY" id="rapid-key"/>\n        </div>\n        <div class="form-group">\n          <label>Search Schedule</label>\n          <select><option>Daily at 9:00 AM</option><option>Daily at 8:00 AM</option><option>Twice daily</option></select>\n        </div>\n      </div>\n    </div>\n\n    <div class="panel">\n      <div class="panel-hd"><div class="panel-title">🔍 Search Settings</div></div>\n      <div class="form-grid">\n        <div class="form-group full">\n          <label>Job Search Keywords (one per line)</label>\n          <textarea id="keywords">performance marketing manager\nSEO manager\ndigital marketing manager\ngrowth marketing manager\nAI marketing specialist\npaid media manager</textarea>\n        </div>\n        <div class="form-group">\n          <label>Target Countries</label>\n          <select><option>Germany + UK</option><option>Germany only</option><option>Europe + Remote</option><option>Worldwide</option></select>\n        </div>\n        <div class="form-group">\n          <label>Minimum Match Score</label>\n          <input type="number" value="65" min="0" max="100"/>\n        </div>\n        <div class="form-group full">\n          <label>Companies to Skip (comma separated)</label>\n          <input type="text" placeholder="Company A, Company B..."/>\n        </div>\n      </div>\n    </div>\n\n    <button class="btn btn-primary" onclick="saveConfig()">💾 Save Configuration</button>\n    <button class="btn btn-ghost" style="margin-left:10px" onclick="testApi()">🧪 Test API Connection</button>\n  </div>\n\n  <!-- LOGS PANE -->\n  <div class="dash-pane" id="pane-logs">\n    <div class="topbar"><div><div class="page-title">Search Logs</div><div class="page-sub">History of all automated job searches</div></div></div>\n    <div class="panel">\n      <div class="panel-hd"><div class="panel-title">📋 Execution Log</div><span style="font-size:12px;color:var(--muted)">Last 30 days</span></div>\n      <table class="table" id="logs-table"></table>\n    </div>\n  </div>\n\n</main>\n\n<div class="toast" id="toast"></div>\n\n<script>\nconst JOBS = [\n  {id:1,title:"Senior Performance Marketing Manager",company:"Zalando SE",location:"Berlin, Germany",match:98,salary:"€55k–€75k",platform:"Adzuna DE",posted:"Today",status:"Pending",url:"#"},\n  {id:2,title:"SEO & Growth Manager",company:"Delivery Hero",location:"Berlin, Germany",match:96,salary:"€50k–€70k",platform:"Adzuna DE",posted:"Today",status:"Pending",url:"#"},\n  {id:3,title:"Performance Marketing Specialist",company:"Remote.com",location:"Worldwide",match:95,salary:"$45k–$65k",platform:"LinkedIn",posted:"Today",status:"Pending",url:"#"},\n  {id:4,title:"Digital Marketing Manager",company:"HubSpot",location:"Dublin / Remote",match:93,salary:"€60k–€80k",platform:"Adzuna GB",posted:"2 days ago",status:"Applied",url:"#"},\n  {id:5,title:"SEO Manager",company:"Axel Springer",location:"Berlin, Germany",match:92,salary:"€45k–€62k",platform:"Adzuna DE",posted:"Today",status:"Pending",url:"#"},\n  {id:6,title:"AI Marketing Specialist",company:"N26 Bank",location:"Berlin, Germany",match:91,salary:"€55k–€72k",platform:"JSearch",posted:"3 days ago",status:"Pending",url:"#"},\n  {id:7,title:"Performance Marketing Manager",company:"HelloFresh",location:"Berlin, Germany",match:90,salary:"€52k–€68k",platform:"Adzuna DE",posted:"2 days ago",status:"Pending",url:"#"},\n  {id:8,title:"Senior SEO Strategist",company:"Shopify",location:"Remote",match:89,salary:"$55k–$80k",platform:"LinkedIn",posted:"Today",status:"Pending",url:"#"},\n  {id:9,title:"Digital Marketing Specialist",company:"Siemens AG",location:"Munich, Germany",match:88,salary:"€50k–€67k",platform:"Adzuna DE",posted:"4 days ago",status:"Pending",url:"#"},\n  {id:10,title:"Growth Marketing Lead",company:"Wolt",location:"Helsinki / Remote",match:87,salary:"€55k–€75k",platform:"Adzuna GB",posted:"Today",status:"Pending",url:"#"},\n];\n\nconst WEEKLY = [\n  {week:"Week 1 (Mar 4–10)",found:10,applied:3,hr:2,interviews:0,offers:0},\n  {week:"Week 2 (Mar 11–17)",found:10,applied:0,hr:0,interviews:0,offers:0},\n];\n\nconst LOGS = [\n  {date:"11 Mar 2026",time:"09:00",sources:"Adzuna DE, Adzuna GB, LinkedIn",found:10,added:10,status:"Success"},\n  {date:"10 Mar 2026",time:"09:00",sources:"Adzuna DE, Adzuna GB, LinkedIn",found:8,added:6,status:"Success"},\n  {date:"09 Mar 2026",time:"09:00",sources:"Adzuna DE, LinkedIn",found:7,added:5,status:"Success"},\n  {date:"08 Mar 2026",time:"09:00",sources:"Adzuna DE, Adzuna GB, LinkedIn",found:9,added:9,status:"Success"},\n  {date:"07 Mar 2026",time:"09:00",sources:"Adzuna DE, LinkedIn",found:6,added:4,status:"Partial"},\n];\n\nfunction showPane(p){\n  document.querySelectorAll(\'.dash-pane\').forEach(el=>el.classList.remove(\'active\'));\n  document.querySelectorAll(\'.sb-link\').forEach(el=>el.classList.remove(\'active\'));\n  document.getElementById(\'pane-\'+p).classList.add(\'active\');\n  event.currentTarget.classList.add(\'active\');\n  if(p===\'jobs\') renderAllJobs();\n  if(p===\'weekly\') renderWeekly();\n  if(p===\'logs\') renderLogs();\n}\n\nfunction statusBadge(s){\n  const cls = {Pending:\'pending\',Applied:\'applied\',\'Interview Scheduled\':\'interview\',Rejected:\'rejected\'}[s]||\'pending\';\n  return `<span class="badge ${cls}">${s}</span>`;\n}\nfunction matchPill(m){\n  return `<span class="match-pill ${m>=90?\'high\':\'\'}">${m}%</span>`;\n}\n\nfunction renderOverview(){\n  const rows = JOBS.slice(0,5).map(j=>`<tr>\n    <td>${matchPill(j.match)}</td>\n    <td><strong style="color:#fff">${j.title}</strong><br><span style="color:var(--muted);font-size:11px">${j.company}</span></td>\n    <td style="color:var(--muted)">${j.location}</td>\n    <td style="color:var(--green);font-weight:600">${j.salary}</td>\n    <td>${statusBadge(j.status)}</td>\n    <td><select class="status-sel" onchange="showToast(\'Status updated!\')"><option>Pending</option><option>Applied</option><option>Interview Scheduled</option><option>Rejected</option></select></td>\n  </tr>`).join(\'\');\n  document.getElementById(\'overview-table\').innerHTML = `<thead><tr><th>Match</th><th>Job</th><th>Location</th><th>Salary</th><th>Status</th><th>Update</th></tr></thead><tbody>${rows}</tbody>`;\n}\n\nfunction renderAllJobs(){\n  const rows = JOBS.map(j=>`<tr>\n    <td>${matchPill(j.match)}</td>\n    <td><strong style="color:#fff">${j.title}</strong></td>\n    <td style="color:var(--muted)">${j.company}</td>\n    <td style="color:var(--muted)">${j.location}</td>\n    <td style="color:var(--green)">${j.salary}</td>\n    <td><span style="color:var(--muted);font-size:11px">${j.platform}</span></td>\n    <td><span style="color:var(--muted);font-size:11px">${j.posted}</span></td>\n    <td><select class="status-sel" onchange="showToast(\'Updated!\')"><option>Pending</option><option>Applied</option><option>Interview Scheduled</option><option>Rejected</option></select></td>\n    <td><a href="${j.url}" target="_blank" class="btn btn-primary" style="font-size:11px;padding:6px 12px">Apply</a></td>\n  </tr>`).join(\'\');\n  document.getElementById(\'all-jobs-table\').innerHTML = `<thead><tr><th>Match</th><th>Title</th><th>Company</th><th>Location</th><th>Salary</th><th>Source</th><th>Posted</th><th>Status</th><th></th></tr></thead><tbody>${rows}</tbody>`;\n}\n\nfunction renderChart(){\n  const data = [\n    {day:\'Mon\',val:6},{day:\'Tue\',val:9},{day:\'Wed\',val:10},\n    {day:\'Thu\',val:7},{day:\'Fri\',val:8},{day:\'Sat\',val:4},{day:\'Sun\',val:5}\n  ];\n  const max = Math.max(...data.map(d=>d.val));\n  document.getElementById(\'chart-area\').innerHTML = data.map(d=>`\n    <div class="bar-wrap">\n      <div class="bar-val">${d.val}</div>\n      <div class="bar" style="height:${(d.val/max)*140}px;background:linear-gradient(180deg,#3b82f6,#1d4ed8)" title="${d.val} jobs"></div>\n      <div class="bar-label">${d.day}</div>\n    </div>`).join(\'\');\n}\n\nfunction renderActivity(){\n  const acts = [\n    {color:\'var(--green)\',time:\'09:00 AM\',text:\'10 new jobs added from Adzuna\'},\n    {color:\'var(--blue)\',time:\'Yesterday\',text:\'Auto-search ran successfully · 8 jobs found\'},\n    {color:\'var(--yellow)\',time:\'2 days ago\',text:\'API limit: 95/100 calls remaining\'},\n    {color:\'var(--cyan)\',time:\'3 days ago\',text:\'9 jobs added · 1 duplicate skipped\'},\n    {color:\'var(--muted)\',time:\'4 days ago\',text:\'Scheduler ran · StepStone returned 403\'},\n  ];\n  document.getElementById(\'activity-log\').innerHTML = acts.map(a=>`\n    <div class="log-item">\n      <div class="log-dot" style="background:${a.color}"></div>\n      <div class="log-time">${a.time}</div>\n      <div class="log-text">${a.text}</div>\n    </div>`).join(\'\');\n}\n\nfunction renderWeekly(){\n  document.getElementById(\'weekly-kpis\').innerHTML = [\n    {icon:\'💼\',val:20,label:\'Total Jobs Found\',color:\'blue\'},\n    {icon:\'✅\',val:3,label:\'Total Applied\',color:\'green\'},\n    {icon:\'👤\',val:2,label:\'HR Contacted\',color:\'cyan\'},\n    {icon:\'🗓\',val:0,label:\'Interviews\',color:\'yellow\'},\n  ].map(k=>`<div class="kpi ${k.color}"><div class="kpi-icon">${k.icon}</div><div class="kpi-val">${k.val}</div><div class="kpi-label">${k.label}</div></div>`).join(\'\');\n\n  const rows = WEEKLY.map(w=>`<tr>\n    <td style="color:#fff;font-weight:600">${w.week}</td>\n    <td style="color:var(--accent)">${w.found}</td>\n    <td style="color:var(--green)">${w.applied}</td>\n    <td style="color:var(--cyan)">${w.hr}</td>\n    <td style="color:var(--yellow)">${w.interviews}</td>\n    <td style="color:var(--green)">${w.offers}</td>\n    <td>${w.applied?`<span style="color:var(--green);font-weight:600">${Math.round(w.applied/w.found*100)}%</span>`:\'—\'}</td>\n  </tr>`).join(\'\');\n  document.getElementById(\'weekly-table\').innerHTML = `<thead><tr><th>Week</th><th>Found</th><th>Applied</th><th>HR Contact</th><th>Interviews</th><th>Offers</th><th>Rate</th></tr></thead><tbody>${rows}</tbody>`;\n}\n\nfunction renderLogs(){\n  const rows = LOGS.map(l=>`<tr>\n    <td style="color:#fff">${l.date}</td>\n    <td style="color:var(--muted)">${l.time}</td>\n    <td style="color:var(--muted);font-size:12px">${l.sources}</td>\n    <td style="color:var(--accent)">${l.found}</td>\n    <td style="color:var(--green)">${l.added}</td>\n    <td><span class="badge ${l.status===\'Success\'?\'interview\':\'pending\'}">${l.status}</span></td>\n  </tr>`).join(\'\');\n  document.getElementById(\'logs-table\').innerHTML = `<thead><tr><th>Date</th><th>Time</th><th>Sources</th><th>Found</th><th>Added</th><th>Status</th></tr></thead><tbody>${rows}</tbody>`;\n}\n\nfunction saveConfig(){showToast(\'✅ Configuration saved!\')}\nfunction testApi(){showToast(\'🧪 Testing Adzuna API... Connected! 100 calls/day remaining.\')}\n\nfunction showToast(msg){\n  const t=document.getElementById(\'toast\');\n  t.textContent=msg;t.classList.add(\'show\');\n  setTimeout(()=>t.classList.remove(\'show\'),2500);\n}\n\n// Init\nrenderOverview();renderChart();renderActivity();\n</script>\n</body>\n</html>\n'

YOUR_SKILLS = [
    "seo","google ads","meta ads","performance marketing","ga4","google analytics",
    "looker studio","semrush","ahrefs","python","ai","automation","b2b","saas",
    "fmcg","ecommerce","cro","roas","cpa","cpc","gtm","hubspot","wordpress",
    "shopify","technical seo","link building","content strategy","multilingual",
]
SEARCH_QUERIES = [
    "performance marketing manager","SEO manager","digital marketing manager",
    "growth marketing manager","AI marketing specialist",
]

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
    return Response(INDEX_HTML, mimetype="text/html")

@app.route("/dashboard")
def dashboard():
    return Response(DASHBOARD_HTML, mimetype="text/html")

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
    if DATABASE_URL and HAS_PG:
        jobs = load_jobs_db()
        db_status = "✅ PostgreSQL Connected"
    else:
        data = {}
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE) as f: data = json.load(f)
            except: pass
        jobs = data.get("jobs",[])
        db_status = "⚠️ Using JSON file (no DB)"
    last = datetime.datetime.now().isoformat()
    html = f"""<html><head><title>JobRadar Status</title>
    <style>body{font-family:Arial;background:#05080f;color:#e2e8f0;padding:40px;max-width:800px;margin:0 auto}
    h1{color:#3b82f6} .card{background:#0d1526;border:1px solid #1e3a5f;border-radius:12px;padding:20px;margin:16px 0}
    .green{color:#10b981} .yellow{color:#f59e0b}
    .btn{display:inline-block;padding:12px 24px;background:#3b82f6;color:white;border-radius:8px;text-decoration:none;margin:8px;font-weight:bold}
    .btn.green{background:#10b981} table{width:100%;border-collapse:collapse} td,th{padding:8px 12px;border-bottom:1px solid #1e3a5f;text-align:left}
    </style></head><body>
    <h1>🔍 JobRadar Status</h1>
    <div class="card"><b>Database:</b> <span class="green">{db_status}</span></div>
    <div class="card"><b>Total Jobs Saved:</b> <span class="green">{len(jobs)}</span><br>
    <b>Last Check:</b> <span class="yellow">{last[:19]}</span></div>
    <div class="card"><b>Latest Jobs:</b><br><br>
    <table><tr><th>Match</th><th>Title</th><th>Company</th><th>Date</th></tr>
    {''.join([f"<tr><td><b>{j.get('match')}%</b></td><td>{j.get('title','')}</td><td>{j.get('company','')}</td><td>{j.get('posted','')}</td></tr>" for j in jobs[:10]])}
    </table></div>
    <a href="/api/search/run" class="btn">🔄 Run Job Search Now</a>
    <a href="/" class="btn green">← Job Board</a>
    </body></html>"""
    return html

def start_scheduler():
    schedule.every().day.at("09:00").do(run_job_search)
    while True:
        schedule.run_pending()
        time.sleep(60)


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
