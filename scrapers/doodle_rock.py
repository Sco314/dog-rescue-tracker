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
    
    # Doodle Rock structure: each dog is in a col-sm-4 div with:
    # - <a href="dog-page-url"><img src="thumbnail"></a>
    # - <center><a href="dog-page-url"><strong>Name,</strong> Breed</a><br>Status</center>
    
    for col in soup.find_all("div", class_=re.compile(r"col-sm-\d")):
      # Find the image link
      img_link = col.find("a", href=re.compile(r"/rescue-dog/"))
      if not img_link:
        continue
      
      dog_url = img_link.get("href", "")
      if not dog_url.startswith("http"):
        dog_url = "https://doodlerockrescue.org" + dog_url
      
      # Get the image
      img = img_link.find("img")
      image_url = ""
      if img:
        image_url = img.get("src", "") or img.get("data-src", "")
      
      # Get the name from the center text
      center = col.find("center")
      if not center:
        continue
      
      name_link = center.find("a")
      if not name_link:
        continue
      
      text = name_link.get_text(strip=True)
      # Format: "Name, Poodle Mix" or "Name, Breed"
      name = text.split(",")[0].strip()
      
      # Clean name
      name = re.sub(r"#\d+", "", name).strip()
      
      if not name or len(name) < 2 or len(name) > 40:
        continue
      
      # Skip non-dog entries
      skip_words = ["adopt", "foster", "alumni", "apply", "rescue", "doodle rock", "facebook"]
      if any(word in name.lower() for word in skip_words):
        continue
      
      # Determine breed from text
      breed = "Poodle Mix"
      if "," in text:
        breed_part = text.split(",", 1)[1].strip()
        if breed_part:
          breed = breed_part
      
      # Check for status in center text (might override page-level status)
      center_text = center.get_text(strip=True).lower()
      dog_status = status
      if "pending" in center_text:
        dog_status = "Pending"
      elif "available" in center_text:
        dog_status = "Available"
      
      dog = Dog(
        dog_id=self.create_dog_id(name),
        dog_name=name,
        rescue_name=self.rescue_name,
        breed=breed,
        shedding="Low",  # Poodle mixes
        energy_level="Medium",
        platform=self.platform,
        location=self.location,
        status=dog_status,
        source_url=dog_url,
        image_url=image_url,
        date_collected=get_current_date()
      )
      
      dog.fit_score = calculate_fit_score(dog)
      dog.watch_list = check_watch_list(dog)
      dogs.append(dog)
      
      img_status = "📸" if image_url else "🐕"
      print(f"  {img_status} {name} | Fit: {dog.fit_score} | {dog_status}")
    
    # Fallback: if no dogs found with structured parsing, try other methods
    if not dogs:
      dogs = self._parse_from_images(soup, status)
    
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
