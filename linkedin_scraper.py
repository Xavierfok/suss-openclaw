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
