# SUSS OpenClaw — Lead Gen & Profiling Tool

## Overview
A lead generation and profiling tool for a SUSS school project deployed on OpenClaw. Finds HR Directors and CFOs at target companies, builds detailed profiles via background checks, analyzes their communication style, and generates personalized outreach messages designed to maximize engagement and reply rates.

Built for one-time use now, but structured cleanly for future reuse.

## Product Context: Heyva Health
The outreach is selling **Heyva Health** — a platform that:
- **Financial risk exposure analysis** — analyzes companies' financial risk related to lifestyle diseases among their workforce
- **Biomarker-based insights** — ingests employee medical checkup data (biomarkers) to assess health risks
- **Personalized health programs** — creates individualized health programs for each employee based on their biomarker data
- **Value proposition:** Helps companies reduce healthcare costs and insurance claims by proactively managing employee lifestyle disease risks through data-driven, personalized interventions

All outreach messages should be framed around this product's value — particularly how it helps HR Directors manage employee health costs and helps CFOs understand/reduce the financial exposure from lifestyle diseases.

## Target Leads
- **Titles:** HR Director, CFO
- **Industries:** Oil & gas, MNCs, tech companies
- **Criteria:** Companies that invest in insurance / health reimbursement packages
- **Volume:** 10-30 leads (small batch, high quality)

## Architecture

### Two-Phase Pipeline

```
Phase 1 (Python):
[Lead Input] → [Google/Social Background Checker] → raw_leads.json

Phase 2 (Claude Code):
raw_leads.json → [Tone Analysis] → [Outreach Generation] → analyzed_leads.json → Excel Output
```

### Phase 1 — Data Collection (Python)

#### Lead Input (Primary: Manual Collection)
LinkedIn has aggressive bot detection that blocks automated scraping within a few requests. The primary approach is manual lead collection:

1. **Manual LinkedIn search** — User searches LinkedIn for HR Directors/CFOs in target industries
2. **Export or copy** lead details into `leads_data/manual_leads.csv` (name, title, company, LinkedIn URL)
3. Alternatively, export from **LinkedIn Sales Navigator** if available

The `linkedin_scraper.py` module exists as an optional automated path, but expect it to be blocked quickly. It uses Playwright with random delays (3-8 seconds) but LinkedIn's fingerprinting will likely detect it.

#### Background Checker (`background_checker.py`)
For each lead from the input:
- Google search: `"{name}" "{company}"` using Google Custom Search API (free tier: 100 queries/day, sufficient for 10-30 leads)
- Discover social media profiles from search results (Twitter/X, Facebook, Instagram)
- Scrape public posts from discovered profiles where accessible
- If no social media found: mark as "No public social media", proceed with LinkedIn data only
- If profile is private: note as "Private profile", skip scraping

**Output:** `leads_data/raw_leads.json`

#### raw_leads.json Schema
```json
[
  {
    "name": "Jane Smith",
    "title": "HR Director",
    "company": "Shell Asia Pacific",
    "industry": "Oil & Gas",
    "linkedin_url": "https://linkedin.com/in/janesmith",
    "linkedin_about": "20+ years in HR leadership...",
    "linkedin_posts": ["Excited to share our new wellness program...", "..."],
    "social_profiles": {
      "twitter": "https://twitter.com/janesmith",
      "facebook": null,
      "instagram": null
    },
    "social_posts": ["Great article on employee benefits...", "..."],
    "google_mentions": ["Jane Smith appointed HR Director at Shell - BusinessTimes", "..."],
    "data_quality": "full"
  }
]
```

`data_quality` values: `"full"` (LinkedIn + social), `"linkedin_only"` (no social found), `"limited"` (minimal data)

### Phase 2 — Analysis & Outreach (Claude Code)

Claude Code performs analysis using the existing subscription (no API key needed).

**How it works:**
1. User runs: `claude "Read leads_data/raw_leads.json and analyze each lead following analyze.md instructions. Write output to leads_data/analyzed_leads.json"`
2. Claude Code reads the raw JSON + the `analyze.md` prompt file
3. Claude Code writes `leads_data/analyzed_leads.json` with tone analysis + outreach messages per lead
4. User runs: `python excel_writer.py` to convert analyzed JSON → final Excel file

**Tone Analysis per lead:**
- Formal vs casual communication style
- Vocabulary level and key phrases they use
- Topics they engage with and care about
- Emotional triggers and interests

**Outreach Generation per lead:**
- Personalized LinkedIn connection request message (mirrors their tone)
- Personalized follow-up message for after connection accepted
- Key talking points for first meeting

**analyzed_leads.json adds these fields per lead:**
```json
{
  "tone_profile": "Formal, data-driven communicator. Uses industry jargon...",
  "connection_message": "Hi Jane, I noticed your recent post on...",
  "followup_message": "Thanks for connecting, Jane. I'd love to...",
  "key_interests": ["employee wellness", "HR tech", "DEI initiatives"],
  "talking_points": ["Ask about their wellness program rollout", "..."],
  "notes": ""
}
```

## Tech Stack
- `playwright` — browser automation (optional LinkedIn scraping)
- Google Custom Search API — background checks (free tier: 100/day)
- `requests` + `beautifulsoup4` — social media scraping
- `pandas` — data handling
- `openpyxl` — Excel output
- Claude Code — tone analysis and outreach generation (no API key)

## Configuration (`config.py`)
```python
# Search filters
TARGET_TITLES = ["HR Director", "CFO", "Chief Financial Officer", "Head of HR"]
TARGET_INDUSTRIES = ["Oil & Gas", "Technology", "MNC"]
TARGET_CRITERIA = ["insurance", "health reimbursement", "employee benefits"]

# Rate limiting
GOOGLE_DELAY_SECONDS = (2, 5)  # random delay range between searches
SCRAPE_DELAY_SECONDS = (3, 8)  # random delay range between page loads

# Google Custom Search API (free tier)
GOOGLE_API_KEY = ""  # from console.cloud.google.com
GOOGLE_CSE_ID = ""   # custom search engine ID

# Paths
RAW_LEADS_PATH = "leads_data/raw_leads.json"
ANALYZED_LEADS_PATH = "leads_data/analyzed_leads.json"
MANUAL_LEADS_PATH = "leads_data/manual_leads.csv"
OUTPUT_DIR = "output/"
```

## File Structure
```
suss_openclaw/
├── config.py              # search filters, API keys, settings
├── linkedin_scraper.py    # optional: automated LinkedIn scraping
├── background_checker.py  # Google + social media background checks
├── excel_writer.py        # converts analyzed JSON → Excel
├── main.py                # orchestrates full pipeline
├── analyze.md             # prompt instructions for Claude Code Phase 2
├── requirements.txt       # Python dependencies
├── leads_data/            # data directory
│   ├── manual_leads.csv   # primary: manually collected leads
│   ├── raw_leads.json     # Phase 1 output
│   └── analyzed_leads.json # Phase 2 output
└── output/                # final Excel files
```

## Excel Output Columns
| Column | Description |
|--------|-------------|
| Name | Full name |
| Title | Job title |
| Company | Company name |
| Industry | Industry sector |
| LinkedIn URL | Profile link |
| Social Media Links | Twitter/X, Facebook, Instagram URLs |
| Tone Profile Summary | Formal/casual, vocabulary, key phrases |
| Suggested Connection Message | Personalized LinkedIn connection request |
| Suggested Follow-up Message | Message after connection accepted |
| Key Interests | Topics they engage with |
| Talking Points | Suggestions for first meeting |
| Data Quality | Full / Limited / LinkedIn Only |
| Notes | Any flags or observations |

## Error Handling
- **LinkedIn scraping blocked:** Expected — use manual lead input as primary approach
- **Google rate limited:** Delay between searches, fall back to manual Google search if needed
- **No social media found:** Proceed with LinkedIn data only, flag in Excel
- **Private social profiles:** Note as private, skip scraping
- **Very little data:** Generate professional generic outreach, flag as "limited data"
- **Any failure:** Log and skip to next lead, don't halt pipeline

## Workflow (Step by Step)
1. Manually search LinkedIn, save leads to `leads_data/manual_leads.csv`
2. Run `python main.py` → runs background checker, outputs `raw_leads.json`
3. Run `claude "Read leads_data/raw_leads.json and analyze each lead following analyze.md. Write output to leads_data/analyzed_leads.json"`
4. Run `python excel_writer.py` → outputs final Excel to `output/`

## Testing & Validation
- Test full pipeline on 1 lead first
- Spot check 3-5 leads against actual profiles for accuracy
- Review generated outreach messages for tone match quality

## Future Considerations
- Dashboard visualization of leads
- LinkedIn automated outreach integration
- Scaling to larger batches (50-100+)
- Scheduled/recurring runs
- OpenClaw deployment configuration
