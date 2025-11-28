"""
Scraper for Doodle Rock Rescue (Dallas, TX)
v3.0.0 - Follows individual dog links to get full details

This site is heavily JavaScript-rendered and requires a headless browser.
"""
import re
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
    self.base_url = "https://doodlerockrescue.org"
  
  def scrape(self) -> List[Dog]:
    """Scrape all dogs from Doodle Rock Rescue"""
    dogs = []
    
    # Try Playwright first (works in GitHub Actions)
    if self._playwright_available():
      print("  🎭 Using Playwright for JS rendering")
      
      available_url = self.config.get("available_url")
      if available_url:
        print(f"\n🐩 Scraping Doodle Rock - Available Dogs")
        dogs.extend(self._scrape_listing_page(available_url, "Available"))
      
      upcoming_url = self.config.get("upcoming_url")
      if upcoming_url:
        print(f"\n🐩 Scraping Doodle Rock - Upcoming Dogs")
        dogs.extend(self._scrape_listing_page(upcoming_url, "Upcoming"))
    else:
      print("  ⚠️ Playwright not available - Doodle Rock requires JS rendering")
    
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
  
  def _scrape_listing_page(self, url: str, status: str) -> List[Dog]:
    """Scrape listing page to find individual dog links, then scrape each dog"""
    dogs = []
    dog_links = []
    
    try:
      from playwright.sync_api import sync_playwright
      
      with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        print(f"  🔍 Fetching listing: {url}")
        page.goto(url, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(3000)
        
        # Scroll to load all content
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(2000)
        
        # Find all dog profile links
        # Pattern: /rescue-dog/dog-name/
        links = page.query_selector_all('a[href*="/rescue-dog/"]')
        
        for link in links:
          href = link.get_attribute('href')
          if href and '/rescue-dog/' in href:
            # Make absolute URL
            if href.startswith('/'):
              href = self.base_url + href
            if href not in dog_links:
              dog_links.append(href)
        
        print(f"  🔗 Found {len(dog_links)} dog profile links")
        
        # Now visit each dog's profile page
        for dog_url in dog_links:
          dog = self._scrape_dog_profile(page, dog_url, status)
          if dog:
            dogs.append(dog)
        
        browser.close()
        
    except Exception as e:
      print(f"  ❌ Error: {e}")
    
    return dogs
  
  def _scrape_dog_profile(self, page, url: str, status: str) -> Optional[Dog]:
    """Scrape individual dog profile page for full details"""
    try:
      print(f"  🔍 Fetching profile: {url}")
      page.goto(url, wait_until="networkidle", timeout=30000)
      page.wait_for_timeout(1500)
      
      html = page.content()
      soup = BeautifulSoup(html, "html.parser")
      
      # Get dog name from title or h1
      name = ""
      h1 = soup.find("h1")
      if h1:
        name = h1.get_text().strip()
      
      if not name:
        title = soup.find("title")
        if title:
          name = title.get_text().split("-")[0].split("|")[0].strip()
      
      if not name or len(name) < 2:
        return None
      
      # Clean name - remove things like "#2" suffix
      name = re.sub(r'\s*#\d+\s*$', '', name).strip()
      
      # Get all text content for parsing
      text = soup.get_text(separator="\n", strip=True)
      
      # Extract details
      weight = self._extract_weight(text)
      age = self._extract_age(text)
      sex = self._extract_sex(text)
      breed = self._extract_breed(text)
      
      # Look for "good with" info
      good_with_dogs = self._extract_good_with(text, "dogs")
      good_with_kids = self._extract_good_with(text, "kids") or self._extract_good_with(text, "children")
      good_with_cats = self._extract_good_with(text, "cats")
      
      # Energy level
      energy = self._extract_energy(text)
      
      # Special needs
      special_needs = self._extract_special_needs(text)
      
      dog = Dog(
        dog_id=self.create_dog_id(name),
        dog_name=name,
        rescue_name=self.rescue_name,
        breed=breed or "Poodle Mix",
        weight=weight,
        age_range=age,
        age_category=self._categorize_age(age),
        sex=sex,
        shedding="Low",  # Poodle mixes typically low shedding
        energy_level=energy,
        good_with_kids=good_with_kids,
        good_with_dogs=good_with_dogs,
        good_with_cats=good_with_cats,
        special_needs=special_needs,
        platform=self.platform,
        location=self.location,
        status=status,
        source_url=url,
        date_collected=get_current_date()
      )
      
      dog.fit_score = calculate_fit_score(dog)
      dog.watch_list = check_watch_list(dog)
      
      print(f"  🐕 {name}: {weight or '?'}lbs, {age or '?'} | Fit: {dog.fit_score} | {status}")
      return dog
      
    except Exception as e:
      print(f"  ⚠️ Error scraping {url}: {e}")
      return None
  
  def _extract_weight(self, text: str) -> Optional[int]:
    """Extract weight from text"""
    patterns = [
      r'(\d+)\s*(?:lbs?|pounds?)',
      r'weight[:\s]+(\d+)',
      r'(\d+)\s*(?:lb|pound)'
    ]
    for pattern in patterns:
      match = re.search(pattern, text.lower())
      if match:
        return int(match.group(1))
    return None
  
  def _extract_age(self, text: str) -> str:
    """Extract age from text"""
    patterns = [
      r'(\d+\.?\d*)\s*(?:years?|yrs?)\s*old',
      r'(\d+)\s*(?:months?|mos?)\s*old',
      r'age[:\s]+(\d+\.?\d*)\s*(?:years?|yrs?|months?|mos?)',
      r'(\d+\.?\d*)\s*(?:years?|yrs?)',
      r'(\d+)\s*(?:months?|mos?)'
    ]
    for pattern in patterns:
      match = re.search(pattern, text.lower())
      if match:
        num = match.group(1)
        if 'month' in pattern or 'mos' in pattern:
          return f"{num} months"
        return f"{num} years"
    return ""
  
  def _extract_sex(self, text: str) -> str:
    """Extract sex from text"""
    text_lower = text.lower()
    # Look for explicit mentions
    if re.search(r'\b(female|girl|spayed)\b', text_lower):
      return "Female"
    if re.search(r'\b(male|boy|neutered)\b', text_lower):
      return "Male"
    return ""
  
  def _extract_breed(self, text: str) -> str:
    """Extract breed from text"""
    breeds = [
      "goldendoodle", "labradoodle", "bernedoodle", "aussiedoodle",
      "sheepadoodle", "poodle mix", "poodle", "doodle"
    ]
    text_lower = text.lower()
    for breed in breeds:
      if breed in text_lower:
        return breed.title()
    return "Poodle Mix"
  
  def _extract_good_with(self, text: str, animal: str) -> str:
    """Extract good with dogs/kids/cats info"""
    text_lower = text.lower()
    
    # Positive patterns
    positive = [
      f"good with {animal}",
      f"great with {animal}",
      f"loves {animal}",
      f"gets along with {animal}",
      f"does well with {animal}",
      f"friendly with {animal}",
      f"ok with {animal}",
      f"yes.+{animal}",
      f"{animal}.+yes"
    ]
    
    # Negative patterns
    negative = [
      f"no {animal}",
      f"not good with {animal}",
      f"doesn't like {animal}",
      f"no other {animal}",
      f"only {animal}",
      f"{animal}.+no"
    ]
    
    for pattern in positive:
      if re.search(pattern, text_lower):
        return "Yes"
    
    for pattern in negative:
      if re.search(pattern, text_lower):
        return "No"
    
    return "Unknown"
  
  def _extract_energy(self, text: str) -> str:
    """Extract energy level"""
    text_lower = text.lower()
    
    low_indicators = ["calm", "mellow", "laid back", "lazy", "couch potato", "relaxed", "low energy"]
    high_indicators = ["high energy", "very active", "energetic", "needs lots of exercise", "hyper"]
    medium_indicators = ["moderate", "medium energy", "playful", "active"]
    
    for indicator in low_indicators:
      if indicator in text_lower:
        return "Low"
    
    for indicator in high_indicators:
      if indicator in text_lower:
        return "High"
    
    for indicator in medium_indicators:
      if indicator in text_lower:
        return "Medium"
    
    return "Medium"  # Default for doodles
  
  def _extract_special_needs(self, text: str) -> str:
    """Check for special needs mentions"""
    indicators = [
      "special needs", "medical", "medication", "ongoing treatment",
      "blind", "deaf", "diabetic", "seizure", "heart condition",
      "requires daily", "chronic", "disabled"
    ]
    text_lower = text.lower()
    for indicator in indicators:
      if indicator in text_lower:
        return "Yes"
    return "No"
  
  def _categorize_age(self, age_str: str) -> str:
    """Categorize age into Puppy/Adult/Senior"""
    if not age_str:
      return ""
    
    age_lower = age_str.lower()
    
    if "month" in age_lower:
      match = re.search(r"(\d+)", age_str)
      if match:
        months = int(match.group(1))
        return "Puppy" if months < 12 else "Adult"
      return "Puppy"
    
    if "year" in age_lower:
      match = re.search(r"(\d+\.?\d*)", age_str)
      if match:
        years = float(match.group(1))
        if years < 2:
          return "Puppy"
        elif years >= 8:
          return "Senior"
        else:
          return "Adult"
    
    return ""
