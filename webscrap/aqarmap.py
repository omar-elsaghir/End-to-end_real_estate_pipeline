from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import pandas as pd
import time

options = Options()
options.add_argument("--start-maximized")
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_argument("user-agent=Mozilla/5.0")

driver = webdriver.Chrome()

driver.get("https://aqarmap.com.eg/en/for-sale/apartment/")
time.sleep(5)

# bypass detection
driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

# scroll
for _ in range(35):
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(2)

data = []

num_pages = 50

for page in range(num_pages):
    print(f"Scraping page {page + 1}")

    properties = driver.find_elements(By.CSS_SELECTOR, "article.listing-card")

    print("Found:", len(properties))

    for prop in properties:
        try:
            price = prop.find_element(By.CSS_SELECTOR, "data").get_attribute("value")
        except:
            price = None

        try:
            title = prop.find_element(By.CSS_SELECTOR, "div.listing-card-details h2").text
        except:
            title = None

        try:
            location_element = prop.find_element(By.CSS_SELECTOR, "div.text-caption-1.text-gray__dark_2")
            location = location_element.text.strip()
        except:
            location = None

        try:
            items = prop.find_elements(By.CSS_SELECTOR, "ul.list-none > li")
            area = items[0].text if len(items) > 0 else None
            bedrooms = items[1].text if len(items) > 1 else None
            bathrooms = items[2].text if len(items) > 2 else None
        except:
            area = bedrooms = bathrooms = None

        data.append({
            "title": title,
            "price": price,
            "location": location,
            "area": area,
            "bedrooms": bedrooms,
            "bathrooms": bathrooms,
        })

    try:
        next_button = driver.find_element(By.CSS_SELECTOR, 'a[title="Next Page"]')
        driver.execute_script("arguments[0].click();", next_button)
        time.sleep(5)
    except:
        print("Stopped early - no more pages")
        break

driver.quit()

df = pd.DataFrame(data)
df.to_csv("aqarmapfinaaal.csv", index=False, encoding="utf-8-sig")
print("Done ")