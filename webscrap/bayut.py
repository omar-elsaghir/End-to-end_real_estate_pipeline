from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException
import pandas as pd
import time

options = Options()
options.add_argument("--start-maximized")
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_argument("user-agent=Mozilla/5.0")

driver = webdriver.Chrome(options=options)

url = "https://www.bayut.eg/en/egypt/properties-for-sale/"
driver.get(url)
time.sleep(6)

driver.execute_script(
    "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
)
for _ in range(20):
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(2)


def get_text_by_selectors(element, selectors):
    """Try a list of CSS selectors in order, return the first non-empty text found."""
    for sel in selectors:
        try:
            found = element.find_element(By.CSS_SELECTOR, sel)
            text = found.text.strip()
            if text:
                return text
            # fall back to aria-label if text is empty
            label = found.get_attribute("aria-label")
            if label:
                return label.strip()
        except NoSuchElementException:
            continue
    return None


data = []
num_pages = 50

for page in range(num_pages):
    print(f"\nScraping page {page + 1}")
    time.sleep(5)

    properties = driver.find_elements(By.CSS_SELECTOR, "article")
    print("Found:", len(properties))

    for prop in properties:
        try:
            title = get_text_by_selectors(prop, ["h2", "h2 a", "[aria-label*='Title']"])
        except StaleElementReferenceException:
            continue

        price = get_text_by_selectors(prop, [
            "[aria-label*='Price']",
            "span[aria-label*='price']",
            "[data-testid*='price']"
        ])

        location = get_text_by_selectors(prop, [
            "[aria-label*='Location']",
            "[data-testid*='location']"
        ])

        area = get_text_by_selectors(prop, [
            "[aria-label*='Area']",
            "[data-testid*='area']",
        ])

        bedrooms = get_text_by_selectors(prop, [
            "[aria-label*='Bed']",
            "[data-testid*='bed']",
        ])

        bathrooms = get_text_by_selectors(prop, [
            "[aria-label*='Bath']",
            "[data-testid*='bath']",
        ])

        # last-resort fallback: scan all spans' aria-labels/text
        if area is None or bedrooms is None or bathrooms is None:
            try:
                spans = prop.find_elements(By.CSS_SELECTOR, "span")
                for s in spans:
                    label = (s.get_attribute("aria-label") or "").lower()
                    text = s.text.strip()
                    if not text:
                        continue
                    if area is None and ("area" in label or "m²" in text or "sqft" in text.lower()):
                        area = text
                    elif bedrooms is None and ("bed" in label or "bed" in text.lower()):
                        bedrooms = text
                    elif bathrooms is None and ("bath" in label or "bath" in text.lower()):
                        bathrooms = text
            except StaleElementReferenceException:
                pass

        if title is not None:
            data.append({
                "title": title,
                "price": price,
                "location": location,
                "area": area,
                "bedrooms": bedrooms,
                "bathrooms": bathrooms
            })

    try:
        next_button = driver.find_element(By.CSS_SELECTOR, 'a[title="Next"]')
        driver.execute_script("arguments[0].click();", next_button)
        time.sleep(6)
    except NoSuchElementException:
        print("No more pages")
        break

driver.quit()

df = pd.DataFrame(data)

if not df.empty and "price" in df.columns:
    df["price"] = (
        df["price"]
        .astype(str)
        .str.replace(",", "", regex=False)
        .str.replace("EGP", "", regex=False)
        .str.replace("From", "", regex=False)
        .str.strip()
    )
    df["price"] = pd.to_numeric(df["price"], errors="coerce")

df.to_csv("bayut_properties.csv", index=False)

print("\nDone Successfully")
print(df.head())