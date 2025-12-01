"""
Scraper for Doodle Rock Rescue (Dallas, TX)
v2.1.0 - Uses Playwright for JS rendering + pagination support

This site is heavily JavaScript-rendered and requires a headless browser.
Uses WordPress Views pagination (?wpv_paged=N)
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
        dogs.extend(self._scrape_with_playwright_paginated(available_url, "Available"))
      
      upcoming_url = self.config.get("upcoming_url")
      if upcoming_url:
        print(f"\n🐩 Scraping Doodle Rock - Upcoming Dogs")
        dogs.extend(self._scrape_with_playwright_paginated(upcoming_url, "Upcoming"))
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
  
  def _scrape_with_playwright_paginated(self, base_url: str, status: str) -> List[Dog]:
    """Scrape all pages using Playwright with WordPress pagination"""
    all_dogs = []
    page_num = 1
    max_pages = 10  # Safety limit
    
    try:
      from playwright.sync_api import sync_playwright
      
      with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        while page_num <= max_pages:
          # Build URL with pagination
          if page_num == 1:
            url = base_url
          else:
            # WordPress Views pagination format
            if "?" in base_url:
              url = f"{base_url}&wpv_paged={page_num}"
            else:
              url = f"{base_url}?wpv_paged={page_num}"
          
          print(f"  🔍 Fetching page {page_num}: {url}")
          
          try:
            page.goto(url, wait_until="networkidle", timeout=60000)
          except Exception as e:
            print(f"  ⚠️ Page {page_num} load error: {e}")
            break
          
          # Wait for content to load
          page.wait_for_timeout(3000)
          
          # Scroll to load lazy content
          page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
          page.wait_for_timeout(2000)
          page.evaluate("window.scrollTo(0, 0)")
          page.wait_for_timeout(1000)
          
          # Get page content
          html = page.content()
          soup = BeautifulSoup(html, "html.parser")
          
          # Parse dogs from this page
          page_dogs = self._parse_dog_page(soup, url, status)
          
          if not page_dogs:
            print(f"  ↳ No dogs found on page {page_num}, stopping pagination")
            break
          
          print(f"  ↳ Found {len(page_dogs)} dogs on page {page_num}")
          all_dogs.extend(page_dogs)
          
          # Check if there's a next page
          has_next = self._has_next_page(soup, page_num)
          if not has_next:
            print(f"  ↳ No more pages after page {page_num}")
            break
          
          page_num += 1
        
        browser.close()
        
    except Exception as e:
      print(f"  ❌ Playwright error: {e}")
    
    return all_dogs
  
  def _has_next_page(self, soup: BeautifulSoup, current_page: int) -> bool:
    """Check if there's a next page in WordPress pagination"""
    # Look for pagination links
    # Common patterns: wpv-pagination, page-numbers, pagination
    
    # Check for "next" link
    next_links = soup.find_all("a", class_=re.compile(r"(next|wpv-pagination-next)"))
    if next_links:
      return True
    
    # Check for page number links
    page_links = soup.find_all("a", href=re.compile(r"wpv_paged=\d+"))
    for link in page_links:
      href = link.get("href", "")
      match = re.search(r"wpv_paged=(\d+)", href)
      if match:
        linked_page = int(match.group(1))
        if linked_page > current_page:
          return True
    
    # Check for page-numbers class (WordPress default)
    page_numbers = soup.find_all("a", class_="page-numbers")
    for link in page_numbers:
      text = link.get_text(strip=True)
      if text.isdigit() and int(text) > current_page:
        return True
      if "next" in link.get("class", []) or "→" in text or "»" in text:
        return True
    
    return False
  
  def _scrape_with_playwright(self, url: str, status: str) -> List[Dog]:
    """Scrape single page using Playwright for full JS rendering (legacy)"""
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
    
    # Debug: count what we find
    all_cols = soup.find_all("div", class_=re.compile(r"col-sm-\d"))
    print(f"  🔍 Found {len(all_cols)} col-sm-* divs")
    
    # Doodle Rock structure: each dog is in a col-sm-4 div with:
    # - <a href="dog-page-url"><img src="thumbnail"></a>
    # - <center><a href="dog-page-url"><strong>Name,</strong> Breed</a><br>Status</center>
    
    for col in all_cols:
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
      
      # Skip non-dog entries (including tracking pixels like fbpx)
      skip_words = [
        "adopt", "foster", "alumni", "apply", "rescue", "doodle rock", "facebook",
        "fbpx", "pixel", "tracking", "script", "analytics", "gtag", "gtm",
        "widget", "sidebar", "footer", "header", "menu", "nav", "search"
      ]
      if any(word in name.lower() for word in skip_words):
        continue
      
      # Skip if name looks like code/technical
      if re.match(r"^[a-z]{2,4}$", name.lower()) and name.lower() in ["fbpx", "gtag", "init", "load"]:
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
      
      # Try to get additional details from individual dog page
      dog = self._enrich_dog_from_page(dog, dog_url)
      
      dog.fit_score = calculate_fit_score(dog)
      dog.watch_list = check_watch_list(dog)
      dogs.append(dog)
      
      img_status = "📸" if image_url else "🐕"
      print(f"  {img_status} {name} | {dog.weight or '?'}lbs | Fit: {dog.fit_score} | {dog_status}")
    
    # Fallback: if no dogs found with structured parsing, try other methods
    if not dogs:
      # Try parsing from center tags without /rescue-dog/ links (for upcoming page)
      dogs = self._parse_from_center_tags(soup, status)
    
    if not dogs:
      dogs = self._parse_from_images(soup, status)
    
    return dogs
  
  def _parse_from_center_tags(self, soup: BeautifulSoup, status: str) -> List[Dog]:
    """
    Parse dog info from <center> tags - used for upcoming dogs page
    where dogs don't have individual /rescue-dog/ pages yet.
    
    Structure is typically:
    <center>
      <strong>Name,</strong> Breed<br>
      Status text
    </center>
    """
    dogs = []
    seen_names = set()
    
    for col in soup.find_all("div", class_=re.compile(r"col-sm-\d")):
      # Look for center tag with dog info
      center = col.find("center")
      if not center:
        continue
      
      # Get text content
      text = center.get_text(separator=" ", strip=True)
      if not text or len(text) < 3:
        continue
      
      # Try to find name - usually before comma or in <strong> tag
      name = ""
      strong = center.find("strong")
      if strong:
        name = strong.get_text(strip=True).rstrip(",").strip()
      else:
        # Take first part before comma
        if "," in text:
          name = text.split(",")[0].strip()
        else:
          # First word might be name
          words = text.split()
          if words:
            name = words[0].strip()
      
      # Clean name
      name = re.sub(r"#\d+", "", name).strip()
      name = name.rstrip(",").strip()
      
      if not name or len(name) < 2 or len(name) > 40:
        continue
      
      # Skip non-dog entries
      skip_words = [
        "adopt", "foster", "alumni", "apply", "rescue", "doodle rock", "facebook",
        "fbpx", "pixel", "tracking", "script", "analytics", "the", "this",
        "available", "coming", "soon", "welcome", "dog"
      ]
      if name.lower() in skip_words or any(word == name.lower() for word in skip_words):
        continue
      
      # Skip duplicates
      name_key = name.lower()
      if name_key in seen_names:
        continue
      seen_names.add(name_key)
      
      # Get image from the col
      image_url = ""
      img = col.find("img")
      if img:
        image_url = img.get("src", "") or img.get("data-src", "")
      
      # Determine breed from text
      breed = "Poodle Mix"
      if "," in text:
        breed_part = text.split(",", 1)[1].strip()
        # Clean up breed - take first line/part
        breed_part = breed_part.split("\n")[0].split("<")[0].strip()
        if breed_part and len(breed_part) < 50:
          breed = breed_part
      
      # Check for status indicators in text
      text_lower = text.lower()
      dog_status = status
      if "pending" in text_lower:
        dog_status = "Pending"
      elif "adopted" in text_lower:
        continue  # Skip adopted dogs
      
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
        source_url="https://doodlerockrescue.org/adopt/coming-soon-for-adoption/",
        image_url=image_url,
        date_collected=get_current_date()
      )
      
      dog.fit_score = calculate_fit_score(dog)
      dog.watch_list = check_watch_list(dog)
      dogs.append(dog)
      
      img_icon = "📸" if image_url else "🐕"
      print(f"  {img_icon} {name} | Fit: {dog.fit_score} | {dog_status}")
    
    return dogs
  
  def _enrich_dog_from_page(self, dog: Dog, url: str) -> Dog:
    """Fetch individual dog page to get additional details like weight, energy, compatibility"""
    try:
      soup = self.fetch_page(url)
      if not soup:
        return dog
      
      # Get all text content
      text = soup.get_text(separator=" ", strip=True).lower()
      
      # Extract weight
      weight_match = re.search(r"(\d+)\s*(?:lbs?|pounds?)", text)
      if weight_match:
        dog.weight = int(weight_match.group(1))
      
      # Extract age if not already set
      if not dog.age_range:
        age_match = re.search(r"(\d+\.?\d*)\s*(years?|yrs?|months?|mos?|weeks?|wks?)", text)
        if age_match:
          num = age_match.group(1)
          unit = age_match.group(2)
          if "year" in unit or "yr" in unit:
            dog.age_range = f"{num} yrs"
          elif "month" in unit or "mo" in unit:
            dog.age_range = f"{num} mos"
          elif "week" in unit or "wk" in unit:
            dog.age_range = f"{num} wks"
      
      # Extract energy level
      if "high energy" in text or "very active" in text or "lots of exercise" in text:
        dog.energy_level = "High"
      elif "low energy" in text or "calm" in text or "couch potato" in text or "laid back" in text:
        dog.energy_level = "Low"
      elif "moderate energy" in text or "medium energy" in text:
        dog.energy_level = "Medium"
      
      # Extract good with dogs
      if "good with dogs" in text or "gets along with dogs" in text or "loves other dogs" in text:
        dog.good_with_dogs = "Yes"
      elif "no dogs" in text or "only dog" in text or "no other dogs" in text:
        dog.good_with_dogs = "No"
      
      # Extract good with cats
      if "good with cats" in text or "cat friendly" in text or "lives with cats" in text:
        dog.good_with_cats = "Yes"
      elif "no cats" in text or "not cat friendly" in text or "chases cats" in text:
        dog.good_with_cats = "No"
      
      # Extract good with kids
      if "good with kids" in text or "good with children" in text or "family friendly" in text:
        dog.good_with_kids = "Yes"
      elif "no kids" in text or "no children" in text or "no small children" in text or "older children only" in text:
        dog.good_with_kids = "No"
      
      # Check for special needs indicators
      if any(term in text for term in ["special needs", "medical needs", "ongoing medication", 
                                         "blind", "deaf", "three legs", "wheelchair"]):
        dog.special_needs = True
      
      # Collect ALL images from the page
      collected_images = []
      seen_urls = set()
      
      for img in soup.find_all("img"):
        src = img.get("src", "") or img.get("data-src", "")
        if not src:
          continue
        
        # Only want wp-content/uploads images (actual dog photos)
        if "wp-content/uploads" not in src:
          continue
        
        # Skip tiny thumbnails (wpcf_200x200, 150x150, etc.)
        if any(size in src for size in ["wpcf_200x200", "150x150", "100x100", "50x50", "-150x", "-100x", "-50x"]):
          continue
        
        # Skip if we've seen this URL
        if src in seen_urls:
          continue
        seen_urls.add(src)
        
        collected_images.append(src)
      
      # Set primary image and additional images
      if collected_images:
        dog.image_url = collected_images[0]  # Legacy field
        dog.additional_images = collected_images[1:] if len(collected_images) > 1 else []
        print(f"    📸 Found {len(collected_images)} images")
      
      print(f"    ↳ Enriched: {dog.weight or '?'}lbs, energy={dog.energy_level}, dogs={dog.good_with_dogs or '?'}")
      
    except Exception as e:
      print(f"    ⚠️ Could not enrich {dog.dog_name}: {e}")
    
    return dog
  
  def _parse_from_images(self, soup: BeautifulSoup, status: str) -> List[Dog]:
    """Extract dog names from image alt text"""
    dogs = []
    seen_names = set()
    
    for img in soup.find_all("img", alt=True):
      alt = img.get("alt", "").strip()
      
      # Skip generic alts
      if len(alt) < 3 or len(alt) > 40:
        continue
      
      skip_words = [
        "logo", "image", "photo", "icon", "banner", "doodle rock", "rescue",
        "fbpx", "pixel", "tracking", "script", "analytics", "gtag", "gtm",
        "widget", "sidebar", "footer", "header", "menu", "nav", "search",
        "facebook", "twitter", "instagram", "social"
      ]
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
