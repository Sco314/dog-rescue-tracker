"""
Scraper for Doodle Rock Rescue (Dallas, TX)
May require Selenium for JS rendering
"""
import re
import json
from typing import List, Optional
from bs4 import BeautifulSoup
from scrapers.base_scraper import BaseScraper
from models import Dog, get_current_date
from scoring import calculate_fit_score, check_watch_list


class DoodleRockScraper(BaseScraper):
  """Scraper for doodlerockrescue.org"""
  
  def __init__(self, config: dict):
    super().__init__("Doodle Rock Rescue", config)
    self.platform = "doodlerockrescue.org"
    self.location = config.get("location", "Dallas, TX")
    self.use_selenium = False  # Will be set True if basic fetch fails
  
  def scrape(self) -> List[Dog]:
    """Scrape all dogs from Doodle Rock Rescue"""
    dogs = []
    
    # Try available dogs
    available_url = self.config.get("available_url")
    if available_url:
      print(f"\n🐩 Scraping Doodle Rock - Available Dogs")
      dogs.extend(self._scrape_page(available_url, "Available"))
    
    # Try upcoming/foster dogs
    upcoming_url = self.config.get("upcoming_url")
    if upcoming_url:
      print(f"\n🐩 Scraping Doodle Rock - Upcoming Dogs")
      dogs.extend(self._scrape_page(upcoming_url, "Upcoming"))
    
    print(f"  ✅ Found {len(dogs)} dogs from Doodle Rock")
    return dogs
  
  def _scrape_page(self, url: str, status: str) -> List[Dog]:
    """Scrape a listing page"""
    dogs = []
    
    # First try with requests (works if content is in HTML)
    soup = self.fetch_page(url)
    if soup:
      dogs = self._parse_listing_page(soup, url, status)
    
    # If no dogs found, try Selenium
    if not dogs and self._selenium_available():
      print("  🔄 Trying Selenium for JS-rendered content...")
      dogs = self._scrape_with_selenium(url, status)
    
    if not dogs:
      print(f"  ⚠️ No dogs found at {url} - may need manual check")
    
    return dogs
  
  def _parse_listing_page(self, soup: BeautifulSoup, base_url: str, status: str) -> List[Dog]:
    """Parse listing page HTML for dog cards"""
    dogs = []
    
    # Look for common patterns in dog listing pages
    # Pattern 1: Grid items with dog info
    dog_cards = soup.find_all("div", class_=re.compile(r"dog|pet|card|grid-item|animal"))
    
    # Pattern 2: Links with dog names
    if not dog_cards:
      dog_cards = soup.find_all("a", href=re.compile(r"/adopt/|/dog/|/pet/"))
    
    # Pattern 3: Look for structured data (JSON-LD)
    json_data = self._find_json_ld(soup)
    if json_data:
      dogs.extend(self._parse_json_ld(json_data, status))
    
    # Pattern 4: Images with alt text containing dog names
    if not dogs:
      imgs = soup.find_all("img", alt=re.compile(r".+"))
      seen_names = set()
      for img in imgs:
        alt = img.get("alt", "")
        # Filter out generic alts
        if len(alt) > 2 and len(alt) < 30 and alt.lower() not in ["logo", "image", "photo"]:
          if alt not in seen_names:
            seen_names.add(alt)
            dog = self._create_minimal_dog(alt, status)
            if dog:
              dogs.append(dog)
    
    return dogs
  
  def _find_json_ld(self, soup: BeautifulSoup) -> Optional[dict]:
    """Look for JSON-LD structured data"""
    scripts = soup.find_all("script", type="application/ld+json")
    for script in scripts:
      try:
        data = json.loads(script.string)
        return data
      except:
        continue
    return None
  
  def _parse_json_ld(self, data: dict, status: str) -> List[Dog]:
    """Parse JSON-LD structured data"""
    dogs = []
    # Handle various JSON-LD formats
    items = []
    if isinstance(data, list):
      items = data
    elif isinstance(data, dict):
      if "itemListElement" in data:
        items = data["itemListElement"]
      else:
        items = [data]
    
    for item in items:
      name = item.get("name", "")
      if name:
        dog = self._create_minimal_dog(name, status)
        if dog:
          # Add any additional info from JSON
          dog.source_url = item.get("url", "")
          dogs.append(dog)
    
    return dogs
  
  def _create_minimal_dog(self, name: str, status: str) -> Optional[Dog]:
    """Create dog with minimal info (name only)"""
    if not name or len(name) < 2:
      return None
    
    # Clean up name
    name = name.strip().title()
    
    dog = Dog(
      dog_id=self.create_dog_id(name),
      dog_name=name,
      rescue_name=self.rescue_name,
      breed="Doodle/Mix",  # Assume doodle
      shedding="Low",  # Assume low for doodles
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
      from selenium.webdriver.support.ui import WebDriverWait
      from selenium.webdriver.support import expected_conditions as EC
      import time
      
      # Setup headless Chrome
      options = Options()
      options.add_argument("--headless")
      options.add_argument("--no-sandbox")
      options.add_argument("--disable-dev-shm-usage")
      options.add_argument(f"user-agent={self.session.headers['User-Agent']}")
      
      driver = webdriver.Chrome(options=options)
      driver.get(url)
      
      # Wait for content to load
      time.sleep(3)  # Basic wait
      
      # Try to wait for specific elements
      try:
        WebDriverWait(driver, 10).until(
          EC.presence_of_element_located((By.CSS_SELECTOR, "img[alt]"))
        )
      except:
        pass
      
      # Get rendered HTML
      soup = BeautifulSoup(driver.page_source, "html.parser")
      dogs = self._parse_listing_page(soup, url, status)
      
      # Also try to find dog links and scrape those
      dog_links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/adopt/']")
      for link in dog_links:
        href = link.get_attribute("href")
        if href and "/available-dogs" not in href and "/coming-soon" not in href:
          # This is likely an individual dog page
          detail_dog = self._scrape_dog_detail_selenium(driver, href, status)
          if detail_dog:
            dogs.append(detail_dog)
      
      driver.quit()
      
    except Exception as e:
      print(f"  ❌ Selenium error: {e}")
    
    return dogs
  
  def _scrape_dog_detail_selenium(self, driver, url: str, status: str) -> Optional[Dog]:
    """Scrape individual dog page with Selenium"""
    try:
      driver.get(url)
      import time
      time.sleep(2)
      
      soup = BeautifulSoup(driver.page_source, "html.parser")
      
      # Get name from h1 or title
      name = ""
      h1 = soup.find("h1")
      if h1:
        name = h1.get_text().strip()
      
      if not name:
        title = soup.find("title")
        if title:
          name = title.get_text().split("-")[0].split("|")[0].strip()
      
      if not name:
        return None
      
      # Get bio text
      bio = ""
      content = soup.find("main") or soup.find("article") or soup.find("div", class_=re.compile("content"))
      if content:
        bio = content.get_text(separator=" ", strip=True)
      
      dog = Dog(
        dog_id=self.create_dog_id(name),
        dog_name=name,
        rescue_name=self.rescue_name,
        breed=self._extract_breed(bio),
        weight=self.extract_weight(bio) if bio else None,
        shedding="Low",
        platform=self.platform,
        location=self.location,
        status=status,
        source_url=url,
        notes=bio[:500] if bio else "",
        date_collected=get_current_date()
      )
      
      dog.fit_score = calculate_fit_score(dog)
      dog.watch_list = check_watch_list(dog)
      
      return dog
      
    except Exception as e:
      print(f"  ⚠️ Error scraping {url}: {e}")
      return None
  
  def _extract_breed(self, text: str) -> str:
    """Extract breed from text"""
    breeds = ["goldendoodle", "labradoodle", "bernedoodle", "aussiedoodle", 
              "sheepadoodle", "poodle", "doodle"]
    text_lower = text.lower()
    for breed in breeds:
      if breed in text_lower:
        return breed.title()
    return "Doodle/Mix"
