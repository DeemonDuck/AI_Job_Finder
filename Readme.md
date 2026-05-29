# 🤖 AI Job Assist
### An intelligent job discovery pipeline — built because job hunting is broken.

---

## The Problem I Was Trying to Solve

Anyone who has looked for a job or internship knows the drill: open five tabs, search the same keywords across Internshala, LinkedIn, Naukri, scroll endlessly, copy-paste details into a spreadsheet, and somehow still miss good listings because they expired two weeks ago.

I wanted to fix that — not just for myself, but as a proper engineering challenge.

**AI Job Assist** is my attempt at automating the messy, repetitive parts of job discovery so that a job seeker only has to focus on what actually matters — applying and preparing.

---

## What This Project Actually Does

At its core, the system does three things:

1. **Finds jobs automatically** — It navigates job platforms like Internshala the way a human would: opening the site, selecting categories, handling popups, scrolling through pages — all without hardcoded, brittle URLs.

2. **Cleans and stores them properly** — Every listing gets normalized (title, company, skills, salary, freshness, source) and stored in a structured SQLite database. No duplicates. No stale data.

3. **Prepares for smart matching** — The pipeline is intentionally designed so an AI recommendation layer can sit on top — ranking jobs by relevance to a candidate's skills and preferences.

The project is currently at Phase 1 — the data pipeline is solid and running. Phases 2–5 bring multi-source support, cross-platform deduplication, and eventually an AI agent that can shortlist and apply on your behalf.

---

## How It Works (The Technical Story)

```
Your Preferences  →  Collector  →  Normalizer  →  SQLite DB  →  (Future) AI Matching Agent
```

### 🔍 Dynamic Job Discovery
Instead of hardcoding URLs like `/ai-machine-learning-internship/`, the collector uses **Playwright** to navigate the site the way a real user does:

- Opens the internship search page
- Dismisses signup popups automatically
- Types the category name into the search field
- Submits, captures the generated URL, and begins extraction

This makes the system resilient to site structure changes — a common failure point in scrapers.

### 📅 Freshness Filtering
Jobs are filtered by how recently they were posted. The system understands natural language timestamps like `"Just Now"`, `"Few Hours Ago"`, `"1 Day Ago"`, `"3 Weeks Ago"` — and converts them into day-based values for threshold filtering.

### 🧠 Category-Aware Storage
Every job is tagged with the search category that discovered it (e.g., *Machine Learning*, *NLP*, *Data Science*). This isn't just metadata — it's the foundation for future analytics and personalized recommendations.

### 🚫 Duplicate Prevention
URLs are used as unique identifiers to prevent the same listing from being stored twice across multiple runs.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Automation | Playwright (Python) |
| API Layer | FastAPI |
| ORM | SQLAlchemy |
| Database | SQLite |
| Validation | Pydantic |
| Language | Python 3.11 |

---

## Database Schema (Simplified)

**Jobs Table** — Stores title, company, location, salary, skills, description, URL, source platform, posting date, freshness, search category, status, and timestamps.

**User Preferences Table** — Stores preferred skills, freshness thresholds, and filtering rules.

**Category Table** — Stores the full Internshala category taxonomy (131 unique categories extracted automatically).

---

## Current Status & Roadmap

### ✅ Done
- Playwright-based dynamic navigation (no hardcoded URLs)
- Automatic popup dismissal
- Pagination discovery
- Freshness filtering with natural language parsing
- Duplicate detection
- Full database persistence
- 131 Internshala categories extracted and stored

### 🔄 In Progress / Planned

| Phase | Goal |
|---|---|
| Phase 1 | Multi-category collection (ML, AI, Data Science, NLP) |
| Phase 2 | Multi-source support — Naukri, LinkedIn, Wellfound |
| Phase 3 | Cross-platform deduplication using job fingerprints (`title + company + location`) |
| Phase 4 | AI-powered matching and relevance ranking engine |
| Phase 5 | Agent-based automation — shortlisting and application workflows |

---

## Why I Built It This Way

A simpler version of this project would just be a Python script that hits an API and dumps JSON. I deliberately went further because:

- **Playwright over static requests** — Real job sites are JavaScript-heavy and block naive scrapers. Browser automation is the honest, maintainable approach.
- **Structured DB over flat files** — CSV files fall apart at scale. A proper schema with categories, timestamps, and status fields makes the data actually useful downstream.
- **Modular pipeline design** — The collector, normalizer, and database layers are intentionally separate so each phase of the roadmap can be added without breaking what already works.
- **Category metadata** — Storing *how* a job was discovered (which search category) enables future personalization and analytics that you simply can't do if you treat all jobs the same.

---

## What I Learned Building This

- Browser automation is powerful but needs careful handling — viewport size, popup timing, and selector stability all affect reliability in ways that aren't obvious until something breaks in production.
- Data freshness is underrated. A job database without staleness management becomes useless quickly.
- Designing for extensibility from Phase 1 saves enormous refactoring pain later. The schema changes I avoided by thinking ahead were significant.

---

## Setup

```bash
git clone https://github.com/your-username/ai-job-assist
cd ai-job-assist
pip install -r requirements.txt
playwright install chromium
python main.py
```

> Requires Python 3.11+

---

## Project Status

🚧 **Active Development** — Core pipeline complete. Multi-source collection and AI matching layer coming next.

---

*Built by a CSE (AI-ML) student who got tired of manually searching for internships and decided to engineer a better way.*
