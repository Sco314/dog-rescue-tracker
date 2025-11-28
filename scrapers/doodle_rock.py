"""
Scraper for Doodle Rock Rescue (Dallas, TX)
v2.0.0 - Uses Playwright for JS rendering (works in GitHub Actions)

This site is heavily JavaScript-rendered and requires a headless browser.
"""
import re
import os
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
  
  def scrape(self) -> List[Dog]:
    """Scrape all dogs from Doodle Rock Rescue"""
    dogs = []
    
    # Try Playwright first (works in GitHub Actions)
    if self._playwright_available():
      print("  🎭 Using Playwright for JS rendering")
      
      available_url = self.config.get("available_url")
      if available_url:
        print(f"\n🐩 Scraping Doodle Rock - Available Dogs")
        dogs.extend(self._scrape_with_playwright(available_url, "Available"))
      
      upcoming_url = self.config.get("upcoming_url")
      if upcoming_url:
        print(f"\n🐩 Scraping Doodle Rock - Upcoming Dogs")
        dogs.extend(self._scrape_with_playwright(upcoming_url, "Upcoming"))
    else:
      # Fallback: try basic fetch (won't get much data)
      print("  ⚠️ Playwright not available - trying basic fetch")
      available_url = self.config.get("available_url")
      if available_url:
        dogs.extend(self._scrape_basic(available_url, "Available"))
    
    # Deduplicate
    seen = set()
    unique_dogs = []
    for dog in dogs:
      if dog.dog_id not in seen:
        seen.add(dog.dog_id)
        unique_dogs.append(dog)
    
    print(f"  ✅ Found {len(unique_dogs)} dogs from Doodle Rock")
    return unique_dogs
  
  def _playwright_available(self) -> bool:
    """Check if Playwright is available"""
    try:
      from playwright.sync_api import sync_playwright
      return True
    except ImportError:
      return False
  
  def _scrape_with_playwright(self, url: str, status: str) -> List[Dog]:
    """Scrape using Playwright for full JS rendering"""
    dogs = []
    
    try:
      from playwright.sync_api import sync_playwright
      
      with sync_playwright() as p:
        # Launch browser
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        print(f"  🔍 Fetching: {url}")
        page.goto(url, wait_until="networkidle", timeout=60000)
        
        # Wait for content to load
        page.wait_for_timeout(3000)
        
        # Scroll to load lazy content
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(2000)
        page.evaluate("window.scrollTo(0, 0)")
        page.wait_for_timeout(1000)
        
        # Get page content
        html = page.content()
        browser.close()
        
        # Parse with BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        dogs = self._parse_dog_page(soup, url, status)
        
    except Exception as e:
      print(f"  ❌ Playwright error: {e}")
    
    return dogs
  
  def _scrape_basic(self, url: str, status: str) -> List[Dog]:
    """Fallback: basic HTTP fetch (limited results expected)"""
    dogs = []
    soup = self.fetch_page(url)
    
    if soup:
      dogs = self._parse_dog_page(soup, url, status)
    
    return dogs
  
  def _parse_dog_page(self, soup: BeautifulSoup, url: str, status: str) -> List[Dog]:
    """Parse dog listings from page HTML"""
    dogs = []
    
    # Get all text for analysis
    text = soup.get_text(separator="\n", strip=True)
    
    # Look for dog names and info patterns
    # Doodle Rock typically shows: Name, Breed, Status
    # Example: "Drizzle, Poodle Mix Available"
    
    # Pattern 1: Look for elements that might be dog cards
    dog_elements = soup.find_all(["div", "article", "a"], 
                                  class_=re.compile(r"dog|pet|card|item|gallery", re.I))
    
    for elem in dog_elements:
      dog = self._parse_dog_element(elem, status)
      if dog:
        dogs.append(dog)
    
    # Pattern 2: Parse structured text (Name, Breed pattern)
    if not dogs:
      dogs = self._parse_text_listings(text, status)
    
    # Pattern 3: Look at image alt text
    if not dogs:
      dogs = self._parse_from_images(soup, status)
    
    return dogs
  
  def _parse_dog_element(self, elem, status: str) -> Optional[Dog]:
    """Parse a single dog element"""
    text = elem.get_text(separator=" ", strip=True)
    
    # Skip if too short or looks like navigation
    if len(text) < 3 or len(text) > 200:
      return None
    
    # Try to extract name and breed
    # Common patterns: "Name - Breed" or "Name, Breed" or just "Name"
    name = None
    breed = "Poodle Mix"  # Default for this rescue
    
    # Pattern: "Name, Breed Status" or "Name - Breed"
    match = re.match(r"^([A-Za-z][A-Za-z\s'#\d]+?)[\s,\-]+(?:Poodle|Doodle|Mix|Shih)", text)
    if match:
      name = match.group(1).strip()
    else:
      # Just take first word/phrase as name
      parts = re.split(r"[\n\r,\-]", text)
      if parts:
        potential_name = parts[0].strip()
        if 2 < len(potential_name) < 30:
          name = potential_name
    
    if not name:
      return None
    
    # Clean name
    name = re.sub(r"#\d+", "", name).strip()
    
    # Skip non-dog entries
    skip_words = ["adopt", "foster", "available", "pending", "alumni", "apply", 
                  "rescue", "doodle rock", "facebook", "instagram"]
    if any(word in name.lower() for word in skip_words):
      return None
    
    # Try to find image in element
    image_url = ""
    img = elem.find("img")
    if img:
      image_url = img.get("src", "") or img.get("data-src", "")
    
    # Create dog
    dog = Dog(
      dog_id=self.create_dog_id(name),
      dog_name=name,
      rescue_name=self.rescue_name,
      breed=breed,
      shedding="Low",  # Poodle mixes
      energy_level="Medium",
      platform=self.platform,
      location=self.location,
      status=status,
      source_url=f"{self.config.get('available_url', '')}",
      image_url=image_url,
      date_collected=get_current_date()
    )
    
    dog.fit_score = calculate_fit_score(dog)
    dog.watch_list = check_watch_list(dog)
    
    print(f"  🐕 {name} | Fit: {dog.fit_score} | {status}")
    return dog
  
  def _parse_text_listings(self, text: str, status: str) -> List[Dog]:
    """Parse dog names from text content"""
    dogs = []
    
    # Look for pattern: Name, Breed Available/Pending
    pattern = r"([A-Z][a-z]+(?:\s+#?\d+)?)\s*,?\s*(?:Poodle|Doodle)\s*(?:Mix)?\s*(?:Available|Pending)?"
    matches = re.findall(pattern, text)
    
    for name in matches:
      name = name.strip()
      if len(name) < 2 or len(name) > 30:
        continue
      
      dog = Dog(
        dog_id=self.create_dog_id(name),
        dog_name=name,
        rescue_name=self.rescue_name,
        breed="Poodle Mix",
        shedding="Low",
        energy_level="Medium",
        platform=self.platform,
        location=self.location,
        status=status,
        date_collected=get_current_date()
      )
      
      dog.fit_score = calculate_fit_score(dog)
      dog.watch_list = check_watch_list(dog)
      dogs.append(dog)
      print(f"  🐕 {name} | Fit: {dog.fit_score} | {status}")
    
    return dogs
  
  def _parse_from_images(self, soup: BeautifulSoup, status: str) -> List[Dog]:
    """Extract dog names from image alt text"""
    dogs = []
    seen_names = set()
    
    for img in soup.find_all("img", alt=True):
      alt = img.get("alt", "").strip()
      
      # Skip generic alts
      if len(alt) < 3 or len(alt) > 40:
        continue
      
      skip_words = ["logo", "image", "photo", "icon", "banner", "doodle rock", "rescue"]
      if any(word in alt.lower() for word in skip_words):
        continue
      
      # Clean up alt text
      name = re.sub(r"\.(jpg|png|gif|jpeg).*$", "", alt, flags=re.I)
      name = re.sub(r"#\d+", "", name).strip()
      
      # Get image URL
      image_url = img.get("src", "") or img.get("data-src", "")
      
      if name and name not in seen_names and 2 < len(name) < 30:
        seen_names.add(name)
        
        dog = Dog(
          dog_id=self.create_dog_id(name),
          dog_name=name,
          rescue_name=self.rescue_name,
          breed="Poodle Mix",
          shedding="Low",
          energy_level="Medium",
          platform=self.platform,
          location=self.location,
          status=status,
          image_url=image_url,
          date_collected=get_current_date()
        )
        
        dog.fit_score = calculate_fit_score(dog)
        dog.watch_list = check_watch_list(dog)
        dogs.append(dog)
        print(f"  🐕 {name} | Fit: {dog.fit_score} | {status}")
    
    return dogs
