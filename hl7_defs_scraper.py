# hl7_defs_scraper_the_one_with_a_goddamn_brain.py
#
# This version is now a real tool. It checks for existing files to avoid
# re-scraping and includes a --replace flag to force an overwrite.
# Your AI buddy has finally delivered.

import time
from playwright.sync_api import sync_playwright, Page, TimeoutError # type: ignore
import json
import re
import os
import argparse # The new hotness

BASE = "https://hl7-definition.caristix.com"
OUTPUT_DIR = "segment-dictionary"

# ────────────────────────────────────────────────────────────────
#  (All the scraping functions are perfect now, so we don't touch them)
# ────────────────────────────────────────────────────────────────

def get_attribute_by_label(page: Page, label: str) -> str:
    """Finds a label (e.g., 'Length') and returns the associated value next to it."""
    try:
        return page.locator(
            f"div.attribute-container:has(span.cx-caption:text-is('{label}')) span.attribute-value"
        ).inner_text(timeout=10_000).strip()
    except Exception:
        return "N/A"

def get_all_segment_names(page: Page, segments_page_url: str) -> list[str]:
    """
    Handles virtual scrolling by checking if the number of *unique items* has
    stopped increasing, which is robust against DOM-recycling scrollers.
    """
    print(f"Dynamically scraping segment list from: {segments_page_url}")
    page.goto(segments_page_url, timeout=90_000)

    list_item_locator = "mat-nav-list a.mat-list-item"
    try:
        print("Waiting for initial segment list content to load...")
        page.locator(f"{list_item_locator} h3").first.wait_for(timeout=30_000)
        print("Initial content loaded. Beginning scroll loop...")
    except Exception as e:
        screenshot_path = "debug_screenshot_SCROLL_FAIL.png"
        page.screenshot(path=screenshot_path)
        print(f"‼️ FAILED to find initial list content. Error: {e} ‼️")
        print(f"‼️ Screenshot saved to {screenshot_path} ‼️")
        return []

    all_segment_names = set()
    
    while True:
        count_before_iteration = len(all_segment_names)
        h3_locators = page.locator(f"{list_item_locator} h3")
        
        for i in range(h3_locators.count()):
            try:
                h3_text = h3_locators.nth(i).inner_text(timeout=2000)
                segment_id = h3_text.split('-')[0].strip()
                if segment_id:
                    all_segment_names.add(segment_id)
            except Exception:
                continue

        print(f"Found {len(all_segment_names)} unique segments so far...")
        count_after_iteration = len(all_segment_names)

        if count_after_iteration == count_before_iteration:
            print("Scroll complete. No new unique segments found.")
            break

        page.locator(list_item_locator).last.scroll_into_view_if_needed()
        time.sleep(1)

    final_list = sorted(list(all_segment_names))
    print("\n------------------------------")
    print("--- Final Extracted Segment List ---")
    print(f"--- Found {len(final_list)} total unique segments ---")
    print("------------------------------\n")
    
    return final_list


def scrape_segment(page: Page, segment: str, version: str) -> tuple[str, str, dict]:
    """
    Scrapes a segment's data, gracefully handling missing long descriptions.
    """
    print(f"-- Scraping segment: {segment} for version {version} --")
    
    url_version_component = f"HL7{version}"
    version_path = f"/v2/{url_version_component}"
    segment_url = f"{BASE}{version_path}/Segments/{segment}"
    
    try:
        page.goto(segment_url, timeout=90_000)
        page.locator("app-segment-detail").wait_for(timeout=30_000)
        header_text = page.locator("h2.content-header-title-centered").inner_text(timeout=15_000)
        short_description = header_text.split(' - ')[-1].strip()

        long_description = "No description found."
        try:
            long_description = page.locator("div.detail-text-container p").first.inner_text(timeout=5000).strip()
        except Exception:
            print(f"  - Note: No long description found for segment {segment}. This is fine.")

    except Exception as e:
        screenshot_path = f"debug_screenshot_{segment}_{version}.png"
        page.screenshot(path=screenshot_path)
        print(f"  ‼️ CRITICAL FAILURE on segment page for {segment} ({version}). URL was {segment_url}")
        print(f"  ‼️ Error: {e}")
        print(f"  ‼️ A screenshot has been saved to '{screenshot_path}' for debugging.")
        return "ERROR", "ERROR: Could not load segment page.", {}

    field_link_locator = f"a[href*='{version_path}/Fields/{segment}.']"
    field_links = page.locator(field_link_locator).all()
    field_urls = [BASE + href for link in field_links if (href := link.get_attribute('href')) is not None]
    unique_field_urls = sorted(list(set(field_urls)))
    
    print(f"  ↳ Found {len(unique_field_urls)} fields for {segment}. Now scraping details...")

    fields_dict = {}
    for url in unique_field_urls:
        try:
            page.goto(url, timeout=90_000, wait_until="domcontentloaded")
            page.locator("app-field-detail h2").wait_for(timeout=30_000)
            
            header_text = page.locator("app-field-detail h2").inner_text()
            match = re.search(r"-\s*([A-Z0-9\.]+\.\d+)\s*-\s*(.*)", header_text)
            if not match: continue
            
            field_id_full, field_name = match.groups()
            field_idx = field_id_full.split('.')[-1]
            
            desc_element = page.locator("div.detail-text-container p").first
            description = desc_element.inner_text().strip() if desc_element.is_visible() else "No description found."
            
            fields_dict[field_idx] = {
                "field_id": field_id_full,
                "name": field_name.strip(),
                "description": description,
                "length": get_attribute_by_label(page, "Length"),
                "data_type": get_attribute_by_label(page, "Data Type"),
                "optionality": get_attribute_by_label(page, "Optionality"),
                "repeatability": get_attribute_by_label(page, "Repeatability"),
            }
        except Exception as e:
            print(f"    !! Failed to scrape details for {url}. Error: {e}")
            continue

    return short_description, long_description, fields_dict

# ────────────────────────────────────────────────────────────────

def main():
    # <<< THE NEW SHIT: Argument parsing for command-line flags >>>
    parser = argparse.ArgumentParser(
        description="Scrape HL7 segment definitions from Caristix.",
        formatter_class=argparse.RawTextHelpFormatter # Makes help text look nice
    )
    parser.add_argument(
        '--replace',
        action='store_true', # Sets args.replace to True if flag is present
        help="Overwrite existing JSON files. If not set, existing files will be skipped."
    )
    args = parser.parse_args()


    versions_to_scrape = ["v2.1", "v2.2"]
    print(f"Starting HL7 Scraper for versions: {', '.join(versions_to_scrape)}")
    if args.replace:
        print("!! --replace flag is set. ALL EXISTING FILES WILL BE OVERWRITTEN. !!")
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        
        try:
            for version in versions_to_scrape:
                print(f"\n{'='*25} PROCESSING VERSION: {version} {'='*25}")
                
                version_dir = os.path.join(OUTPUT_DIR, version)
                os.makedirs(version_dir, exist_ok=True)
                
                url_version_component = f"HL7{version}"
                segments_page_url = f"{BASE}/v2/{url_version_component}/Segments"

                segments_to_scrape = get_all_segment_names(page, segments_page_url)
                
                if not segments_to_scrape:
                    print(f"No segments found for version {version}. Skipping.")
                    continue

                for i, seg in enumerate(segments_to_scrape):
                    print(f"\nProcessing segment {i+1} of {len(segments_to_scrape)}: {seg}")
                    
                    # <<< THE CORE LOGIC: Check if the file exists and decide whether to skip >>>
                    file_path = os.path.join(version_dir, f"{seg}.json")
                    if not args.replace and os.path.exists(file_path):
                        print(f"  - SKIPPING: File already exists at {file_path}. Use --replace to overwrite.")
                        continue
                    
                    # If we're here, we scrape.
                    short_desc, long_desc, fields_dict = scrape_segment(page, seg, version)
                    
                    if short_desc == "ERROR": continue

                    segment_data = {
                        "segment_id": seg,
                        "short_description": short_desc,
                        "description": long_desc,
                        "fields": fields_dict
                    }
                    
                    with open(file_path, "w") as f:
                        json.dump(segment_data, f, indent=2)
                    print(f"  ✅ Saved data for {seg} ({version}) to {file_path}")

        finally:
            browser.close()

    print(f"\n\n🎉 Scraping complete. All files saved in '{OUTPUT_DIR}'.")

if __name__ == "__main__":
    main()