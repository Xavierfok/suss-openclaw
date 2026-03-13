# SUSS OpenClaw Lead Gen & Profiling Tool — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a two-phase lead generation pipeline that collects HR Director/CFO profiles via background checks, then uses Claude Code to analyze communication style and generate personalized Heyva Health outreach messages, outputting to Excel.

**Architecture:** Phase 1 is Python scripts that read manually-collected leads from CSV, run Google + social media background checks, and output structured JSON. Phase 2 uses Claude Code (no API key) to read the JSON, analyze tone, generate outreach, and write analyzed JSON. A final Python script converts analyzed JSON to Excel.

**Tech Stack:** Python 3, requests, beautifulsoup4, google-api-python-client, pandas, openpyxl, playwright (optional)

---

## File Structure

| File | Responsibility |
|------|---------------|
| `config.py` | All configuration: search filters, API keys, paths, rate limits |
| `background_checker.py` | Google Custom Search + social media discovery + scraping |
| `excel_writer.py` | Reads `analyzed_leads.json`, writes formatted Excel |
| `main.py` | Orchestrates Phase 1: reads CSV input → runs background checker → outputs `raw_leads.json` |
| `analyze.md` | Prompt file for Claude Code Phase 2 (tone analysis + outreach generation) |
| `requirements.txt` | Python dependencies |
| `linkedin_scraper.py` | Optional: automated LinkedIn scraping (expect blocks) |

---

## Chunk 1: Project Setup & Config

### Task 1: Initialize project and dependencies

**Files:**
- Create: `config.py`
- Create: `requirements.txt`
- Create: `.gitignore`
- Create: `leads_data/` directory
- Create: `output/` directory

- [ ] **Step 1: Create .gitignore**

```
.env
output/
__pycache__/
*.pyc
leads_data/analyzed_leads.json
```

- [ ] **Step 2: Create requirements.txt**

```
requests>=2.31.0
beautifulsoup4>=4.12.0
google-api-python-client>=2.100.0
pandas>=2.1.0
openpyxl>=3.1.0
playwright>=1.40.0
```

- [ ] **Step 2: Create config.py**

```python
import os

# Search filters
TARGET_TITLES = ["HR Director", "CFO", "Chief Financial Officer", "Head of HR"]
TARGET_INDUSTRIES = ["Oil & Gas", "Technology", "MNC"]
TARGET_CRITERIA = ["insurance", "health reimbursement", "employee benefits"]

# Rate limiting
GOOGLE_DELAY_SECONDS = (2, 5)
SCRAPE_DELAY_SECONDS = (3, 8)

# Google Custom Search API (free tier: 100 queries/day)
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")
GOOGLE_CSE_ID = os.environ.get("GOOGLE_CSE_ID", "")

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LEADS_DATA_DIR = os.path.join(BASE_DIR, "leads_data")
RAW_LEADS_PATH = os.path.join(LEADS_DATA_DIR, "raw_leads.json")
ANALYZED_LEADS_PATH = os.path.join(LEADS_DATA_DIR, "analyzed_leads.json")
MANUAL_LEADS_PATH = os.path.join(LEADS_DATA_DIR, "manual_leads.csv")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
```

- [ ] **Step 3: Create directory structure**

```bash
cd ~/Desktop/suss_openclaw
mkdir -p leads_data output
```

- [ ] **Step 4: Install dependencies**

```bash
cd ~/Desktop/suss_openclaw
pip install -r requirements.txt
```

- [ ] **Step 5: Create sample manual_leads.csv with headers**

```csv
name,title,company,industry,linkedin_url,linkedin_about,linkedin_posts
Jane Smith,HR Director,Shell Asia Pacific,Oil & Gas,https://linkedin.com/in/janesmith,"20+ years in HR leadership focusing on employee wellness","Excited to share our new wellness program|Great turnout at our health screening event"
```

Note: `linkedin_posts` uses `|` as delimiter for multiple posts within the CSV field.

- [ ] **Step 6: Commit**

```bash
git init
git add config.py requirements.txt leads_data/manual_leads.csv
git commit -m "feat: initialize project with config, dependencies, and sample data"
```

---

## Chunk 2: Background Checker

### Task 2: Build Google search module

**Files:**
- Create: `background_checker.py`

- [ ] **Step 1: Write background_checker.py with Google search function**

```python
import json
import random
import time
import logging
from typing import Optional
from googleapiclient.discovery import build
import requests
from bs4 import BeautifulSoup
import config

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def google_search(name: str, company: str) -> list[dict]:
    """Search Google for a person at a company. Returns list of search results."""
    if not config.GOOGLE_API_KEY or not config.GOOGLE_CSE_ID:
        logger.warning("Google API key or CSE ID not set. Skipping Google search.")
        return []

    query = f'"{name}" "{company}"'
    try:
        service = build("customsearch", "v1", developerKey=config.GOOGLE_API_KEY)
        result = service.cse().list(q=query, cx=config.GOOGLE_CSE_ID, num=10).execute()
        items = result.get("items", [])
        return [{"title": item.get("title", ""), "link": item.get("link", ""), "snippet": item.get("snippet", "")} for item in items]
    except Exception as e:
        logger.error(f"Google search failed for {name}: {e}")
        return []


def find_social_profiles(search_results: list[dict]) -> dict:
    """Extract social media profile URLs from Google search results."""
    profiles = {"twitter": None, "facebook": None, "instagram": None}
    for result in search_results:
        link = result.get("link", "").lower()
        if "twitter.com/" in link or "x.com/" in link:
            profiles["twitter"] = result["link"]
        elif "facebook.com/" in link:
            profiles["facebook"] = result["link"]
        elif "instagram.com/" in link:
            profiles["instagram"] = result["link"]
    return profiles


def scrape_public_posts(url: str, max_posts: int = 5) -> list[str]:
    """Attempt to scrape public posts from a social media profile URL.
    Returns list of post text. Returns empty list if blocked or private."""
    try:
        delay = random.uniform(*config.SCRAPE_DELAY_SECONDS)
        time.sleep(delay)
        headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            logger.warning(f"Could not access {url}: HTTP {response.status_code}")
            return []
        soup = BeautifulSoup(response.text, "html.parser")
        # Extract text from paragraphs and article tags as a general approach
        texts = []
        for tag in soup.find_all(["p", "article", "span"], limit=50):
            text = tag.get_text(strip=True)
            if len(text) > 30:
                texts.append(text)
        return texts[:max_posts]
    except Exception as e:
        logger.warning(f"Failed to scrape {url}: {e}")
        return []


def check_lead(name: str, company: str) -> dict:
    """Run full background check for one lead. Returns dict with social profiles, posts, google mentions."""
    logger.info(f"Background checking: {name} at {company}")

    # Google search
    delay = random.uniform(*config.GOOGLE_DELAY_SECONDS)
    time.sleep(delay)
    search_results = google_search(name, company)

    # Extract social profiles
    social_profiles = find_social_profiles(search_results)

    # Scrape public posts from found social profiles
    social_posts = []
    for platform, url in social_profiles.items():
        if url:
            posts = scrape_public_posts(url)
            social_posts.extend(posts)

    # Google mentions (titles + snippets from non-social results)
    social_domains = ["twitter.com", "x.com", "facebook.com", "instagram.com", "linkedin.com"]
    google_mentions = [
        f"{r['title']} - {r['snippet']}"
        for r in search_results
        if not any(domain in r.get("link", "").lower() for domain in social_domains)
    ]

    # Determine data quality
    has_social = any(social_profiles.values())
    data_quality = "full" if has_social and social_posts else ("linkedin_only" if not has_social else "limited")

    return {
        "social_profiles": social_profiles,
        "social_posts": social_posts,
        "google_mentions": google_mentions,
        "data_quality": data_quality,
    }
```

- [ ] **Step 2: Test with a manual dry run**

```bash
cd ~/Desktop/suss_openclaw
python -c "
from background_checker import find_social_profiles
results = [{'title': 'Test', 'link': 'https://twitter.com/testuser', 'snippet': 'test'}]
print(find_social_profiles(results))
"
```

Expected: `{'twitter': 'https://twitter.com/testuser', 'facebook': None, 'instagram': None}`

- [ ] **Step 3: Commit**

```bash
git add background_checker.py
git commit -m "feat: add background checker with Google search and social media discovery"
```

---

## Chunk 3: Main Pipeline Orchestrator

### Task 3: Build main.py to orchestrate Phase 1

**Files:**
- Create: `main.py`

- [ ] **Step 1: Write main.py**

```python
import csv
import json
import logging
import os
from background_checker import check_lead
import config

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def load_manual_leads(csv_path: str) -> list[dict]:
    """Load leads from manual_leads.csv."""
    leads = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            lead = {
                "name": row.get("name", "").strip(),
                "title": row.get("title", "").strip(),
                "company": row.get("company", "").strip(),
                "industry": row.get("industry", "").strip(),
                "linkedin_url": row.get("linkedin_url", "").strip(),
                "linkedin_about": row.get("linkedin_about", "").strip(),
                "linkedin_posts": [p.strip() for p in row.get("linkedin_posts", "").split("|") if p.strip()],
            }
            if lead["name"] and lead["company"]:
                leads.append(lead)
            else:
                logger.warning(f"Skipping lead with missing name or company: {row}")
    return leads


def run_pipeline():
    """Run Phase 1: load leads from CSV, run background checks, output raw_leads.json."""
    # Load leads
    csv_path = config.MANUAL_LEADS_PATH
    if not os.path.exists(csv_path):
        logger.error(f"Manual leads file not found: {csv_path}")
        logger.info("Create leads_data/manual_leads.csv with columns: name,title,company,industry,linkedin_url,linkedin_about,linkedin_posts")
        return

    leads = load_manual_leads(csv_path)
    logger.info(f"Loaded {len(leads)} leads from {csv_path}")

    if not leads:
        logger.error("No valid leads found in CSV.")
        return

    # Run background checks
    enriched_leads = []
    for i, lead in enumerate(leads, 1):
        logger.info(f"Processing lead {i}/{len(leads)}: {lead['name']}")
        try:
            bg_data = check_lead(lead["name"], lead["company"])
            lead.update(bg_data)
            enriched_leads.append(lead)
        except Exception as e:
            logger.error(f"Failed to process {lead['name']}: {e}")
            lead["social_profiles"] = {"twitter": None, "facebook": None, "instagram": None}
            lead["social_posts"] = []
            lead["google_mentions"] = []
            lead["data_quality"] = "limited"
            enriched_leads.append(lead)

    # Save output
    os.makedirs(os.path.dirname(config.RAW_LEADS_PATH), exist_ok=True)
    with open(config.RAW_LEADS_PATH, "w", encoding="utf-8") as f:
        json.dump(enriched_leads, f, indent=2, ensure_ascii=False)

    logger.info(f"Saved {len(enriched_leads)} leads to {config.RAW_LEADS_PATH}")


if __name__ == "__main__":
    run_pipeline()
```

- [ ] **Step 2: Test with sample CSV**

```bash
cd ~/Desktop/suss_openclaw
python main.py
```

Expected: Loads 1 sample lead, runs background check (may fail if no Google API key set — that's OK), saves `leads_data/raw_leads.json`.

- [ ] **Step 3: Verify raw_leads.json was created**

```bash
cat leads_data/raw_leads.json
```

Expected: JSON array with 1 lead object containing all expected fields.

- [ ] **Step 4: Commit**

```bash
git add main.py
git commit -m "feat: add main pipeline orchestrator for Phase 1"
```

---

## Chunk 4: Claude Code Analysis Prompt

### Task 4: Write the analyze.md prompt file for Phase 2

**Files:**
- Create: `analyze.md`

- [ ] **Step 1: Write analyze.md**

````markdown
# Lead Analysis Instructions

Read `leads_data/raw_leads.json` and analyze each lead. Write the results to `leads_data/analyzed_leads.json`.

## Product Context

You are generating outreach for **Heyva Health**, a platform that:
- Analyzes companies' financial risk exposure to lifestyle diseases among their workforce
- Ingests employee medical checkup data (biomarkers) to assess health risks
- Creates personalized health programs for each employee
- Value prop: reduces healthcare costs and insurance claims through data-driven, personalized interventions

## For Each Lead

### 1. Tone Analysis
Look at their LinkedIn posts, social media posts, and Google mentions. Determine:
- **Communication style:** Formal or casual? Data-driven or narrative? Corporate or personal?
- **Vocabulary level:** Technical jargon user? Simple and direct? Buzzword heavy?
- **Key phrases they use:** What words/phrases appear repeatedly in their posts?
- **Topics they care about:** What do they post about? Employee wellness? Company culture? Industry trends?
- **Emotional triggers:** What gets them engaged? Innovation? Cost savings? Employee satisfaction?

### 2. Outreach Messages
Generate messages that **mirror their communication style**. If they're formal, be formal. If they use data, lead with data. If they care about people, lead with employee impact.

**Connection Message** (max 300 chars for LinkedIn):
- Reference something specific from their posts or profile
- Connect it to Heyva Health's value
- Match their tone exactly

**Follow-up Message** (after connection accepted):
- Build on the connection message
- Introduce Heyva Health naturally
- Propose a specific next step (15-min call, demo, etc.)
- Keep it under 500 words

**Talking Points** (for first meeting):
- 3-5 bullet points tailored to their role and interests
- For HR Directors: focus on employee health outcomes, wellness program ROI, retention
- For CFOs: focus on financial risk reduction, insurance cost optimization, data-driven decisions

### 3. Output Format

For each lead, add these fields to their existing data:

```json
{
  "tone_profile": "Detailed description of their communication style...",
  "connection_message": "The personalized LinkedIn connection request...",
  "followup_message": "The follow-up message after connection...",
  "key_interests": ["interest1", "interest2", "interest3"],
  "talking_points": ["point1", "point2", "point3"],
  "notes": "Any additional observations or flags"
}
```

Write the complete array (original fields + new analysis fields) to `leads_data/analyzed_leads.json`.
````

- [ ] **Step 2: Commit**

```bash
git add analyze.md
git commit -m "feat: add Claude Code analysis prompt for Phase 2"
```

---

## Chunk 5: Excel Writer

### Task 5: Build excel_writer.py

**Files:**
- Create: `excel_writer.py`

- [ ] **Step 1: Write excel_writer.py**

```python
import json
import os
from datetime import datetime
import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import Font, Alignment, PatternFill
import config

import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def load_analyzed_leads(path: str) -> list[dict]:
    """Load analyzed leads from JSON."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def format_social_links(profiles: dict) -> str:
    """Format social profile URLs into a readable string."""
    links = []
    for platform, url in profiles.items():
        if url:
            links.append(f"{platform}: {url}")
    return "\n".join(links) if links else "None found"


def leads_to_dataframe(leads: list[dict]) -> pd.DataFrame:
    """Convert analyzed leads to a DataFrame matching the spec columns."""
    rows = []
    for lead in leads:
        row = {
            "Name": lead.get("name", ""),
            "Title": lead.get("title", ""),
            "Company": lead.get("company", ""),
            "Industry": lead.get("industry", ""),
            "LinkedIn URL": lead.get("linkedin_url", ""),
            "Social Media Links": format_social_links(lead.get("social_profiles", {})),
            "Tone Profile Summary": lead.get("tone_profile", "Not analyzed"),
            "Suggested Connection Message": lead.get("connection_message", ""),
            "Suggested Follow-up Message": lead.get("followup_message", ""),
            "Key Interests": ", ".join(lead.get("key_interests", [])),
            "Talking Points": "\n".join(f"- {tp}" for tp in lead.get("talking_points", [])),
            "Data Quality": lead.get("data_quality", "unknown"),
            "Notes": lead.get("notes", ""),
        }
        rows.append(row)
    return pd.DataFrame(rows)


def style_workbook(filepath: str):
    """Apply formatting to the Excel workbook."""
    wb = load_workbook(filepath)
    ws = wb.active

    # Header style
    header_font = Font(bold=True, color="FFFFFF", size=11)
    header_fill = PatternFill(start_color="2D8B2D", end_color="2D8B2D", fill_type="solid")

    for cell in ws[1]:
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", wrap_text=True)

    # Data rows
    for row in ws.iter_rows(min_row=2, max_row=ws.max_row, max_col=ws.max_column):
        for cell in row:
            cell.alignment = Alignment(wrap_text=True, vertical="top")

    # Column widths
    column_widths = {
        "A": 20, "B": 18, "C": 25, "D": 15, "E": 35,
        "F": 30, "G": 40, "H": 45, "I": 45,
        "J": 30, "K": 40, "L": 15, "M": 30,
    }
    for col, width in column_widths.items():
        ws.column_dimensions[col].width = width

    wb.save(filepath)


def write_excel():
    """Main function: load analyzed leads, write formatted Excel."""
    analyzed_path = config.ANALYZED_LEADS_PATH
    if not os.path.exists(analyzed_path):
        logger.error(f"Analyzed leads file not found: {analyzed_path}")
        logger.info("Run Phase 2 (Claude Code analysis) first.")
        return

    leads = load_analyzed_leads(analyzed_path)
    logger.info(f"Loaded {len(leads)} analyzed leads")

    df = leads_to_dataframe(leads)

    # Output file
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = os.path.join(config.OUTPUT_DIR, f"heyva_leads_{timestamp}.xlsx")

    df.to_excel(output_path, index=False, engine="openpyxl")
    style_workbook(output_path)

    logger.info(f"Excel file saved to: {output_path}")
    return output_path


if __name__ == "__main__":
    write_excel()
```

- [ ] **Step 2: Test with a mock analyzed_leads.json**

Create a test file:
```bash
cd ~/Desktop/suss_openclaw
cat > leads_data/analyzed_leads.json << 'EOF'
[
  {
    "name": "Jane Smith",
    "title": "HR Director",
    "company": "Shell Asia Pacific",
    "industry": "Oil & Gas",
    "linkedin_url": "https://linkedin.com/in/janesmith",
    "linkedin_about": "20+ years in HR leadership",
    "social_profiles": {"twitter": "https://twitter.com/janesmith", "facebook": null, "instagram": null},
    "social_posts": ["Great article on employee benefits"],
    "google_mentions": ["Jane Smith appointed HR Director - BusinessTimes"],
    "data_quality": "full",
    "tone_profile": "Formal, data-driven communicator focused on employee wellness outcomes",
    "connection_message": "Hi Jane, your recent post on employee wellness resonated with me.",
    "followup_message": "Thanks for connecting. At Heyva Health, we help companies like Shell quantify lifestyle disease risk.",
    "key_interests": ["employee wellness", "HR tech", "DEI"],
    "talking_points": ["Ask about wellness program ROI", "Discuss biomarker-based risk assessment", "Share case study on insurance cost reduction"],
    "notes": ""
  }
]
EOF
```

- [ ] **Step 3: Run excel_writer.py**

```bash
python excel_writer.py
```

Expected: Creates `output/heyva_leads_<timestamp>.xlsx` with formatted data and green headers.

- [ ] **Step 4: Commit**

```bash
git add excel_writer.py
git commit -m "feat: add Excel writer with formatted output for analyzed leads"
```

---

## Chunk 6: Optional LinkedIn Scraper

### Task 6: Build optional linkedin_scraper.py

**Files:**
- Create: `linkedin_scraper.py`

Note: This is the optional automated path. Expect LinkedIn to block it quickly. The primary approach is manual lead collection via CSV.

- [ ] **Step 1: Write linkedin_scraper.py**

```python
"""
Optional LinkedIn scraper using Playwright.
WARNING: LinkedIn has aggressive bot detection. Expect to be blocked within a few requests.
Primary approach is manual lead collection via leads_data/manual_leads.csv.
"""
import csv
import json
import random
import time
import logging
from playwright.sync_api import sync_playwright
import config

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def scrape_linkedin_profile(page, url: str) -> dict:
    """Scrape a single LinkedIn profile page. Returns dict with about and posts."""
    try:
        delay = random.uniform(*config.SCRAPE_DELAY_SECONDS)
        time.sleep(delay)
        page.goto(url, wait_until="domcontentloaded", timeout=15000)
        time.sleep(2)

        # Check if blocked
        if "authwall" in page.url or "login" in page.url:
            logger.warning(f"LinkedIn login wall hit for {url}")
            return {"linkedin_about": "", "linkedin_posts": []}

        # Try to get about section
        about = ""
        try:
            about_section = page.query_selector("[id='about'] + div")
            if about_section:
                about = about_section.inner_text()
        except Exception:
            pass

        # Try to get recent posts (from activity section)
        posts = []
        try:
            post_elements = page.query_selector_all(".feed-shared-update-v2__description")
            for el in post_elements[:5]:
                text = el.inner_text().strip()
                if text:
                    posts.append(text)
        except Exception:
            pass

        return {"linkedin_about": about, "linkedin_posts": posts}

    except Exception as e:
        logger.error(f"Failed to scrape {url}: {e}")
        return {"linkedin_about": "", "linkedin_posts": []}


def scrape_leads_from_urls(urls: list[str]) -> list[dict]:
    """Scrape LinkedIn profiles from a list of URLs."""
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        )
        page = context.new_page()

        for url in urls:
            logger.info(f"Scraping: {url}")
            data = scrape_linkedin_profile(page, url)
            data["linkedin_url"] = url
            results.append(data)

        browser.close()
    return results


if __name__ == "__main__":
    # Test with a single URL
    import sys
    if len(sys.argv) > 1:
        url = sys.argv[1]
        results = scrape_leads_from_urls([url])
        print(json.dumps(results, indent=2))
    else:
        print("Usage: python linkedin_scraper.py <linkedin_profile_url>")
```

- [ ] **Step 2: Commit**

```bash
git add linkedin_scraper.py
git commit -m "feat: add optional LinkedIn scraper (fallback, expect blocks)"
```

---

## Chunk 7: End-to-End Integration & Test

### Task 7: Test full pipeline end-to-end

- [ ] **Step 1: Set up Google API key (if available)**

Go to console.cloud.google.com:
1. Enable "Custom Search API"
2. Create API key
3. Create a Custom Search Engine at programmablesearchengine.google.com
4. Set environment variables:

```bash
export GOOGLE_API_KEY="your-key-here"
export GOOGLE_CSE_ID="your-cse-id-here"
```

If skipping Google API setup for now, the pipeline will still work — it'll just skip Google search results and produce "limited" data quality leads.

- [ ] **Step 2: Populate manual_leads.csv with 1-2 real leads**

Edit `leads_data/manual_leads.csv` with real LinkedIn profiles you've found manually.

- [ ] **Step 3: Run Phase 1**

```bash
cd ~/Desktop/suss_openclaw
python main.py
```

Expected: `leads_data/raw_leads.json` created with enriched lead data.

- [ ] **Step 4: Run Phase 2 (Claude Code analysis)**

```bash
cd ~/Desktop/suss_openclaw
claude "Read leads_data/raw_leads.json and analyze each lead following the instructions in analyze.md. Write the complete output (original fields + analysis) to leads_data/analyzed_leads.json"
```

Expected: `leads_data/analyzed_leads.json` created with tone profiles + outreach messages.

- [ ] **Step 5: Run Excel writer**

```bash
cd ~/Desktop/suss_openclaw
python excel_writer.py
```

Expected: `output/heyva_leads_<timestamp>.xlsx` created with formatted data.

- [ ] **Step 6: Review the Excel output**

Open the Excel file and verify:
- All columns are populated
- Tone profiles are specific to each lead (not generic)
- Outreach messages mirror the lead's communication style
- Data quality flags are correct

- [ ] **Step 7: Final commit**

```bash
git add config.py requirements.txt .gitignore background_checker.py main.py analyze.md excel_writer.py linkedin_scraper.py leads_data/manual_leads.csv
git commit -m "feat: complete end-to-end pipeline with sample data and test results"
```
