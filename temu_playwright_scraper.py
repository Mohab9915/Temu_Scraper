"""
Playwright-based Temu scraper that:
1. Opens browser and waits for user login / CAPTCHA solving.
2. Intercepts the search API request to capture fresh headers/cookies.
3. Replays the request with `requests` to fetch products.
4. Saves products to CSV (re-using parse_response_to_csv.py logic).

Install dependencies:
pip install playwright requests
playwright install chromium
"""

import json
import time
import csv
from pathlib import Path


from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync

SEARCH_QUERY = "menshoes"
PAGE_SIZE = 120
URL = "https://www.temu.com/api/poppy/v1/search?scene=search"
HEADERS_FILE = Path(__file__).with_name("headers.json")
PRODUCTS_CSV = Path(__file__).with_name("products.csv")





def run_playwright():
    """Launch browser, wait for user login, intercept headers."""
    with sync_playwright() as p:
        user_data_dir = Path(__file__).parent / "user_data"
        context = p.chromium.launch_persistent_context(
            user_data_dir,
            headless=False,
            slow_mo=50,
            locale="en-US",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"
        )
        context.add_cookies([
            {"name": "language", "value": "en", "domain": ".temu.com", "path": "/"},
            {"name": "locale", "value": "en_US", "domain": ".temu.com", "path": "/"},
        ])
        page = context.new_page()

        stealth_sync(page)

        page.goto("https://www.temu.com/", wait_until="networkidle")

        print("Browser opened. Please log in or solve any CAPTCHA.")
        print("Your session will be saved for future runs.")
        print("Once you are logged in and on the homepage, press Enter to continue...")
        input()

        print("Performing search and waiting for API response...")
        with page.expect_response("**/api/poppy/v1/search?scene=search", timeout=60000) as response_info:
            print("Simulating user typing and clicking search...")
            page.locator('#searchInput').type(SEARCH_QUERY, delay=100)
            page.locator('#searchInput').press('Enter')
            time.sleep(5)
            page.locator('#searchInput').press('Enter')
        response = response_info.value

        if not response.ok:
            print(f"API request failed with status {response.status}")
            return

        print("Successfully intercepted API response.")
        data = response.json()
        products = list(extract_products(data))

        if not products:
            print("API response did not contain any products.")
            return

        fieldnames = list(products[0].keys())
        with PRODUCTS_CSV.open("w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(products)
        
        print(f"\n*** Successfully saved {len(products)} products to {PRODUCTS_CSV.name} ***")
        context.close()





def extract_products(data: dict):
    """Yield dicts of product info from loaded JSON data."""
    try:
        goods_list = data["result"]["data"]["goods_list"]
    except (KeyError, TypeError):
        raise ValueError("Unexpected JSON structure: cannot find goods_list")

    for item in goods_list:
        price_info = item.get("price_info", {})
        yield {
            "goods_id": item.get("goods_id", ""),
            "title": item.get("title", ""),
            "price_str": price_info.get("price_str", ""),
            "price": price_info.get("price", ""),
            "currency": price_info.get("currency", ""),
            "sales_num": item.get("sales_num", ""),
            "thumb_url": item.get("thumb_url", ""),
            "link_url": item.get("link_url", ""),
        }


def main():
    print("=== Temu Playwright Scraper ===")
    run_playwright()
    print("Script finished. Check products.csv for results.")


if __name__ == "__main__":
    main()
