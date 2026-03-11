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

INDEX_HTML = '<!DOCTYPE html>\n<html lang="en">\n<head>\n<meta charset="UTF-8"/>\n<meta name="viewport" content="width=device-width,initial-scale=1.0"/>\n<title>JobRadar — Saddam\'s AI Job Search</title>\n<link href="https://fonts.googleapis.com/css2?family=Clash+Display:wght@400;500;600;700&family=Cabinet+Grotesk:wght@300;400;500;700;800&display=swap" rel="stylesheet"/>\n<style>\n*{margin:0;padding:0;box-sizing:border-box}\n:root{\n  --ink:#0a0a0f;--ink2:#12121a;--ink3:#1a1a28;\n  --border:rgba(255,255,255,0.07);--border2:rgba(255,255,255,0.12);\n  --blue:#4f7cff;--blue2:#3b63e8;--cyan:#00d4ff;--green:#00e5a0;\n  --yellow:#ffd166;--red:#ff6b6b;--purple:#9b72ff;\n  --text:#f0f0f8;--muted:#6b7280;--soft:#9ca3af;\n}\nhtml{scroll-behavior:smooth}\nbody{background:var(--ink);color:var(--text);font-family:\'Cabinet Grotesk\',sans-serif;font-size:15px;overflow-x:hidden}\n\n/* NOISE TEXTURE */\nbody::after{content:\'\';position:fixed;inset:0;pointer-events:none;z-index:999;\n  background-image:url("data:image/svg+xml,%3Csvg viewBox=\'0 0 256 256\' xmlns=\'http://www.w3.org/2000/svg\'%3E%3Cfilter id=\'noise\'%3E%3CfeTurbulence type=\'fractalNoise\' baseFrequency=\'0.9\' numOctaves=\'4\' stitchTiles=\'stitch\'/%3E%3C/filter%3E%3Crect width=\'100%25\' height=\'100%25\' filter=\'url(%23noise)\' opacity=\'0.03\'/%3E%3C/svg%3E");\n  opacity:.4}\n\n/* GLOW BLOBS */\n.blob{position:fixed;border-radius:50%;filter:blur(120px);pointer-events:none;z-index:0}\n.blob1{width:600px;height:600px;background:rgba(79,124,255,0.08);top:-200px;left:-200px}\n.blob2{width:500px;height:500px;background:rgba(0,212,255,0.06);bottom:-100px;right:-100px}\n.blob3{width:400px;height:400px;background:rgba(155,114,255,0.05);top:50%;left:50%;transform:translate(-50%,-50%)}\n\n/* NAV */\nnav{position:sticky;top:0;z-index:100;\n  background:rgba(10,10,15,0.8);backdrop-filter:blur(24px);\n  border-bottom:1px solid var(--border);padding:0 24px}\n.nav-inner{max-width:1280px;margin:0 auto;height:64px;display:flex;align-items:center;justify-content:space-between;gap:20px}\n.logo{display:flex;align-items:center;gap:12px;text-decoration:none}\n.logo-mark{width:36px;height:36px;background:linear-gradient(135deg,var(--blue),var(--cyan));\n  border-radius:10px;display:flex;align-items:center;justify-content:center;\n  font-size:18px;font-weight:800;color:#fff;font-family:\'Clash Display\',sans-serif;\n  box-shadow:0 0 20px rgba(79,124,255,0.4)}\n.logo-text{font-family:\'Clash Display\',sans-serif;font-size:20px;font-weight:700;color:#fff;letter-spacing:-.02em}\n.logo-text span{color:var(--cyan)}\n.nav-pills{display:flex;gap:2px;background:var(--ink2);border:1px solid var(--border);border-radius:12px;padding:4px}\n.nav-pill{padding:7px 16px;border-radius:9px;border:none;background:none;\n  color:var(--muted);font-size:13px;font-weight:600;cursor:pointer;\n  transition:all .2s;font-family:\'Cabinet Grotesk\',sans-serif;white-space:nowrap}\n.nav-pill:hover{color:var(--text)}\n.nav-pill.active{background:var(--ink3);color:#fff;box-shadow:0 2px 8px rgba(0,0,0,.4)}\n.nav-count{display:inline-flex;align-items:center;justify-content:center;\n  width:20px;height:20px;border-radius:50%;background:var(--blue);\n  color:#fff;font-size:10px;font-weight:800;margin-left:6px}\n.nav-right{display:flex;align-items:center;gap:10px}\n.live-badge{display:flex;align-items:center;gap:6px;padding:6px 12px;\n  background:rgba(0,229,160,0.08);border:1px solid rgba(0,229,160,0.2);\n  border-radius:20px;font-size:11px;font-weight:700;color:var(--green);letter-spacing:.05em}\n.live-dot{width:6px;height:6px;border-radius:50%;background:var(--green);\n  box-shadow:0 0 8px var(--green);animation:blink 1.5s infinite}\n@keyframes blink{0%,100%{opacity:1}50%{opacity:.3}}\n.btn-dash{padding:8px 16px;border-radius:9px;background:var(--ink3);\n  border:1px solid var(--border2);color:var(--soft);font-size:13px;font-weight:600;\n  text-decoration:none;transition:all .2s;display:flex;align-items:center;gap:6px}\n.btn-dash:hover{color:#fff;border-color:var(--blue)}\n\n/* HERO */\n.hero{position:relative;z-index:1;padding:80px 24px 60px;text-align:center;max-width:1280px;margin:0 auto}\n.hero-eyebrow{display:inline-flex;align-items:center;gap:8px;margin-bottom:28px;\n  padding:8px 20px;background:rgba(79,124,255,0.08);\n  border:1px solid rgba(79,124,255,0.2);border-radius:30px;\n  font-size:12px;font-weight:700;color:var(--blue);letter-spacing:.1em;text-transform:uppercase}\n.hero h1{font-family:\'Clash Display\',sans-serif;font-size:clamp(44px,7vw,88px);\n  font-weight:700;line-height:1.0;letter-spacing:-.03em;color:#fff;margin-bottom:24px}\n.hero h1 em{font-style:normal;\n  background:linear-gradient(90deg,var(--blue),var(--cyan),var(--purple));\n  -webkit-background-clip:text;-webkit-text-fill-color:transparent;\n  background-clip:text}\n.hero-sub{font-size:18px;color:var(--soft);max-width:560px;margin:0 auto 48px;line-height:1.7;font-weight:400}\n\n/* STATS ROW */\n.stats-row{display:flex;justify-content:center;gap:0;margin-bottom:48px;\n  background:var(--ink2);border:1px solid var(--border);border-radius:20px;\n  overflow:hidden;max-width:680px;margin-left:auto;margin-right:auto;margin-bottom:48px}\n.stat-item{flex:1;padding:24px 20px;text-align:center;border-right:1px solid var(--border)}\n.stat-item:last-child{border-right:none}\n.stat-num{font-family:\'Clash Display\',sans-serif;font-size:36px;font-weight:700;\n  color:#fff;line-height:1;margin-bottom:6px}\n.stat-num.blue{color:var(--blue)}\n.stat-num.green{color:var(--green)}\n.stat-num.yellow{color:var(--yellow)}\n.stat-num.purple{color:var(--purple)}\n.stat-lbl{font-size:11px;color:var(--muted);font-weight:600;text-transform:uppercase;letter-spacing:.08em}\n\n/* HERO ACTIONS */\n.hero-btns{display:flex;justify-content:center;gap:12px;flex-wrap:wrap}\n.btn-main{padding:14px 32px;border-radius:12px;font-size:15px;font-weight:700;\n  cursor:pointer;border:none;text-decoration:none;transition:all .25s;\n  display:inline-flex;align-items:center;gap:8px;font-family:\'Cabinet Grotesk\',sans-serif}\n.btn-primary{background:linear-gradient(135deg,var(--blue),var(--blue2));color:#fff;\n  box-shadow:0 4px 24px rgba(79,124,255,0.35)}\n.btn-primary:hover{transform:translateY(-2px);box-shadow:0 8px 32px rgba(79,124,255,0.5)}\n.btn-outline{background:transparent;color:var(--text);border:1px solid var(--border2)}\n.btn-outline:hover{border-color:var(--blue);color:var(--blue)}\n\n/* MAIN CONTENT */\n.main{position:relative;z-index:1;max-width:1280px;margin:0 auto;padding:0 24px 80px}\n\n/* TABS */\n.tab-row{display:flex;gap:2px;background:var(--ink2);border:1px solid var(--border);\n  border-radius:14px;padding:4px;margin-bottom:32px;overflow-x:auto}\n.tab{flex:1;min-width:120px;padding:11px 20px;border-radius:11px;border:none;\n  cursor:pointer;font-size:13px;font-weight:700;transition:all .2s;\n  background:transparent;color:var(--muted);font-family:\'Cabinet Grotesk\',sans-serif;\n  white-space:nowrap;letter-spacing:.01em}\n.tab:hover{color:var(--text)}\n.tab.active{background:var(--ink3);color:#fff;box-shadow:0 2px 12px rgba(0,0,0,.5)}\n\n/* TOOLBAR */\n.toolbar{display:flex;gap:10px;align-items:center;margin-bottom:24px;flex-wrap:wrap}\n.search-box{position:relative;flex:1;min-width:200px}\n.search-box input{width:100%;padding:11px 16px 11px 44px;background:var(--ink2);\n  border:1px solid var(--border);border-radius:11px;color:var(--text);\n  font-size:14px;font-family:\'Cabinet Grotesk\',sans-serif;outline:none;transition:border .2s}\n.search-box input:focus{border-color:rgba(79,124,255,0.5)}\n.search-box input::placeholder{color:var(--muted)}\n.search-icon{position:absolute;left:15px;top:50%;transform:translateY(-50%);color:var(--muted);font-size:16px}\n.chip{padding:10px 16px;border-radius:10px;background:var(--ink2);\n  border:1px solid var(--border);color:var(--muted);font-size:13px;font-weight:600;\n  cursor:pointer;transition:all .2s;white-space:nowrap;font-family:\'Cabinet Grotesk\',sans-serif}\n.chip:hover,.chip.on{border-color:var(--blue);color:var(--blue);background:rgba(79,124,255,0.08)}\n.count-chip{padding:10px 16px;border-radius:10px;background:var(--ink2);\n  border:1px solid var(--border);color:var(--muted);font-size:13px;white-space:nowrap}\n\n/* JOB CARDS */\n.jobs-list{display:flex;flex-direction:column;gap:10px}\n.job-card{background:var(--ink2);border:1px solid var(--border);border-radius:16px;\n  padding:22px 24px;transition:all .3s;position:relative;overflow:hidden;\n  animation:slideUp .4s ease both}\n@keyframes slideUp{from{opacity:0;transform:translateY(20px)}to{opacity:1;transform:translateY(0)}}\n.job-card::after{content:\'\';position:absolute;inset:0;\n  background:linear-gradient(135deg,rgba(79,124,255,0.03),transparent);\n  opacity:0;transition:opacity .3s;pointer-events:none}\n.job-card:hover{border-color:rgba(79,124,255,0.3);transform:translateY(-2px);\n  box-shadow:0 8px 40px rgba(0,0,0,.4)}\n.job-card:hover::after{opacity:1}\n.job-card.applied-card{border-color:rgba(0,229,160,0.2);background:rgba(0,229,160,0.02)}\n.job-card.hot-card{border-color:rgba(255,209,102,0.2)}\n\n/* ACCENT BAR */\n.job-card .accent-bar{position:absolute;left:0;top:16px;bottom:16px;width:3px;\n  border-radius:0 3px 3px 0;background:linear-gradient(180deg,var(--blue),var(--cyan));\n  opacity:0;transition:opacity .3s}\n.job-card:hover .accent-bar,.job-card.applied-card .accent-bar{opacity:1}\n.job-card.applied-card .accent-bar{background:linear-gradient(180deg,var(--green),#00c88a)}\n.job-card.hot-card .accent-bar{background:linear-gradient(180deg,var(--yellow),#ffb700)}\n\n.card-body{display:flex;gap:18px;align-items:flex-start}\n\n/* SCORE RING */\n.score-ring{flex-shrink:0;position:relative;width:56px;height:56px}\n.score-ring svg{transform:rotate(-90deg)}\n.ring-track{fill:none;stroke:rgba(255,255,255,0.06);stroke-width:4}\n.ring-prog{fill:none;stroke-width:4;stroke-linecap:round;transition:stroke-dashoffset 1s ease}\n.score-val{position:absolute;inset:0;display:flex;flex-direction:column;\n  align-items:center;justify-content:center}\n.score-num{font-family:\'Clash Display\',sans-serif;font-size:14px;font-weight:700;color:#fff;line-height:1}\n.score-pct{font-size:8px;color:var(--muted);text-transform:uppercase;letter-spacing:.05em}\n\n.card-info{flex:1;min-width:0}\n.job-title{font-family:\'Clash Display\',sans-serif;font-size:17px;font-weight:600;\n  color:#fff;margin-bottom:8px;line-height:1.3;letter-spacing:-.01em}\n.job-meta{display:flex;flex-wrap:wrap;gap:12px;align-items:center;margin-bottom:12px}\n.meta-company{font-size:13px;font-weight:700;color:var(--blue)}\n.meta-loc{font-size:12px;color:var(--muted);display:flex;align-items:center;gap:4px}\n.meta-salary{font-size:12px;font-weight:700;color:var(--green)}\n.meta-date{font-size:11px;color:var(--muted)}\n.job-tags{display:flex;flex-wrap:wrap;gap:6px}\n.tag{padding:4px 10px;border-radius:6px;font-size:11px;font-weight:600;\n  background:rgba(255,255,255,0.04);color:var(--muted);border:1px solid var(--border)}\n.tag.type-tag{background:rgba(79,124,255,0.08);color:rgba(79,124,255,0.9);border-color:rgba(79,124,255,0.15)}\n\n/* BADGES */\n.badge-hot{position:absolute;top:14px;right:16px;padding:4px 12px;border-radius:20px;\n  background:linear-gradient(90deg,rgba(255,209,102,0.15),rgba(255,107,107,0.15));\n  border:1px solid rgba(255,209,102,0.3);color:var(--yellow);\n  font-size:10px;font-weight:800;letter-spacing:.06em}\n.badge-applied{position:absolute;top:14px;right:16px;padding:4px 12px;border-radius:20px;\n  background:rgba(0,229,160,0.1);border:1px solid rgba(0,229,160,0.25);\n  color:var(--green);font-size:10px;font-weight:800;letter-spacing:.06em}\n\n/* CARD ACTIONS */\n.card-actions{display:flex;flex-direction:column;gap:8px;flex-shrink:0;min-width:140px}\n.btn-apply{display:block;padding:11px 0;text-align:center;border-radius:10px;\n  background:linear-gradient(135deg,var(--blue),var(--blue2));color:#fff;\n  font-size:13px;font-weight:700;text-decoration:none;border:none;cursor:pointer;\n  transition:all .2s;box-shadow:0 2px 16px rgba(79,124,255,0.3);font-family:\'Cabinet Grotesk\',sans-serif}\n.btn-apply:hover{transform:translateY(-1px);box-shadow:0 4px 24px rgba(79,124,255,0.5)}\n.btn-hr{display:block;padding:10px 0;text-align:center;border-radius:10px;\n  background:transparent;border:1px solid var(--border2);color:var(--soft);\n  font-size:12px;font-weight:600;text-decoration:none;cursor:pointer;transition:all .2s;\n  font-family:\'Cabinet Grotesk\',sans-serif}\n.btn-hr:hover{border-color:var(--blue);color:var(--blue)}\n.btn-row2{display:flex;gap:6px}\n.btn-status{flex:1;padding:9px 0;border-radius:9px;border:none;cursor:pointer;\n  font-size:11px;font-weight:700;transition:all .2s;font-family:\'Cabinet Grotesk\',sans-serif}\n.btn-status.idle{background:rgba(255,255,255,0.04);color:var(--muted)}\n.btn-status.done{background:rgba(0,229,160,0.1);color:var(--green)}\n.btn-star{padding:9px 10px;border-radius:9px;border:none;background:rgba(255,255,255,0.04);\n  cursor:pointer;font-size:14px;transition:all .2s;color:var(--muted)}\n.btn-star.on{background:rgba(255,209,102,0.1);color:var(--yellow)}\n\n/* HR GRID */\n.hr-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:12px}\n.hr-card{background:var(--ink2);border:1px solid var(--border);border-radius:14px;\n  padding:20px;transition:all .2s}\n.hr-card:hover{border-color:rgba(79,124,255,0.3)}\n.hr-co{font-family:\'Clash Display\',sans-serif;font-size:16px;font-weight:600;\n  color:#fff;margin-bottom:4px}\n.hr-loc{font-size:12px;color:var(--muted);margin-bottom:16px}\n.btn-find{display:block;padding:10px;border-radius:10px;text-align:center;\n  background:linear-gradient(135deg,var(--blue),var(--blue2));color:#fff;\n  font-size:13px;font-weight:700;text-decoration:none;transition:all .2s;\n  box-shadow:0 2px 12px rgba(79,124,255,0.25)}\n.btn-find:hover{transform:translateY(-1px);box-shadow:0 4px 20px rgba(79,124,255,0.4)}\n\n/* MSG BOX */\n.msg-box{margin-top:24px;background:var(--ink2);border:1px solid rgba(255,209,102,0.15);\n  border-radius:16px;padding:24px}\n.msg-hd{font-family:\'Clash Display\',sans-serif;font-size:17px;font-weight:600;\n  color:var(--yellow);margin-bottom:16px}\n.msg-body{background:rgba(0,0,0,.3);border-radius:10px;padding:18px 20px;\n  font-size:13px;color:var(--soft);line-height:1.9;font-family:monospace;white-space:pre-wrap}\n.btn-copy{margin-top:12px;padding:10px 20px;border-radius:9px;\n  background:rgba(255,209,102,0.08);border:1px solid rgba(255,209,102,0.2);\n  color:var(--yellow);font-size:12px;font-weight:700;cursor:pointer;transition:all .2s;\n  font-family:\'Cabinet Grotesk\',sans-serif}\n.btn-copy:hover{background:rgba(255,209,102,0.15)}\n\n/* LINKS */\n.links-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:10px}\n.link-card{display:flex;align-items:center;justify-content:space-between;\n  padding:16px 20px;background:var(--ink2);border:1px solid var(--border);\n  border-radius:13px;text-decoration:none;transition:all .2s;color:var(--text)}\n.link-card:hover{border-color:var(--blue);background:var(--ink3);transform:translateY(-1px)}\n.link-name{font-weight:700;font-size:14px}\n.link-region{font-size:11px;color:var(--muted);margin-top:2px}\n.link-arr{color:var(--blue);font-size:18px;font-weight:300}\n\n/* PROGRESS */\n.progress-card{background:var(--ink2);border:1px solid var(--border);\n  border-radius:16px;padding:24px;margin-bottom:24px}\n.progress-hd{font-family:\'Clash Display\',sans-serif;font-size:18px;font-weight:600;\n  color:#fff;margin-bottom:24px}\n.prog-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:20px}\n.prog-item{text-align:center}\n.prog-ring{position:relative;width:72px;height:72px;margin:0 auto 12px}\n.prog-ring svg{transform:rotate(-90deg)}\n.prog-center{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;\n  font-family:\'Clash Display\',sans-serif;font-size:18px;font-weight:700;color:#fff}\n.prog-label{font-size:12px;font-weight:600;color:var(--muted);text-transform:uppercase;letter-spacing:.06em}\n\n/* EMPTY STATE */\n.empty{text-align:center;padding:64px 20px;color:var(--muted)}\n.empty-icon{font-size:48px;margin-bottom:16px}\n.empty-text{font-size:16px}\n\n/* TOAST */\n.toast{position:fixed;bottom:28px;right:28px;z-index:1000;\n  background:var(--green);color:#000;padding:13px 22px;\n  border-radius:12px;font-size:13px;font-weight:800;\n  box-shadow:0 8px 32px rgba(0,229,160,0.35);\n  transform:translateY(80px);opacity:0;transition:all .35s;pointer-events:none}\n.toast.show{transform:translateY(0);opacity:1}\n\n/* SECTION HEADER */\n.sec-hd{display:flex;align-items:center;justify-content:space-between;\n  margin-bottom:24px;flex-wrap:wrap;gap:12px}\n.sec-title{font-family:\'Clash Display\',sans-serif;font-size:22px;font-weight:700;color:#fff}\n.sec-sub{font-size:13px;color:var(--muted);margin-top:4px}\n.btn-refresh{padding:9px 18px;border-radius:9px;background:var(--ink2);\n  border:1px solid var(--border);color:var(--soft);font-size:13px;font-weight:600;\n  cursor:pointer;transition:all .2s;font-family:\'Cabinet Grotesk\',sans-serif}\n.btn-refresh:hover{border-color:var(--blue);color:var(--blue)}\n\nfooter{position:relative;z-index:1;border-top:1px solid var(--border);\n  padding:28px 24px;text-align:center;color:var(--muted);font-size:13px}\nfooter a{color:var(--blue);text-decoration:none}\n\n@media(max-width:640px){\n  .card-body{flex-direction:column}\n  .card-actions{flex-direction:row;min-width:auto;width:100%;flex-wrap:wrap}\n  .btn-apply,.btn-hr{flex:1}\n  .nav-pills{display:none}\n  .stats-row{border-radius:16px}\n}\n</style>\n</head>\n<body>\n<div class="blob blob1"></div>\n<div class="blob blob2"></div>\n<div class="blob blob3"></div>\n\n<nav>\n  <div class="nav-inner">\n    <a href="/" class="logo">\n      <div class="logo-mark">J</div>\n      <span class="logo-text">Job<span>Radar</span></span>\n    </a>\n    <div class="nav-pills">\n      <button class="nav-pill active" onclick="showTab(\'jobs\')">Jobs <span class="nav-count" id="nc">0</span></button>\n      <button class="nav-pill" onclick="showTab(\'hr\')">HR Finder</button>\n      <button class="nav-pill" onclick="showTab(\'links\')">Job Boards</button>\n      <button class="nav-pill" onclick="showTab(\'progress\')">Progress</button>\n    </div>\n    <div class="nav-right">\n      <div class="live-badge"><span class="live-dot"></span>LIVE</div>\n      <a href="/dashboard" class="btn-dash">⚙ Dashboard</a>\n    </div>\n  </div>\n</nav>\n\n<section class="hero">\n  <div class="hero-eyebrow">🎯 AI-Powered · Germany & Remote · Auto-Updated Daily</div>\n  <h1>Your Daily<br/><em>Job Radar</em></h1>\n  <p class="hero-sub">Hand-picked Performance Marketing, SEO & Growth roles — matched to your exact skillset and updated every morning.</p>\n  <div class="stats-row">\n    <div class="stat-item"><div class="stat-num blue" id="s-total">0</div><div class="stat-lbl">Jobs Today</div></div>\n    <div class="stat-item"><div class="stat-num green" id="s-applied">0</div><div class="stat-lbl">Applied</div></div>\n    <div class="stat-item"><div class="stat-num yellow" id="s-saved">0</div><div class="stat-lbl">Saved</div></div>\n    <div class="stat-item"><div class="stat-num purple" id="s-rate">0%</div><div class="stat-lbl">Rate</div></div>\n  </div>\n  <div class="hero-btns">\n    <button class="btn-main btn-primary" onclick="showTab(\'jobs\');document.querySelector(\'.main\').scrollIntoView({behavior:\'smooth\'})">🎯 View Today\'s Jobs</button>\n    <a href="/dashboard" class="btn-main btn-outline">⚙ Admin Dashboard</a>\n  </div>\n</section>\n\n<main class="main">\n  <div class="tab-row">\n    <button class="tab active" id="t-jobs" onclick="showTab(\'jobs\')">🎯 Today\'s Jobs</button>\n    <button class="tab" id="t-hr" onclick="showTab(\'hr\')">👤 HR Finder</button>\n    <button class="tab" id="t-links" onclick="showTab(\'links\')">🔗 Job Boards</button>\n    <button class="tab" id="t-progress" onclick="showTab(\'progress\')">📈 Progress</button>\n  </div>\n\n  <!-- JOBS -->\n  <div id="p-jobs">\n    <div class="sec-hd">\n      <div>\n        <div class="sec-title">Today\'s Matched Jobs</div>\n        <div class="sec-sub" id="last-upd">Fetching latest jobs...</div>\n      </div>\n      <button class="btn-refresh" onclick="loadJobs()">↻ Refresh</button>\n    </div>\n    <div class="toolbar">\n      <div class="search-box"><span class="search-icon">🔍</span>\n        <input type="text" placeholder="Search jobs, companies, skills..." oninput="filterJobs()" id="q"/>\n      </div>\n      <button class="chip" id="f-remote" onclick="toggleF(\'remote\')">🌍 Remote</button>\n      <button class="chip" id="f-de" onclick="toggleF(\'de\')">🇩🇪 Germany</button>\n      <button class="chip" id="f-saved" onclick="toggleF(\'saved\')">🔖 Saved</button>\n      <div class="count-chip" id="jcount">— jobs</div>\n    </div>\n    <div class="jobs-list" id="jobs-list"></div>\n  </div>\n\n  <!-- HR -->\n  <div id="p-hr" style="display:none">\n    <div class="sec-hd">\n      <div><div class="sec-title">Find HR on LinkedIn</div>\n      <div class="sec-sub">Message recruiters after applying — 2× callback rate</div></div>\n    </div>\n    <div class="hr-grid" id="hr-grid"></div>\n    <div class="msg-box">\n      <div class="msg-hd">📝 LinkedIn Connection Message</div>\n      <div class="msg-body">Hi [Name] 👋\n\nI recently applied for the [Job Title] role at [Company].\n\nI bring 6+ years in performance marketing — 120% organic traffic growth, 35% lead gen lift, consistent ROAS across B2B, SaaS & FMCG verticals.\n\nI also build AI-augmented workflows using Python & LangChain that cut manual work by ~40%.\n\nWould love to connect — portfolio: www.saddamadil.in\n\nBest,\nSaddam Adil</div>\n      <button class="btn-copy" onclick="copyMsg()">📋 Copy Message</button>\n    </div>\n  </div>\n\n  <!-- LINKS -->\n  <div id="p-links" style="display:none">\n    <div class="sec-hd"><div>\n      <div class="sec-title">Job Board Links</div>\n      <div class="sec-sub">Pre-searched for your exact role — click to open</div>\n    </div></div>\n    <div class="links-grid" id="links-grid"></div>\n  </div>\n\n  <!-- PROGRESS -->\n  <div id="p-progress" style="display:none">\n    <div class="progress-card">\n      <div class="progress-hd">📊 Application Funnel</div>\n      <div class="prog-grid" id="prog-grid"></div>\n    </div>\n    <div class="sec-title" style="margin-bottom:16px">Application History</div>\n    <div class="jobs-list" id="hist-list"></div>\n  </div>\n</main>\n\n<footer>\n  <div style="max-width:1280px;margin:0 auto">\n    JobRadar · Built for <a href="https://www.saddamadil.in" target="_blank">Saddam Adil</a> · Auto-updates daily at 9:00 AM IST\n  </div>\n</footer>\n<div class="toast" id="toast"></div>\n\n<script>\nconst LINKS=[\n  {n:"LinkedIn Jobs",r:"🌍 Global",u:"https://www.linkedin.com/jobs/performance-marketing-manager-jobs-worldwide"},\n  {n:"StepStone DE",r:"🇩🇪 Germany",u:"https://www.stepstone.de/jobs/Performance-Marketing-Manager/in-Deutschland.html"},\n  {n:"Indeed Germany",r:"🇩🇪 Germany",u:"https://de.indeed.com/jobs?q=digital+marketing+specialist&l=Deutschland"},\n  {n:"XING Jobs",r:"🇩🇪 Germany",u:"https://www.xing.com/jobs/search?keywords=seo+manager&location=berlin"},\n  {n:"Glassdoor",r:"🌍 Global",u:"https://www.glassdoor.com/Job/digital-marketing-manager-jobs-SRCH_KO0,25.htm"},\n  {n:"WeWorkRemotely",r:"🌍 Remote",u:"https://weworkremotely.com/categories/remote-marketing-jobs"},\n  {n:"Otta Europe",r:"🇪🇺 Europe",u:"https://app.otta.com/jobs/marketing"},\n  {n:"YC Jobs",r:"🌍 Startups",u:"https://www.ycombinator.com/jobs/role/marketing"},\n  {n:"Arbeitsagentur",r:"🇩🇪 Germany",u:"https://www.arbeitsagentur.de/jobsuche/suche?was=marketing+manager&wo=Deutschland"},\n  {n:"Remote.co",r:"🌍 Remote",u:"https://remote.co/remote-jobs/marketing/"},\n];\nconst HR_COMPANIES=[\n  {c:"Zalando SE",l:"Berlin, Germany"},{c:"Delivery Hero",l:"Berlin, Germany"},\n  {c:"HelloFresh",l:"Berlin, Germany"},{c:"N26 Bank",l:"Berlin, Germany"},\n  {c:"Axel Springer",l:"Berlin, Germany"},{c:"Wolt",l:"Helsinki/Remote"},\n  {c:"Shopify",l:"Worldwide Remote"},{c:"HubSpot",l:"Dublin/Remote"},\n];\n\nlet allJobs=[], saved={}, applied={}, filters={remote:false,de:false,saved:false};\n\nasync function loadJobs(){\n  try{\n    const r = await fetch(\'/api/jobs\');\n    const d = await r.json();\n    allJobs = d.jobs||[];\n    if(d.last_updated){\n      const dt = new Date(d.last_updated);\n      document.getElementById(\'last-upd\').textContent = \'Last updated: \'+dt.toLocaleString();\n    }\n    document.getElementById(\'nc\').textContent = allJobs.length;\n    document.getElementById(\'s-total\').textContent = allJobs.length;\n    updateStats();\n    renderJobs(allJobs);\n    renderHR();\n  }catch(e){\n    document.getElementById(\'jobs-list\').innerHTML=\'<div class="empty"><div class="empty-icon">⚠️</div><div class="empty-text">Could not load jobs. <a href="/api/search/run" style="color:var(--blue)">Run search</a></div></div>\';\n  }\n}\n\nfunction renderJobs(list){\n  const el = document.getElementById(\'jobs-list\');\n  document.getElementById(\'jcount\').textContent = list.length+\' jobs\';\n  if(!list.length){el.innerHTML=\'<div class="empty"><div class="empty-icon">🔍</div><div class="empty-text">No jobs match your filters</div></div>\';return;}\n  el.innerHTML = list.map((j,i)=>jobCard(j,i)).join(\'\');\n}\n\nfunction jobCard(j,i){\n  const isApplied=!!applied[j.id], isSaved=!!saved[j.id];\n  const delay=(i*.04).toFixed(2);\n  const C=2*Math.PI*24, offset=C*(1-j.match/100);\n  const color=j.match>=90?\'#00e5a0\':j.match>=80?\'#ffd166\':\'#4f7cff\';\n  const typeLabel=j.location?.toLowerCase().includes(\'remote\')?\'Remote\':\'On-site\';\n  return `<div class="job-card ${isApplied?\'applied-card\':j.hot?\'hot-card\':\'\'}" style="animation-delay:${delay}s">\n    <div class="accent-bar"></div>\n    ${isApplied?\'<div class="badge-applied">✓ APPLIED</div>\':j.hot?\'<div class="badge-hot">🔥 HOT</div>\':\'\'}\n    <div class="card-body">\n      <div class="score-ring">\n        <svg width="56" height="56" viewBox="0 0 56 56">\n          <circle class="ring-track" cx="28" cy="28" r="24"/>\n          <circle class="ring-prog" cx="28" cy="28" r="24" stroke="${color}"\n            stroke-dasharray="${C}" stroke-dashoffset="${offset}"/>\n        </svg>\n        <div class="score-val"><div class="score-num">${j.match}</div><div class="score-pct">match</div></div>\n      </div>\n      <div class="card-info">\n        <div class="job-title">${j.title||\'Untitled\'}</div>\n        <div class="job-meta">\n          <span class="meta-company">🏢 ${j.company||\'N/A\'}</span>\n          <span class="meta-loc">📍 ${j.location||\'Unknown\'}</span>\n          ${j.salary&&j.salary!=\'See listing\'?`<span class="meta-salary">💰 ${j.salary}</span>`:\'\'}\n          <span class="meta-date">⏰ ${j.posted||\'Recent\'}</span>\n        </div>\n        <div class="job-tags">\n          <span class="tag type-tag">${typeLabel}</span>\n          <span class="tag">${j.platform||\'Adzuna\'}</span>\n          ${j.description?\'<span class="tag">AI-scored</span>\':\'\'}\n        </div>\n      </div>\n      <div class="card-actions">\n        <a href="${j.url||\'#\'}" target="_blank" class="btn-apply">🚀 Apply Now</a>\n        <a href="${j.hrUrl||\'https://linkedin.com\'}" target="_blank" class="btn-hr">👤 Find HR</a>\n        <div class="btn-row2">\n          <button class="btn-status ${isApplied?\'done\':\'idle\'}" onclick="toggleApplied(\'${j.id}\')">${isApplied?\'✅ Applied\':\'Mark Done\'}</button>\n          <button class="btn-star ${isSaved?\'on\':\'\'}" onclick="toggleSaved(\'${j.id}\')">${isSaved?\'🔖\':\'☆\'}</button>\n        </div>\n      </div>\n    </div>\n  </div>`;\n}\n\nfunction toggleApplied(id){\n  applied[id]=!applied[id];\n  updateStats();filterJobs();\n  showToast(applied[id]?\'✅ Marked as Applied!\':\'↩ Unmarked\');\n}\nfunction toggleSaved(id){\n  saved[id]=!saved[id];\n  filterJobs();showToast(saved[id]?\'🔖 Saved!\':\'Removed from saved\');\n}\nfunction toggleF(f){\n  filters[f]=!filters[f];\n  document.getElementById(\'f-\'+f).classList.toggle(\'on\',filters[f]);\n  filterJobs();\n}\nfunction filterJobs(){\n  const q=document.getElementById(\'q\').value.toLowerCase();\n  let list=allJobs.filter(j=>{\n    if(filters.remote&&!j.location?.toLowerCase().includes(\'remote\'))return false;\n    if(filters.de&&!j.location?.toLowerCase().includes(\'berlin\')&&!j.location?.toLowerCase().includes(\'germany\')&&!j.location?.toLowerCase().includes(\'deutschland\'))return false;\n    if(filters.saved&&!saved[j.id])return false;\n    if(q&&!j.title?.toLowerCase().includes(q)&&!j.company?.toLowerCase().includes(q))return false;\n    return true;\n  });\n  renderJobs(list);\n}\nfunction updateStats(){\n  const a=Object.values(applied).filter(Boolean).length;\n  const s=Object.values(saved).filter(Boolean).length;\n  document.getElementById(\'s-applied\').textContent=a;\n  document.getElementById(\'s-saved\').textContent=s;\n  document.getElementById(\'s-rate\').textContent=allJobs.length?Math.round(a/allJobs.length*100)+\'%\':\'0%\';\n}\nfunction renderHR(){\n  const companies=[...new Set(allJobs.map(j=>({c:j.company,l:j.location}))),...HR_COMPANIES];\n  const seen=new Set(), unique=[];\n  companies.forEach(c=>{if(!seen.has(c.c)){seen.add(c.c);unique.push(c);}});\n  document.getElementById(\'hr-grid\').innerHTML=unique.slice(0,12).map(c=>`\n    <div class="hr-card">\n      <div class="hr-co">${c.c}</div>\n      <div class="hr-loc">📍 ${c.l||\'\'}</div>\n      <a href="https://www.linkedin.com/search/results/people/?keywords=HR+Recruiter+${encodeURIComponent(c.c)}" target="_blank" class="btn-find">👤 Find HR on LinkedIn</a>\n    </div>`).join(\'\');\n}\nfunction renderLinks(){\n  document.getElementById(\'links-grid\').innerHTML=LINKS.map(l=>`\n    <a href="${l.u}" target="_blank" class="link-card">\n      <div><div class="link-name">${l.n}</div><div class="link-region">${l.r}</div></div>\n      <span class="link-arr">→</span>\n    </a>`).join(\'\');\n}\nfunction renderProgress(){\n  const a=Object.values(applied).filter(Boolean).length;\n  const items=[\n    {l:\'Jobs Found\',v:allJobs.length,max:20,c:\'#4f7cff\'},\n    {l:\'Applied\',v:a,max:20,c:\'#00e5a0\'},\n    {l:\'HR Contacted\',v:0,max:20,c:\'#00d4ff\'},\n    {l:\'Interviews\',v:0,max:10,c:\'#ffd166\'},\n  ];\n  const C=2*Math.PI*30;\n  document.getElementById(\'prog-grid\').innerHTML=items.map(it=>{\n    const pct=it.max?it.v/it.max:0;\n    const off=C*(1-pct);\n    return `<div class="prog-item">\n      <div class="prog-ring">\n        <svg width="72" height="72" viewBox="0 0 72 72">\n          <circle fill="none" stroke="rgba(255,255,255,0.06)" stroke-width="5" cx="36" cy="36" r="30"/>\n          <circle fill="none" stroke="${it.c}" stroke-width="5" stroke-linecap="round" cx="36" cy="36" r="30"\n            stroke-dasharray="${C}" stroke-dashoffset="${off}"/>\n        </svg>\n        <div class="prog-center">${it.v}</div>\n      </div>\n      <div class="prog-label">${it.l}</div>\n    </div>`;\n  }).join(\'\');\n  const appJobs=allJobs.filter(j=>applied[j.id]);\n  document.getElementById(\'hist-list\').innerHTML=appJobs.length?appJobs.map((j,i)=>jobCard(j,i)).join(\'\'):\'<div class="empty"><div class="empty-icon">📋</div><div class="empty-text">No applications yet — start applying!</div></div>\';\n}\n\nfunction showTab(t){\n  [\'jobs\',\'hr\',\'links\',\'progress\'].forEach(p=>{\n    document.getElementById(\'p-\'+p).style.display=p===t?\'block\':\'none\';\n    document.getElementById(\'t-\'+p).classList.toggle(\'active\',p===t);\n  });\n  if(t===\'links\')renderLinks();\n  if(t===\'progress\')renderProgress();\n}\nfunction copyMsg(){\n  navigator.clipboard.writeText(document.querySelector(\'.msg-body\').textContent);\n  showToast(\'📋 Message copied!\');\n}\nfunction showToast(msg){\n  const t=document.getElementById(\'toast\');\n  t.textContent=msg;t.classList.add(\'show\');\n  setTimeout(()=>t.classList.remove(\'show\'),2500);\n}\n\nloadJobs();\n</script>\n</body>\n</html>\n'
DASHBOARD_HTML = '<!DOCTYPE html>\n<html lang="en">\n<head>\n<meta charset="UTF-8"/>\n<meta name="viewport" content="width=device-width,initial-scale=1.0"/>\n<title>JobRadar — Admin Dashboard</title>\n<link href="https://fonts.googleapis.com/css2?family=Clash+Display:wght@400;500;600;700&family=Cabinet+Grotesk:wght@300;400;500;700;800&display=swap" rel="stylesheet"/>\n<style>\n*{margin:0;padding:0;box-sizing:border-box}\n:root{\n  --ink:#0a0a0f;--ink2:#12121a;--ink3:#1a1a28;--ink4:#222236;\n  --border:rgba(255,255,255,0.07);--border2:rgba(255,255,255,0.12);\n  --blue:#4f7cff;--blue2:#3b63e8;--cyan:#00d4ff;--green:#00e5a0;\n  --yellow:#ffd166;--red:#ff6b6b;--purple:#9b72ff;\n  --text:#f0f0f8;--muted:#6b7280;--soft:#9ca3af;\n}\nbody{background:var(--ink);color:var(--text);font-family:\'Cabinet Grotesk\',sans-serif;font-size:15px;overflow-x:hidden}\nbody::after{content:\'\';position:fixed;inset:0;pointer-events:none;z-index:999;\n  background-image:url("data:image/svg+xml,%3Csvg viewBox=\'0 0 256 256\' xmlns=\'http://www.w3.org/2000/svg\'%3E%3Cfilter id=\'noise\'%3E%3CfeTurbulence type=\'fractalNoise\' baseFrequency=\'0.9\' numOctaves=\'4\' stitchTiles=\'stitch\'/%3E%3C/filter%3E%3Crect width=\'100%25\' height=\'100%25\' filter=\'url(%23noise)\' opacity=\'0.03\'/%3E%3C/svg%3E");opacity:.4}\n.blob{position:fixed;border-radius:50%;filter:blur(120px);pointer-events:none;z-index:0}\n.blob1{width:500px;height:500px;background:rgba(79,124,255,0.07);top:-150px;right:-150px}\n.blob2{width:400px;height:400px;background:rgba(0,229,160,0.05);bottom:-100px;left:-100px}\n\n/* ═══ LOGIN OVERLAY ═══ */\n#login-overlay{position:fixed;inset:0;z-index:500;\n  background:rgba(5,5,10,0.97);backdrop-filter:blur(20px);\n  display:flex;align-items:center;justify-content:center}\n.login-box{width:100%;max-width:420px;padding:20px}\n.login-logo{display:flex;align-items:center;gap:12px;margin-bottom:48px}\n.login-mark{width:44px;height:44px;background:linear-gradient(135deg,var(--blue),var(--cyan));\n  border-radius:12px;display:flex;align-items:center;justify-content:center;\n  font-family:\'Clash Display\',sans-serif;font-size:22px;font-weight:800;color:#fff;\n  box-shadow:0 0 30px rgba(79,124,255,0.5)}\n.login-brand{font-family:\'Clash Display\',sans-serif;font-size:24px;font-weight:700;color:#fff}\n.login-brand span{color:var(--cyan)}\n.login-hd{font-family:\'Clash Display\',sans-serif;font-size:36px;font-weight:700;\n  color:#fff;margin-bottom:8px;letter-spacing:-.02em}\n.login-sub{color:var(--muted);font-size:15px;margin-bottom:40px;line-height:1.6}\n.login-field{margin-bottom:16px}\n.login-field label{display:block;font-size:12px;font-weight:700;color:var(--soft);\n  text-transform:uppercase;letter-spacing:.08em;margin-bottom:8px}\n.login-field input{width:100%;padding:14px 18px;background:var(--ink2);\n  border:1px solid var(--border2);border-radius:12px;color:var(--text);\n  font-size:15px;font-family:\'Cabinet Grotesk\',sans-serif;outline:none;transition:all .2s}\n.login-field input:focus{border-color:rgba(79,124,255,0.6);box-shadow:0 0 0 3px rgba(79,124,255,0.1)}\n.btn-login{width:100%;padding:15px;border-radius:12px;margin-top:8px;\n  background:linear-gradient(135deg,var(--blue),var(--blue2));color:#fff;\n  font-size:15px;font-weight:800;border:none;cursor:pointer;\n  box-shadow:0 4px 24px rgba(79,124,255,0.4);transition:all .25s;\n  font-family:\'Cabinet Grotesk\',sans-serif;letter-spacing:.01em}\n.btn-login:hover{transform:translateY(-2px);box-shadow:0 8px 32px rgba(79,124,255,0.55)}\n.login-err{margin-top:12px;padding:12px 16px;border-radius:10px;\n  background:rgba(255,107,107,0.1);border:1px solid rgba(255,107,107,0.2);\n  color:var(--red);font-size:13px;font-weight:600;display:none}\n.login-hint{margin-top:20px;text-align:center;font-size:12px;color:var(--muted)}\n.login-hint a{color:var(--blue);text-decoration:none}\n\n/* ═══ NAV ═══ */\nnav{position:sticky;top:0;z-index:100;\n  background:rgba(10,10,15,0.85);backdrop-filter:blur(24px);\n  border-bottom:1px solid var(--border);padding:0 28px}\n.nav-inner{max-width:1440px;margin:0 auto;height:64px;\n  display:flex;align-items:center;justify-content:space-between;gap:16px}\n.logo{display:flex;align-items:center;gap:12px;text-decoration:none}\n.logo-mark{width:36px;height:36px;background:linear-gradient(135deg,var(--blue),var(--cyan));\n  border-radius:10px;display:flex;align-items:center;justify-content:center;\n  font-size:17px;font-weight:800;color:#fff;font-family:\'Clash Display\',sans-serif;\n  box-shadow:0 0 16px rgba(79,124,255,0.35)}\n.logo-text{font-family:\'Clash Display\',sans-serif;font-size:19px;font-weight:700;color:#fff}\n.logo-text span{color:var(--cyan)}\n.nav-badge{padding:5px 12px;border-radius:20px;background:rgba(155,114,255,0.1);\n  border:1px solid rgba(155,114,255,0.2);color:var(--purple);\n  font-size:11px;font-weight:800;letter-spacing:.06em}\n.nav-right{display:flex;align-items:center;gap:10px}\n.nav-user{display:flex;align-items:center;gap:8px;padding:6px 14px;\n  background:var(--ink2);border:1px solid var(--border);border-radius:10px;\n  font-size:13px;font-weight:600;color:var(--soft)}\n.user-dot{width:8px;height:8px;border-radius:50%;background:var(--green);\n  box-shadow:0 0 8px var(--green)}\n.btn-logout{padding:8px 16px;border-radius:9px;background:rgba(255,107,107,0.08);\n  border:1px solid rgba(255,107,107,0.2);color:var(--red);font-size:13px;font-weight:600;\n  cursor:pointer;transition:all .2s;font-family:\'Cabinet Grotesk\',sans-serif}\n.btn-logout:hover{background:rgba(255,107,107,0.15)}\n.btn-front{padding:8px 16px;border-radius:9px;background:var(--ink2);\n  border:1px solid var(--border);color:var(--soft);font-size:13px;font-weight:600;\n  text-decoration:none;transition:all .2s}\n.btn-front:hover{color:#fff;border-color:var(--border2)}\n\n/* ═══ LAYOUT ═══ */\n.layout{display:flex;min-height:calc(100vh - 64px);position:relative;z-index:1}\n\n/* SIDEBAR */\n.sidebar{width:240px;flex-shrink:0;padding:24px 16px;\n  border-right:1px solid var(--border);position:sticky;top:64px;height:calc(100vh - 64px);overflow-y:auto}\n.sb-section{margin-bottom:28px}\n.sb-label{font-size:10px;font-weight:800;color:var(--muted);\n  text-transform:uppercase;letter-spacing:.1em;padding:0 12px;margin-bottom:8px}\n.sb-item{display:flex;align-items:center;gap:10px;padding:10px 12px;\n  border-radius:10px;cursor:pointer;transition:all .18s;\n  font-size:14px;font-weight:600;color:var(--muted);margin-bottom:2px}\n.sb-item:hover{background:var(--ink2);color:var(--text)}\n.sb-item.active{background:rgba(79,124,255,0.12);color:var(--blue)}\n.sb-icon{width:20px;text-align:center;font-size:15px}\n.sb-cnt{margin-left:auto;padding:2px 8px;border-radius:20px;\n  background:rgba(79,124,255,0.15);color:var(--blue);font-size:10px;font-weight:800}\n.sb-divider{height:1px;background:var(--border);margin:8px 12px 16px}\n\n/* CONTENT */\n.content{flex:1;padding:32px 32px;max-width:1200px;overflow:hidden}\n\n/* KPI ROW */\n.kpi-row{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-bottom:28px}\n.kpi{background:var(--ink2);border:1px solid var(--border);border-radius:16px;\n  padding:22px 22px;position:relative;overflow:hidden;transition:all .25s}\n.kpi::before{content:\'\';position:absolute;top:0;left:0;right:0;height:2px}\n.kpi.k-blue::before{background:linear-gradient(90deg,var(--blue),var(--cyan))}\n.kpi.k-green::before{background:linear-gradient(90deg,var(--green),#00c88a)}\n.kpi.k-yellow::before{background:linear-gradient(90deg,var(--yellow),#ffb700)}\n.kpi.k-purple::before{background:linear-gradient(90deg,var(--purple),#7c5ccc)}\n.kpi:hover{transform:translateY(-2px);border-color:var(--border2)}\n.kpi-icon{font-size:22px;margin-bottom:14px}\n.kpi-val{font-family:\'Clash Display\',sans-serif;font-size:38px;font-weight:700;\n  color:#fff;line-height:1;margin-bottom:6px;letter-spacing:-.02em}\n.kpi-lbl{font-size:12px;color:var(--muted);font-weight:600;text-transform:uppercase;letter-spacing:.06em}\n.kpi-trend{position:absolute;top:20px;right:20px;padding:4px 10px;border-radius:20px;\n  font-size:11px;font-weight:800}\n.trend-up{background:rgba(0,229,160,0.1);color:var(--green)}\n.trend-dn{background:rgba(255,107,107,0.1);color:var(--red)}\n\n/* SECTION */\n.sec{background:var(--ink2);border:1px solid var(--border);border-radius:18px;\n  padding:24px;margin-bottom:20px}\n.sec-head{display:flex;align-items:center;justify-content:space-between;margin-bottom:20px;flex-wrap:wrap;gap:10px}\n.sec-title{font-family:\'Clash Display\',sans-serif;font-size:17px;font-weight:600;color:#fff}\n.sec-sub{font-size:12px;color:var(--muted);margin-top:3px}\n.btn-sm{padding:8px 16px;border-radius:9px;border:none;cursor:pointer;\n  font-size:12px;font-weight:700;transition:all .18s;font-family:\'Cabinet Grotesk\',sans-serif}\n.btn-primary{background:linear-gradient(135deg,var(--blue),var(--blue2));color:#fff;\n  box-shadow:0 2px 12px rgba(79,124,255,0.3)}\n.btn-primary:hover{transform:translateY(-1px);box-shadow:0 4px 20px rgba(79,124,255,0.45)}\n.btn-ghost{background:var(--ink3);color:var(--soft);border:1px solid var(--border)}\n.btn-ghost:hover{color:#fff;border-color:var(--border2)}\n.btn-danger{background:rgba(255,107,107,0.1);color:var(--red);border:1px solid rgba(255,107,107,0.2)}\n.btn-danger:hover{background:rgba(255,107,107,0.2)}\n\n/* TABLE */\n.tbl-wrap{overflow-x:auto;border-radius:12px;border:1px solid var(--border)}\ntable{width:100%;border-collapse:collapse;font-size:13px}\nthead tr{background:rgba(255,255,255,0.02)}\nth{padding:12px 16px;text-align:left;font-size:10px;font-weight:800;color:var(--muted);\n  text-transform:uppercase;letter-spacing:.08em;border-bottom:1px solid var(--border);white-space:nowrap}\ntd{padding:14px 16px;border-bottom:1px solid rgba(255,255,255,0.03);vertical-align:middle}\ntr:last-child td{border-bottom:none}\ntr:hover td{background:rgba(255,255,255,0.02)}\n.td-title{font-weight:700;color:#fff;font-size:13px}\n.td-co{color:var(--blue);font-weight:600}\n.td-loc{color:var(--muted);font-size:12px}\n.pill{display:inline-flex;align-items:center;padding:4px 11px;border-radius:20px;font-size:11px;font-weight:700}\n.pill-blue{background:rgba(79,124,255,0.1);color:var(--blue)}\n.pill-green{background:rgba(0,229,160,0.1);color:var(--green)}\n.pill-yellow{background:rgba(255,209,102,0.1);color:var(--yellow)}\n.pill-red{background:rgba(255,107,107,0.1);color:var(--red)}\n.pill-gray{background:rgba(255,255,255,0.06);color:var(--soft)}\n.match-bar{width:60px;height:6px;border-radius:3px;background:rgba(255,255,255,0.06);overflow:hidden}\n.match-fill{height:100%;border-radius:3px;background:linear-gradient(90deg,var(--blue),var(--cyan))}\n\n/* CHART BARS */\n.chart-row{display:grid;grid-template-columns:repeat(7,1fr);gap:8px;height:120px;align-items:end}\n.chart-col{display:flex;flex-direction:column;align-items:center;gap:6px}\n.chart-bar-wrap{flex:1;width:100%;display:flex;align-items:end;justify-content:center}\n.chart-bar{width:28px;border-radius:6px 6px 0 0;background:linear-gradient(180deg,var(--blue),rgba(79,124,255,0.3));min-height:4px;transition:all .8s ease}\n.chart-day{font-size:10px;color:var(--muted);font-weight:600}\n.chart-val{font-size:10px;font-weight:800;color:var(--blue)}\n\n/* LOG */\n.log-list{display:flex;flex-direction:column;gap:8px}\n.log-item{display:flex;align-items:center;gap:14px;padding:12px 16px;\n  background:var(--ink3);border-radius:10px}\n.log-dot{width:8px;height:8px;border-radius:50%;flex-shrink:0}\n.log-dot.ok{background:var(--green);box-shadow:0 0 8px var(--green)}\n.log-dot.warn{background:var(--yellow)}\n.log-dot.err{background:var(--red)}\n.log-msg{flex:1;font-size:13px;color:var(--soft)}\n.log-msg strong{color:var(--text)}\n.log-time{font-size:11px;color:var(--muted);white-space:nowrap}\n\n/* STATUS RING */\n.status-row{display:flex;gap:16px;flex-wrap:wrap}\n.status-item{flex:1;min-width:140px;background:var(--ink3);border-radius:12px;\n  padding:16px;display:flex;align-items:center;gap:14px}\n.s-icon{width:40px;height:40px;border-radius:10px;display:flex;align-items:center;\n  justify-content:center;font-size:18px}\n.s-icon.ok{background:rgba(0,229,160,0.1)}\n.s-icon.warn{background:rgba(255,209,102,0.1)}\n.s-icon.err{background:rgba(255,107,107,0.1)}\n.s-label{font-size:11px;color:var(--muted);font-weight:600;text-transform:uppercase;letter-spacing:.05em}\n.s-val{font-size:15px;font-weight:800;color:#fff;margin-top:2px}\n.s-val.ok{color:var(--green)}\n.s-val.warn{color:var(--yellow)}\n.s-val.err{color:var(--red)}\n\n/* SELECT */\nselect{background:var(--ink3);border:1px solid var(--border);color:var(--text);\n  padding:7px 12px;border-radius:8px;font-size:12px;font-family:\'Cabinet Grotesk\',sans-serif;\n  outline:none;cursor:pointer}\n\n/* TOAST */\n.toast{position:fixed;bottom:28px;right:28px;z-index:1000;\n  background:var(--green);color:#000;padding:13px 22px;border-radius:12px;\n  font-size:13px;font-weight:800;box-shadow:0 8px 32px rgba(0,229,160,0.35);\n  transform:translateY(80px);opacity:0;transition:all .35s;pointer-events:none}\n.toast.show{transform:translateY(0);opacity:1}\n\n/* PAGES */\n.page{display:none}.page.active{display:block}\n\n/* RUNNING ANIMATION */\n@keyframes spin{to{transform:rotate(360deg)}}\n.spin{animation:spin .8s linear infinite;display:inline-block}\n\n@media(max-width:900px){.kpi-row{grid-template-columns:repeat(2,1fr)}}\n@media(max-width:640px){.layout{flex-direction:column}.sidebar{width:100%;height:auto;position:static;padding:12px;border-right:none;border-bottom:1px solid var(--border)}.content{padding:20px 16px}.kpi-row{grid-template-columns:repeat(2,1fr)}}\n</style>\n</head>\n<body>\n<div class="blob blob1"></div>\n<div class="blob blob2"></div>\n\n<!-- ═══ LOGIN OVERLAY ═══ -->\n<div id="login-overlay">\n  <div class="login-box">\n    <div class="login-logo">\n      <div class="login-mark">J</div>\n      <div class="login-brand">Job<span>Radar</span></div>\n    </div>\n    <div class="login-hd">Admin Access</div>\n    <div class="login-sub">This dashboard is private. Enter your credentials to continue.</div>\n    <div class="login-field">\n      <label>Username</label>\n      <input type="text" id="usr" placeholder="Enter username" autocomplete="username"/>\n    </div>\n    <div class="login-field">\n      <label>Password</label>\n      <input type="password" id="pwd" placeholder="Enter password" autocomplete="current-password"\n        onkeydown="if(event.key===\'Enter\')doLogin()"/>\n    </div>\n    <button class="btn-login" onclick="doLogin()">Sign In →</button>\n    <div class="login-err" id="login-err">❌ Incorrect credentials. Please try again.</div>\n    <div class="login-hint">← <a href="/">Back to Job Board</a></div>\n  </div>\n</div>\n\n<!-- ═══ MAIN APP ═══ -->\n<div id="app" style="display:none">\n<nav>\n  <div class="nav-inner">\n    <a href="/" class="logo">\n      <div class="logo-mark">J</div>\n      <span class="logo-text">Job<span>Radar</span></span>\n    </a>\n    <div class="nav-badge">⚙ ADMIN</div>\n    <div class="nav-right">\n      <div class="nav-user"><span class="user-dot"></span> Saddam Adil</div>\n      <a href="/" class="btn-front">← Job Board</a>\n      <button class="btn-logout" onclick="doLogout()">Sign Out</button>\n    </div>\n  </div>\n</nav>\n\n<div class="layout">\n  <aside class="sidebar">\n    <div class="sb-section">\n      <div class="sb-label">Overview</div>\n      <div class="sb-item active" onclick="goPage(\'overview\',this)"><span class="sb-icon">📊</span>Dashboard</div>\n      <div class="sb-item" onclick="goPage(\'jobs\',this)"><span class="sb-icon">💼</span>Jobs <span class="sb-cnt" id="sb-jobs">0</span></div>\n      <div class="sb-item" onclick="goPage(\'search\',this)"><span class="sb-icon">🔍</span>Search</div>\n      <div class="sb-item" onclick="goPage(\'logs\',this)"><span class="sb-icon">📋</span>Activity Log</div>\n    </div>\n    <div class="sb-divider"></div>\n    <div class="sb-section">\n      <div class="sb-label">System</div>\n      <div class="sb-item" onclick="goPage(\'system\',this)"><span class="sb-icon">⚙️</span>System Status</div>\n    </div>\n    <div class="sb-divider"></div>\n    <div class="sb-section">\n      <div class="sb-label">Quick Actions</div>\n      <div class="sb-item" onclick="runSearch()"><span class="sb-icon">🚀</span>Run Search Now</div>\n    </div>\n  </aside>\n\n  <main class="content">\n\n    <!-- OVERVIEW -->\n    <div class="page active" id="pg-overview">\n      <div style="margin-bottom:28px">\n        <div style="font-family:\'Clash Display\',sans-serif;font-size:28px;font-weight:700;color:#fff;letter-spacing:-.02em">Dashboard</div>\n        <div style="color:var(--muted);font-size:14px;margin-top:6px" id="dash-time">Loading...</div>\n      </div>\n      <div class="kpi-row">\n        <div class="kpi k-blue"><div class="kpi-icon">💼</div><div class="kpi-val" id="k-total">0</div><div class="kpi-lbl">Total Jobs</div></div>\n        <div class="kpi k-green"><div class="kpi-icon">✅</div><div class="kpi-val" id="k-applied">0</div><div class="kpi-lbl">Applied</div><div class="kpi-trend trend-up">↑ Active</div></div>\n        <div class="kpi k-yellow"><div class="kpi-icon">🔥</div><div class="kpi-val" id="k-hot">0</div><div class="kpi-lbl">Hot Jobs</div></div>\n        <div class="kpi k-purple"><div class="kpi-icon">🗄️</div><div class="kpi-val" id="k-db">—</div><div class="kpi-lbl">Database</div></div>\n      </div>\n\n      <div class="sec">\n        <div class="sec-head">\n          <div><div class="sec-title">Weekly Activity</div><div class="sec-sub">Jobs found per day</div></div>\n        </div>\n        <div class="chart-row" id="chart"></div>\n      </div>\n\n      <div class="sec">\n        <div class="sec-head">\n          <div><div class="sec-title">Recent Jobs</div><div class="sec-sub">Latest matched positions</div></div>\n          <button class="btn-sm btn-ghost" onclick="goPage(\'jobs\',document.querySelector(\'.sb-item:nth-child(2)\'))">View All</button>\n        </div>\n        <div class="tbl-wrap">\n          <table>\n            <thead><tr><th>Job Title</th><th>Company</th><th>Location</th><th>Match</th><th>Platform</th><th>Status</th></tr></thead>\n            <tbody id="recent-tbl"></tbody>\n          </table>\n        </div>\n      </div>\n    </div>\n\n    <!-- JOBS -->\n    <div class="page" id="pg-jobs">\n      <div style="margin-bottom:24px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px">\n        <div>\n          <div style="font-family:\'Clash Display\',sans-serif;font-size:28px;font-weight:700;color:#fff">All Jobs</div>\n          <div style="color:var(--muted);font-size:14px;margin-top:4px" id="jobs-sub">Loading...</div>\n        </div>\n        <button class="btn-sm btn-primary" onclick="runSearch()">🚀 Run Search Now</button>\n      </div>\n      <div class="sec" style="padding:16px 20px;margin-bottom:16px">\n        <div style="display:flex;gap:10px;flex-wrap:wrap">\n          <input type="text" id="j-search" placeholder="🔍 Filter jobs..." oninput="filterTable()"\n            style="flex:1;min-width:180px;padding:10px 14px;background:var(--ink3);border:1px solid var(--border);border-radius:9px;color:var(--text);font-size:13px;font-family:\'Cabinet Grotesk\',sans-serif;outline:none"/>\n          <select id="j-status" onchange="filterTable()">\n            <option value="">All Status</option>\n            <option>Pending</option><option>Applied</option><option>Interview</option><option>Rejected</option>\n          </select>\n          <select id="j-plat" onchange="filterTable()">\n            <option value="">All Platforms</option>\n            <option>Adzuna DE</option><option>Adzuna GB</option>\n          </select>\n        </div>\n      </div>\n      <div class="sec" style="padding:0">\n        <div class="tbl-wrap" style="border:none;border-radius:18px">\n          <table>\n            <thead><tr><th>Job Title</th><th>Company</th><th>Location</th><th>Match</th><th>Salary</th><th>Date</th><th>Status</th><th>Action</th></tr></thead>\n            <tbody id="all-tbl"></tbody>\n          </table>\n        </div>\n      </div>\n    </div>\n\n    <!-- SEARCH -->\n    <div class="page" id="pg-search">\n      <div style="margin-bottom:24px">\n        <div style="font-family:\'Clash Display\',sans-serif;font-size:28px;font-weight:700;color:#fff">Job Search</div>\n        <div style="color:var(--muted);font-size:14px;margin-top:4px">Manually trigger Adzuna API search</div>\n      </div>\n      <div class="sec">\n        <div class="sec-head">\n          <div><div class="sec-title">Run Search Now</div><div class="sec-sub">Fetches latest jobs from Adzuna DE + GB</div></div>\n          <button class="btn-sm btn-primary" onclick="runSearch()" id="run-btn">🚀 Run Search</button>\n        </div>\n        <div id="search-result" style="padding:20px;background:var(--ink3);border-radius:12px;font-size:14px;color:var(--muted)">\n          Click "Run Search" to fetch latest jobs from Adzuna API.\n        </div>\n      </div>\n      <div class="sec">\n        <div class="sec-head"><div><div class="sec-title">API Health</div></div></div>\n        <div class="status-row" id="health-row">\n          <div style="color:var(--muted);font-size:13px;padding:12px">Loading health status...</div>\n        </div>\n      </div>\n    </div>\n\n    <!-- LOGS -->\n    <div class="page" id="pg-logs">\n      <div style="margin-bottom:24px">\n        <div style="font-family:\'Clash Display\',sans-serif;font-size:28px;font-weight:700;color:#fff">Activity Log</div>\n        <div style="color:var(--muted);font-size:14px;margin-top:4px">Search history and system events</div>\n      </div>\n      <div class="sec">\n        <div class="sec-head"><div class="sec-title">Search History</div></div>\n        <div class="log-list" id="log-list"><div style="color:var(--muted);font-size:13px">Loading logs...</div></div>\n      </div>\n    </div>\n\n    <!-- SYSTEM -->\n    <div class="page" id="pg-system">\n      <div style="margin-bottom:24px">\n        <div style="font-family:\'Clash Display\',sans-serif;font-size:28px;font-weight:700;color:#fff">System Status</div>\n        <div style="color:var(--muted);font-size:14px;margin-top:4px" id="sys-time">—</div>\n      </div>\n      <div class="sec">\n        <div class="sec-head"><div class="sec-title">Components</div></div>\n        <div class="status-row" id="sys-status"></div>\n      </div>\n      <div class="sec">\n        <div class="sec-head"><div class="sec-title">Configuration</div></div>\n        <div id="sys-config" style="font-size:13px;color:var(--soft);line-height:2;padding:4px 0"></div>\n      </div>\n    </div>\n\n  </main>\n</div>\n</div>\n\n<div class="toast" id="toast"></div>\n\n<script>\n// ═══ AUTH ═══\nconst CREDS = {user:\'saddam\', pass:\'jobradar2026\'};\n\nfunction doLogin(){\n  const u=document.getElementById(\'usr\').value.trim();\n  const p=document.getElementById(\'pwd\').value;\n  if(u===CREDS.user && p===CREDS.pass){\n    sessionStorage.setItem(\'jrauth\',\'1\');\n    document.getElementById(\'login-overlay\').style.display=\'none\';\n    document.getElementById(\'app\').style.display=\'block\';\n    initDashboard();\n  } else {\n    document.getElementById(\'login-err\').style.display=\'block\';\n    document.getElementById(\'pwd\').value=\'\';\n    document.getElementById(\'pwd\').focus();\n  }\n}\nfunction doLogout(){\n  sessionStorage.removeItem(\'jrauth\');\n  location.reload();\n}\n\n// Auto-login if already authenticated\nif(sessionStorage.getItem(\'jrauth\')===\'1\'){\n  document.getElementById(\'login-overlay\').style.display=\'none\';\n  document.getElementById(\'app\').style.display=\'block\';\n}\n\n// ═══ PAGES ═══\nfunction goPage(name, el){\n  document.querySelectorAll(\'.page\').forEach(p=>p.classList.remove(\'active\'));\n  document.querySelectorAll(\'.sb-item\').forEach(s=>s.classList.remove(\'active\'));\n  document.getElementById(\'pg-\'+name).classList.add(\'active\');\n  if(el) el.classList.add(\'active\');\n  if(name===\'logs\') loadLogs();\n  if(name===\'system\') loadSystem();\n  if(name===\'search\') loadHealth();\n}\n\n// ═══ DATA ═══\nlet allJobs=[];\n\nasync function initDashboard(){\n  const now = new Date();\n  document.getElementById(\'dash-time\').textContent = \'Last updated: \'+now.toLocaleString()+\' · Auto-refreshes daily at 9:00 AM\';\n  document.getElementById(\'sys-time\').textContent = \'System time: \'+now.toLocaleString();\n  await loadJobs();\n  await loadHealth();\n}\n\nasync function loadJobs(){\n  try{\n    const r=await fetch(\'/api/jobs\');\n    const d=await r.json();\n    allJobs=d.jobs||[];\n    document.getElementById(\'sb-jobs\').textContent=allJobs.length;\n    document.getElementById(\'k-total\').textContent=allJobs.length;\n    document.getElementById(\'k-hot\').textContent=allJobs.filter(j=>j.hot).length;\n    const applied=allJobs.filter(j=>j.status===\'Applied\').length;\n    document.getElementById(\'k-applied\').textContent=applied;\n    document.getElementById(\'jobs-sub\').textContent=allJobs.length+\' jobs in database\';\n    renderRecentTable();\n    renderAllTable(allJobs);\n    renderChart();\n  } catch(e){}\n}\n\nfunction renderRecentTable(){\n  const tbody=document.getElementById(\'recent-tbl\');\n  tbody.innerHTML=allJobs.slice(0,8).map(j=>`<tr>\n    <td><div class="td-title">${j.title?.substring(0,40)||\'—\'}</div></td>\n    <td><span class="td-co">${j.company||\'—\'}</span></td>\n    <td><span class="td-loc">${j.location||\'—\'}</span></td>\n    <td>\n      <div style="display:flex;align-items:center;gap:8px">\n        <div class="match-bar"><div class="match-fill" style="width:${j.match||0}%"></div></div>\n        <span style="font-size:12px;font-weight:700;color:var(--blue)">${j.match||0}%</span>\n      </div>\n    </td>\n    <td><span class="pill pill-blue">${j.platform||\'—\'}</span></td>\n    <td>${statusPill(j.status)}</td>\n  </tr>`).join(\'\');\n}\n\nfunction renderAllTable(list){\n  const tbody=document.getElementById(\'all-tbl\');\n  tbody.innerHTML=list.map(j=>`<tr>\n    <td><div class="td-title">${j.title?.substring(0,40)||\'—\'}</div></td>\n    <td><span class="td-co">${j.company||\'—\'}</span></td>\n    <td><span class="td-loc">${j.location?.substring(0,20)||\'—\'}</span></td>\n    <td><span style="font-weight:800;color:${j.match>=80?\'var(--green)\':\'var(--blue)\'}">${j.match||0}%</span></td>\n    <td style="font-size:12px;color:var(--soft)">${j.salary||\'See listing\'}</td>\n    <td style="font-size:12px;color:var(--muted)">${j.posted||\'—\'}</td>\n    <td>\n      <select onchange="updateStatus(\'${j.id}\',this.value)"\n        style="background:var(--ink3);border:1px solid var(--border);color:var(--text);padding:5px 8px;border-radius:7px;font-size:11px;font-family:\'Cabinet Grotesk\',sans-serif">\n        ${[\'Pending\',\'Applied\',\'Interview\',\'Offer\',\'Rejected\'].map(s=>`<option ${j.status===s?\'selected\':\'\'}>${s}</option>`).join(\'\')}\n      </select>\n    </td>\n    <td><a href="${j.url||\'#\'}" target="_blank" style="color:var(--blue);font-size:12px;font-weight:700;text-decoration:none">Open →</a></td>\n  </tr>`).join(\'\');\n}\n\nfunction filterTable(){\n  const q=document.getElementById(\'j-search\').value.toLowerCase();\n  const st=document.getElementById(\'j-status\').value;\n  const pl=document.getElementById(\'j-plat\').value;\n  const list=allJobs.filter(j=>{\n    if(q&&!j.title?.toLowerCase().includes(q)&&!j.company?.toLowerCase().includes(q))return false;\n    if(st&&j.status!==st)return false;\n    if(pl&&j.platform!==pl)return false;\n    return true;\n  });\n  renderAllTable(list);\n}\n\nfunction statusPill(s){\n  const m={Pending:\'pill-gray\',Applied:\'pill-green\',Interview:\'pill-yellow\',Offer:\'pill-blue\',Rejected:\'pill-red\'};\n  return `<span class="pill ${m[s]||\'pill-gray\'}">${s||\'Pending\'}</span>`;\n}\n\nasync function updateStatus(id,status){\n  try{\n    await fetch(\'/api/jobs/\'+id+\'/status\',{method:\'PUT\',headers:{\'Content-Type\':\'application/json\'},body:JSON.stringify({status})});\n    showToast(\'✅ Status updated\');\n    allJobs=allJobs.map(j=>j.id===id?{...j,status}:j);\n  }catch(e){showToast(\'⚠️ Update failed\');}\n}\n\nfunction renderChart(){\n  const days=[\'Mon\',\'Tue\',\'Wed\',\'Thu\',\'Fri\',\'Sat\',\'Sun\'];\n  const vals=[0,0,0,0,0,0,allJobs.length];\n  const max=Math.max(...vals,1);\n  document.getElementById(\'chart\').innerHTML=days.map((d,i)=>`\n    <div class="chart-col">\n      <div class="chart-val">${vals[i]||\'\'}</div>\n      <div class="chart-bar-wrap">\n        <div class="chart-bar" style="height:${Math.round(vals[i]/max*100)}px"></div>\n      </div>\n      <div class="chart-day">${d}</div>\n    </div>`).join(\'\');\n}\n\nasync function runSearch(){\n  const btn=document.getElementById(\'run-btn\');\n  const res=document.getElementById(\'search-result\');\n  if(btn){btn.textContent=\'⏳ Running...\';btn.disabled=true;}\n  if(res)res.innerHTML=\'<span class="spin">⏳</span> Fetching jobs from Adzuna API...\';\n  showToast(\'🔍 Search started...\');\n  try{\n    const r=await fetch(\'/api/search/run\');\n    const d=await r.json();\n    if(res)res.innerHTML=`<div style="color:var(--green);font-weight:700;font-size:15px;margin-bottom:8px">✅ Search Complete!</div>\n      <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-top:12px">\n        <div style="background:var(--ink2);border-radius:10px;padding:16px;text-align:center">\n          <div style="font-family:\'Clash Display\',sans-serif;font-size:28px;font-weight:700;color:var(--blue)">${d.found}</div>\n          <div style="font-size:11px;color:var(--muted);margin-top:4px;text-transform:uppercase;letter-spacing:.05em">Found</div>\n        </div>\n        <div style="background:var(--ink2);border-radius:10px;padding:16px;text-align:center">\n          <div style="font-family:\'Clash Display\',sans-serif;font-size:28px;font-weight:700;color:var(--green)">${d.added}</div>\n          <div style="font-size:11px;color:var(--muted);margin-top:4px;text-transform:uppercase;letter-spacing:.05em">New Added</div>\n        </div>\n        <div style="background:var(--ink2);border-radius:10px;padding:16px;text-align:center">\n          <div style="font-family:\'Clash Display\',sans-serif;font-size:28px;font-weight:700;color:var(--yellow)">${d.found-d.added}</div>\n          <div style="font-size:11px;color:var(--muted);margin-top:4px;text-transform:uppercase;letter-spacing:.05em">Duplicates</div>\n        </div>\n      </div>`;\n    showToast(`✅ Found ${d.found} jobs, ${d.added} new!`);\n    await loadJobs();\n  }catch(e){\n    if(res)res.innerHTML=\'<span style="color:var(--red)">❌ Search failed. Check API keys.</span>\';\n  }\n  if(btn){btn.textContent=\'🚀 Run Search\';btn.disabled=false;}\n}\n\nasync function loadHealth(){\n  try{\n    const r=await fetch(\'/api/health\');\n    const d=await r.json();\n    document.getElementById(\'k-db\').textContent=d.db_connected?\'PG\':\'JSON\';\n\n    const items=[\n      {icon:\'🗄️\',label:\'Database\',val:d.db_connected?\'PostgreSQL\':\'JSON File\',status:d.db_connected?\'ok\':\'warn\'},\n      {icon:\'🔑\',label:\'Adzuna API\',val:d.adzuna_configured?\'Connected\':\'Not Set\',status:d.adzuna_configured?\'ok\':\'err\'},\n      {icon:\'🌐\',label:\'App Server\',val:\'Running\',status:\'ok\'},\n      {icon:\'📄\',label:\'Frontend\',val:d.index_exists?\'Loaded\':\'Missing\',status:d.index_exists?\'ok\':\'err\'},\n    ];\n    const html=items.map(it=>`<div class="status-item">\n      <div class="s-icon ${it.status}">${it.icon}</div>\n      <div><div class="s-label">${it.label}</div><div class="s-val ${it.status}">${it.val}</div></div>\n    </div>`).join(\'\');\n    const hr=document.getElementById(\'health-row\');\n    const ss=document.getElementById(\'sys-status\');\n    if(hr)hr.innerHTML=html;\n    if(ss)ss.innerHTML=html;\n    const cfg=document.getElementById(\'sys-config\');\n    if(cfg)cfg.innerHTML=`\n      <div>App Status: <strong style="color:var(--green)">Online ✓</strong></div>\n      <div>Storage: <strong style="color:var(--text)">${d.storage}</strong></div>\n      <div>Server Time: <strong style="color:var(--text)">${new Date(d.time||Date.now()).toLocaleString()}</strong></div>\n      <div>Auto-Search: <strong style="color:var(--text)">Daily at 9:00 AM UTC</strong></div>\n    `;\n  }catch(e){}\n}\n\nasync function loadLogs(){\n  try{\n    const r=await fetch(\'/api/logs\');\n    const d=await r.json();\n    const logs=d.logs||[];\n    document.getElementById(\'log-list\').innerHTML=logs.length?logs.map(l=>`\n      <div class="log-item">\n        <div class="log-dot ${l.status===\'Success\'?\'ok\':l.status===\'Error\'?\'err\':\'warn\'}"></div>\n        <div class="log-msg"><strong>${l.run_date||l.date||\'—\'} ${l.run_time||l.time||\'\'}</strong> — ${l.jobs_found||0} jobs found, ${l.new_added||0} new added</div>\n        <div class="log-time">${l.status||\'—\'}</div>\n      </div>`).join(\'\')\n    :\'<div style="color:var(--muted);font-size:13px;padding:12px">No search history yet. Run a search to see logs.</div>\';\n  }catch(e){}\n}\n\nasync function loadSystem(){\n  await loadHealth();\n  document.getElementById(\'sys-time\').textContent=\'System time: \'+new Date().toLocaleString();\n}\n\nfunction showToast(msg){\n  const t=document.getElementById(\'toast\');\n  t.textContent=msg;t.classList.add(\'show\');\n  setTimeout(()=>t.classList.remove(\'show\'),2500);\n}\n\n// Init if already logged in\nif(sessionStorage.getItem(\'jrauth\')===\'1\') initDashboard();\n</script>\n</body>\n</html>\n'

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
