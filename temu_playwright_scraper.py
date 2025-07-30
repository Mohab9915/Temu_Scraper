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
import random
from pathlib import Path

from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync

SEARCH_QUERY = "menshoes"
PAGE_SIZE = 120
URL = "https://www.temu.com/api/poppy/v1/search?scene=search"
HEADERS_FILE = Path(__file__).with_name("headers.json")
PRODUCTS_CSV = Path(__file__).with_name("products.csv")

PROXY = {"server": "YOUR_PROXY_IP:YOUR_PROXY_PORT"}

def run_playwright():
    """Launch browser, wait for user login, intercept headers."""
    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=False,
            slow_mo=50,
            proxy=PROXY
        )
        context = browser.new_context(
            locale="en-US",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
        )
        context.add_cookies([
            {"name": "language", "value": "en", "domain": ".temu.com", "path": "/"},
            {"name": "locale", "value": "en_US", "domain": ".temu.com", "path": "/"},
        ])
        page = context.new_page()
        page.set_default_timeout(120000)

        stealth_sync(page)

        page.goto("https://www.temu.com/", wait_until="networkidle")

        try:
            print("Verifying proxy connection...")
            page.goto("https://api.ipify.org?format=json", wait_until="domcontentloaded")
            ip_data = json.loads(page.inner_text('body'))
            print(f"*** Your public IP is: {ip_data['ip']} ***")
            if PROXY and ip_data['ip'] not in PROXY['server']:
                 print("Warning: The public IP does not match the proxy IP.")
            page.go_back()
        except Exception as e:
            print(f"Could not verify IP address: {e}")

        print("Browser opened. Please log in or solve any CAPTCHA.")
        print("Your session will be saved for future runs.")
        print("Once you are logged in and on the homepage, press Enter to continue...")
        input()

        print("Warming up...")
        time.sleep(random.uniform(2, 5))
        page.mouse.move(random.randint(100, 800), random.randint(100, 600))
        time.sleep(random.uniform(1, 3))
        page.mouse.wheel(0, -300)   
        time.sleep(random.uniform(2, 4))

        response = None
        initial_retries = 0
        max_initial_retries = 4

        while initial_retries < max_initial_retries:
            print("Performing search and waiting for API response...")
            try:
                with page.expect_response("**/api/poppy/v1/search?scene=search", timeout=120000) as response_info:
                    print("Simulating user typing and clicking search...")
                    search_input = page.locator('#searchInput')
                    search_input.click(delay=random.uniform(100, 250))
                    time.sleep(random.uniform(0.5, 1.5))
                    search_input.press('Control+A')
                    time.sleep(random.uniform(0.2, 0.5))
                    search_input.press('Backspace')
                    time.sleep(random.uniform(0.5, 1.5))
                    search_input.type(SEARCH_QUERY, delay=random.uniform(80, 200))
                    search_input.press('Enter')
                    time.sleep(random.uniform(4, 7))
                    search_input.press('Enter')
                response = response_info.value

                print("Search submitted. If there is a CAPTCHA, please solve it now.")
                print("Press Enter to continue after solving...")
                input()

                if response.status == 429:
                    wait_time = (2 ** initial_retries) * 60
                    print(f"429 Error on initial search. Retrying in {wait_time / 60} minutes...")
                    time.sleep(wait_time)
                    initial_retries += 1
                    page.reload()
                    time.sleep(5)
                    continue

                if response.ok:
                    break

            except Exception as e:
                print(f"An error occurred during initial search: {e}")
                break
        
        if not response or not response.ok:
            print(f"Initial search failed after multiple retries. Final status: {response.status if response else 'N/A'}")
            context.close()
            return

        print("Successfully intercepted API response.")
        body = response.body()
        data = json.loads(body)
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

        retries = 0
        max_retries = 4
        see_more_count = 0

        while True:
            try:
                time.sleep(random.uniform(8, 15))
                page.mouse.move(random.randint(100, 800), random.randint(100, 600))
                time.sleep(random.uniform(1, 3))
                scroll_amount = random.randint(500, 900)
                page.mouse.wheel(0, scroll_amount)
                time.sleep(random.uniform(3, 6))

                see_more_button = page.locator('div[class*="_2ugbvrpI"]:has-text("See more")')
                see_more_button.scroll_into_view_if_needed()
                
                with page.expect_response("**/api/poppy/v1/search?scene=search", timeout=120000) as response_info:
                    see_more_button.click(delay=random.uniform(100, 300))
                
                response = response_info.value

                if response.status == 429:
                    if retries < max_retries:
                        wait_time = (2 ** retries) * 60
                        print(f"429 Error: Too many requests. Retrying in {wait_time / 60} minutes...")
                        time.sleep(wait_time)
                        retries += 1
                        continue
                    else:
                        print("Max retries reached. Exiting.")
                        break
                
                retries = 0

                if not response.ok:
                    print(f"API request failed with status {response.status}")
                    break

                body = response.body()
                data = json.loads(body)
                new_products = list(extract_products(data))

                if not new_products:
                    print("No more products found.")
                    break

                with PRODUCTS_CSV.open("a", newline="", encoding="utf-8") as csvfile:
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writerows(new_products)
                
                products.extend(new_products)
                see_more_count += 1
                print(f"*** Successfully saved {len(new_products)} more products. Total: {len(products)} ***")

                if see_more_count % 2 == 0:
                    wait_duration = random.uniform(120, 240)
                    print(f"Pausing for {wait_duration / 60:.2f} minutes...")
                    time.sleep(wait_duration)

            except Exception as e:
                print(f"An error occurred: {e}")
                break
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
