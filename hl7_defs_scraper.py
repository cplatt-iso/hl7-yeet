# hl7_defs_scraper_final.py
#
# Pulls every HL7 v2.5.1 field definition from Caristix.
# This version uses a robust locator to avoid strict mode violations.

from playwright.sync_api import sync_playwright, Page, TimeoutError # type: ignore
import json
import re

BASE = "https://hl7-definition.caristix.com"
VERSION_PATH = "/v2/HL7v2.5.1"
SEGMENTS_URL = f"{BASE}{VERSION_PATH}/Segments"


# ────────────────────────────────────────────────────────────────

def get_attribute_by_label(page: Page, label: str) -> str:
    """Finds a label (e.g., 'Length') and returns the associated value next to it."""
    try:
        return page.locator(
            f"div.attribute-container:has(span.cx-caption:text-is('{label}')) span.attribute-value"
        ).inner_text(timeout=5000).strip()
    except Exception:
        return "N/A"

def get_all_segment_names(page: Page) -> list[str]:
    """Scrapes the main segments page to get a list of all segment names."""
    print("Scraping segment list...")
    page.goto(SEGMENTS_URL, timeout=90_000)
    page.wait_for_load_state('networkidle', timeout=30_000)
    
    segment_links = page.locator("tbody tr td:first-child a").all()
    segment_names = [link.inner_text().strip() for link in segment_links if link.inner_text().strip()]
    
    print(f"Found {len(segment_names)} segments.")
    return segment_names

def scrape_segment(page: Page, segment: str) -> dict:
    """Scrapes a segment's fields by finding all field links and visiting each one."""
    print(f"\nScraping segment: {segment}")
    segment_url = f"{SEGMENTS_URL}/{segment}"
    page.goto(segment_url, timeout=90_000)
    page.wait_for_load_state('networkidle', timeout=45_000)

    # --- KEY FIX HERE ---
    # Directly locate all <a> tags that link to a field detail page for the current segment.
    # This is far more robust than iterating through table rows and avoids the strict mode violation.
    field_link_locator = f"a[href*='{VERSION_PATH}/Fields/{segment}.']"
    field_links = page.locator(field_link_locator).all()

    field_urls = []
    for link in field_links:
        href = link.get_attribute('href')
        if href:
            full_url = BASE + href
            if full_url not in field_urls:
                field_urls.append(full_url)
    
    print(f"  ↳ Found {len(field_urls)} fields for {segment}. Now scraping details for each...")

    # 2. Visit each field's detail page to get the complete data
    fields_dict = {}
    for url in field_urls:
        try:
            page.goto(url, timeout=90_000, wait_until="domcontentloaded")
            # Wait for the main header of the field detail page to be visible
            page.locator("app-field-detail h2").wait_for(timeout=30_000)
            
            header_text = page.locator("app-field-detail h2").inner_text()
            match = re.search(r"-\s*([A-Z0-9\.]+\.\d+)\s*-\s*(.*)", header_text)
            if not match:
                print(f"    - Could not parse header on page {url}. Header was: '{header_text}'")
                continue
            
            field_id_full, field_name = match.groups()
            field_idx = field_id_full.split('.')[-1]
            print(f"    - Scraping {field_id_full}...")

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

    return fields_dict

# ────────────────────────────────────────────────────────────────

def main():
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        
        all_results = {}
        try:
            # For a full run, use the line below
            # segments_to_scrape = get_all_segment_names(page)
            
            # For testing, we'll just run with a few segments.
            segments_to_scrape = ["MSH", "PID", "ORC", "OBR", "OBX", "PV1", "OBX", "NTE", "DG1", "PR1", "AL1", "RXA", "RXR", "SPM", "EVN", "PD1", "PV1", "PV2", "IN1", "MRG"]

            for seg in segments_to_scrape:
                all_results[seg] = scrape_segment(page, seg)

        finally:
            browser.close()

    if all_results:
        with open("hl7_field_defs.json", "w") as f:
            json.dump(all_results, f, indent=2)
        print("\n✅  Saved all scraped data to hl7_field_defs.json")
        
        print("\n--- Sample output for MSH['1'] ---")
        print(json.dumps(all_results.get("MSH", {}).get("1", {}), indent=2))
    else:
        print("\n❌ No data was scraped. The output file was not created.")

if __name__ == "__main__":
    main()