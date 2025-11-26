"""
Scraper for Doodle Dandy Rescue (DFW/Houston/Austin/SA)
Wix-based site - likely needs Selenium
"""
import re
import json
from typing import List, Optional
from bs4 import BeautifulSoup
from scrapers.base_scraper import BaseScraper
from models import Dog, get_current_date
from scoring import calculate_fit_score, check_watch_list


class DoodleDandyScraper(BaseScraper):
  """Scraper for doodledandyrescue.org"""
  
  def __init__(self, config: dict):
    super().__init__("Doodle Dandy Rescue", config)
    self.platform = "doodledandyrescue.org"
    self.location = config.get("location", "TX (DFW/Houston/Austin/SA)")
  
  def scrape(self) -> List[Dog]:
    """Scrape all dogs from Doodle Dandy Rescue"""
    dogs = []
    
    # Available dogs
    available_url = self.config.get("available_url")
    if available_url:
      print(f"\n🐩 Scraping Doodle Dandy - Available Dogs")
      dogs.extend(self._scrape_page(available_url, "Available"))
    
    # Pending dogs
    pending_url = self.config.get("pending_url")
    if pending_url:
      print(f"\n🐩 Scraping Doodle Dandy - Pending Dogs")
      dogs.extend(self._scrape_page(pending_url, "Pending"))
    
    # Upcoming/foster dogs
    upcoming_url = self.config.get("upcoming_url")
    if upcoming_url:
      print(f"\n🐩 Scraping Doodle Dandy - Coming Soon")
      dogs.extend(self._scrape_page(upcoming_url, "Upcoming"))
    
    print(f"  ✅ Found {len(dogs)} dogs from Doodle Dandy")
    return dogs
  
  def _scrape_page(self, url: str, status: str) -> List[Dog]:
    """Scrape a listing page"""
    dogs = []
    
    # Wix sites often have data in JSON format in the page
    soup = self.fetch_page(url)
    if soup:
      # Try to find Wix JSON data
      dogs = self._parse_wix_data(soup, status)
      
      # Fallback: parse visible text/images
      if not dogs:
        dogs = self._parse_html_fallback(soup, url, status)
    
    # If still no dogs, try Selenium
    if not dogs and self._selenium_available():
      print("  🔄 Trying Selenium for JS-rendered content...")
      dogs = self._scrape_with_selenium(url, status)
    
    return dogs
  
  def _parse_wix_data(self, soup: BeautifulSoup, status: str) -> List[Dog]:
    """Try to extract dog data from Wix JSON in page"""
    dogs = []
    
    # Wix stores data in script tags with specific patterns
    scripts = soup.find_all("script")
    for script in scripts:
      if script.string and "wixData" in script.string:
        try:
          # Try to find JSON data
          match = re.search(r'"items"\s*:\s*(\[.+?\])', script.string, re.DOTALL)
          if match:
            items = json.loads(match.group(1))
            for item in items:
              dog = self._parse_wix_item(item, status)
              if dog:
                dogs.append(dog)
        except:
          continue
    
    return dogs
  
  def _parse_wix_item(self, item: dict, status: str) -> Optional[Dog]:
    """Parse a Wix data item into a Dog object"""
    name = item.get("name", item.get("title", ""))
    if not name:
      return None
    
    dog = Dog(
      dog_id=self.create_dog_id(name),
      dog_name=name,
      rescue_name=self.rescue_name,
      breed=item.get("breed", "Doodle/Mix"),
      weight=self._parse_weight(item.get("weight")),
      age_range=item.get("age", ""),
      sex=item.get("sex", item.get("gender", "")),
      shedding="Low",  # Assume low for doodles
      energy_level=item.get("energy", ""),
      good_with_kids=self.normalize_yes_no(item.get("kids", "Unknown")),
      good_with_dogs=self.normalize_yes_no(item.get("dogs", "Unknown")),
      good_with_cats=self.normalize_yes_no(item.get("cats", "Unknown")),
      special_needs="Yes" if item.get("specialNeeds") else "No",
      adoption_fee=item.get("fee", ""),
      platform=self.platform,
      location=self.location,
      status=status,
      source_url=item.get("link", item.get("url", "")),
      date_collected=get_current_date()
    )
    
    dog.fit_score = calculate_fit_score(dog)
    dog.watch_list = check_watch_list(dog)
    
    print(f"  🐕 {name}: {dog.weight or '?'}lbs | Fit: {dog.fit_score} | {status}")
    return dog
  
  def _parse_weight(self, weight_val) -> Optional[int]:
    """Parse weight from various formats"""
    if not weight_val:
      return None
    if isinstance(weight_val, (int, float)):
      return int(weight_val)
    if isinstance(weight_val, str):
      match = re.search(r"(\d+)", weight_val)
      if match:
        return int(match.group(1))
    return None
  
  def _parse_html_fallback(self, soup: BeautifulSoup, url: str, status: str) -> List[Dog]:
    """Fallback: parse visible HTML for dog info"""
    dogs = []
    
    # Look for dog name patterns in headings
    headings = soup.find_all(["h1", "h2", "h3", "h4"])
    for h in headings:
      text = h.get_text().strip()
      # Skip common non-name headings
      if len(text) > 2 and len(text) < 30:
        skip_words = ["adopt", "available", "pending", "rescue", "doodle", "about", "contact", "foster"]
        if not any(word in text.lower() for word in skip_words):
          dog = self._create_minimal_dog(text, status)
          if dog:
            dogs.append(dog)
    
    # Also look at image alt text
    imgs = soup.find_all("img", alt=True)
    seen_names = {d.dog_name for d in dogs}
    for img in imgs:
      alt = img.get("alt", "").strip()
      if 2 < len(alt) < 30 and alt not in seen_names:
        skip_words = ["logo", "image", "photo", "icon", "banner"]
        if not any(word in alt.lower() for word in skip_words):
          dog = self._create_minimal_dog(alt, status)
          if dog:
            dogs.append(dog)
            seen_names.add(alt)
    
    return dogs
  
  def _create_minimal_dog(self, name: str, status: str) -> Optional[Dog]:
    """Create dog with minimal info"""
    name = name.strip().title()
    
    dog = Dog(
      dog_id=self.create_dog_id(name),
      dog_name=name,
      rescue_name=self.rescue_name,
      breed="Doodle/Mix",
      shedding="Low",
      platform=self.platform,
      location=self.location,
      status=status,
      date_collected=get_current_date()
    )
    
    dog.fit_score = calculate_fit_score(dog)
    dog.watch_list = check_watch_list(dog)
    
    print(f"  🐕 {name} | Fit: {dog.fit_score} | {status}")
    return dog
  
  def _selenium_available(self) -> bool:
    """Check if Selenium is available"""
    try:
      from selenium import webdriver
      return True
    except ImportError:
      return False
  
  def _scrape_with_selenium(self, url: str, status: str) -> List[Dog]:
    """Scrape using Selenium for JS-rendered content"""
    dogs = []
    
    try:
      from selenium import webdriver
      from selenium.webdriver.chrome.options import Options
      from selenium.webdriver.common.by import By
      import time
      
      options = Options()
      options.add_argument("--headless")
      options.add_argument("--no-sandbox")
      options.add_argument("--disable-dev-shm-usage")
      
      driver = webdriver.Chrome(options=options)
      driver.get(url)
      time.sleep(5)  # Wix sites need time to render
      
      # Scroll to load lazy content
      driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
      time.sleep(2)
      driver.execute_script("window.scrollTo(0, 0);")
      time.sleep(1)
      
      soup = BeautifulSoup(driver.page_source, "html.parser")
      
      # Parse the rendered content
      dogs = self._parse_html_fallback(soup, url, status)
      
      # Look for gallery items (common Wix pattern)
      gallery_items = driver.find_elements(By.CSS_SELECTOR, "[data-hook='item-container'], .gallery-item, .pro-gallery-item")
      for item in gallery_items:
        try:
          # Try to get text from the item
          text = item.text.strip()
          if text and len(text) < 50:
            name = text.split("\n")[0]
            if name and len(name) > 2:
              dog = self._create_minimal_dog(name, status)
              if dog and dog.dog_name not in [d.dog_name for d in dogs]:
                dogs.append(dog)
        except:
          continue
      
      driver.quit()
      
    except Exception as e:
      print(f"  ❌ Selenium error: {e}")
    
    return dogs
