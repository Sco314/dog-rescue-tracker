"""
Scraper for Doodle Dandy Rescue (DFW/Houston/Austin/SA)
v2.0.0 - Rewritten to properly parse Wix text structure

The site outputs dog info in a structured text format:
  Name
  Breed
  Age
  Sex
  Weight
  Location
"""
import re
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
    
    # Deduplicate by dog_id
    seen = set()
    unique_dogs = []
    for dog in dogs:
      if dog.dog_id not in seen:
        seen.add(dog.dog_id)
        unique_dogs.append(dog)
    
    print(f"  ✅ Found {len(unique_dogs)} unique dogs from Doodle Dandy")
    return unique_dogs
  
  def _scrape_page(self, url: str, status: str) -> List[Dog]:
    """Scrape a listing page"""
    dogs = []
    soup = self.fetch_page(url)
    
    if not soup:
      return dogs
    
    # Extract image URLs from the structured links
    # Each dog card has: <a href="/all-adoptable-doodles/{slug}"><wow-image><img src="..."></wow-image></a>
    image_urls = self._extract_images(soup, url)
    
    # Get all text content for parsing dog info
    text = soup.get_text(separator="\n", strip=True)
    
    # Parse dog cards from text
    dogs = self._parse_dog_cards(text, status, image_urls)
    
    return dogs
  
  def _extract_images(self, soup: BeautifulSoup, page_url: str) -> dict:
    """
    Extract dog images from Wix gallery structure.
    Returns dict mapping lowercase dog names to image URLs.
    
    Structure:
    <a href="/all-adoptable-doodles/{slug}">
      <wow-image>
        <img alt="{DogName}" src="https://static.wixstatic.com/...">
      </wow-image>
    </a>
    """
    images = {}
    
    # Determine the base path based on page URL
    # e.g., /all-adoptable-doodles, /adoption-pending-doodles, /doodles-coming-soon
    base_paths = [
      "/all-adoptable-doodles/",
      "/adoption-pending-doodles/",
      "/doodles-coming-soon/"
    ]
    
    # Find all links that point to individual dog pages
    for a_tag in soup.find_all("a", href=True):
      href = a_tag.get("href", "")
      
      # Check if this is a dog profile link
      is_dog_link = False
      for base in base_paths:
        if base in href and href != base.rstrip("/"):
          is_dog_link = True
          break
      
      if not is_dog_link:
        continue
      
      # Extract the slug (dog name) from the URL
      slug = href.rstrip("/").split("/")[-1].lower()
      if not slug or len(slug) < 2:
        continue
      
      # Find the image inside this link
      img = a_tag.find("img")
      if img:
        src = img.get("src", "") or img.get("data-src", "")
        alt = img.get("alt", "").strip()
        
        if src and "wixstatic" in src:
          # Upgrade to larger image size
          src = re.sub(r"/v1/fill/w_\d+,h_\d+", "/v1/fill/w_400,h_400", src)
          
          # Map by slug
          images[slug] = src
          
          # Also map by cleaned alt text
          if alt:
            alt_clean = re.sub(r"[^a-z]", "", alt.lower())
            if alt_clean:
              images[alt_clean] = src
          
          print(f"  📸 Found image for: {slug}")
    
    # Also look for wow-image elements that might have data-image-info
    for wow in soup.find_all("wow-image"):
      img = wow.find("img")
      if img:
        src = img.get("src", "") or img.get("data-src", "")
        alt = img.get("alt", "").strip()
        
        if src and alt and "wixstatic" in src:
          # Upgrade size
          src = re.sub(r"/v1/fill/w_\d+,h_\d+", "/v1/fill/w_400,h_400", src)
          alt_clean = re.sub(r"[^a-z]", "", alt.lower())
          if alt_clean and alt_clean not in images:
            images[alt_clean] = src
    
    print(f"  📸 Total images found: {len(images)}")
    return images
  
  def _parse_dog_cards(self, text: str, status: str, image_urls: dict = None) -> List[Dog]:
    """
    Parse dog info from structured text.
    
    Format is typically:
      Name
      Breed (contains 'doodle', 'poo', etc.)
      Age (contains 'yr', 'mos', 'wks')
      Sex (Male/Female)
      Weight (contains 'lbs')
      Location (HOU, DFW, AUS, SA)
    """
    dogs = []
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    image_urls = image_urls or {}
    
    # Words/patterns to skip (not dog names)
    skip_patterns = [
      r"\.jpg$", r"\.png$", r"\.gif$",  # Image files
      r"^img[_-]", r"^frame\s*\d", r"^profile",  # Image prefixes
      r"^facebook$", r"^instagram$", r"^tiktok$", r"^youtube$",  # Social
      r"^doodle dandy", r"^welcome", r"^here are", r"^our policy",  # Headers
      r"^adoption", r"^please", r"^follow", r"^in foster",  # Instructions
      r"^sheds?:", r"^area:", r"^fee:",  # Labels
      r"^\d+$",  # Just numbers
      r"^applications? closed",  # Status text
    ]
    
    # Valid breeds
    breed_patterns = [
      r"doodle", r"poo\b", r"poodle", r"bernedoodle", r"goldendoodle",
      r"labradoodle", r"aussiedoodle", r"sheepadoodle", r"maltipoo",
      r"cockapoo", r"shih-?poo", r"cavapoo"
    ]
    
    # Location codes
    locations = ["HOU", "DFW", "AUS", "SA", "ATX", "SATX"]
    
    i = 0
    while i < len(lines):
      line = lines[i]
      
      # Skip if matches skip patterns
      if any(re.search(p, line.lower()) for p in skip_patterns):
        i += 1
        continue
      
      # Check if this could be a dog name (not a breed, age, weight, etc.)
      is_breed = any(re.search(p, line.lower()) for p in breed_patterns)
      is_age = re.search(r"\d+\s*(yr|mos|wks|mo|wk|year|month|week)", line.lower())
      is_weight = re.search(r"\d+\s*lbs?", line.lower())
      is_sex = line.lower() in ["male", "female"]
      is_location = line.upper() in locations
      
      # If this line looks like a name (not breed/age/weight/sex/location)
      if not is_breed and not is_age and not is_weight and not is_sex and not is_location:
        # Check if next lines form a dog card
        dog_data = self._try_parse_dog_card(lines, i)
        
        if dog_data:
          # Try to find matching image
          name_key = re.sub(r"[^a-z]", "", dog_data["name"].lower())
          dog_data["image_url"] = image_urls.get(name_key, "")
          
          dog = self._create_dog(dog_data, status)
          if dog:
            dogs.append(dog)
            print(f"  🐕 {dog.dog_name}: {dog.weight or '?'}lbs, {dog.age_range} | Fit: {dog.fit_score} | {status}")
          # Skip past the lines we just parsed
          i += dog_data.get("lines_consumed", 1)
          continue
      
      i += 1
    
    return dogs
  
  def _try_parse_dog_card(self, lines: List[str], start_idx: int) -> Optional[dict]:
    """
    Try to parse a dog card starting at given index.
    Returns dict with dog data if successful, None otherwise.
    """
    if start_idx >= len(lines):
      return None
    
    name = lines[start_idx]
    
    # Name validation
    if len(name) < 2 or len(name) > 40:
      return None
    
    # Skip if name looks like junk
    if re.search(r"\.(jpg|png|gif|jpeg)$", name.lower()):
      return None
    if name.lower() in ["male", "female", "hou", "dfw", "aus", "sa"]:
      return None
    
    data = {
      "name": name,
      "breed": "",
      "age": "",
      "sex": "",
      "weight": None,
      "location": "",
      "lines_consumed": 1
    }
    
    # Look at next 5 lines for dog attributes
    breed_found = False
    for j in range(1, min(6, len(lines) - start_idx)):
      line = lines[start_idx + j]
      line_lower = line.lower()
      
      # Check for breed
      if not breed_found and any(re.search(p, line_lower) for p in 
          [r"doodle", r"poo\b", r"poodle", r"maltipoo", r"shih-?poo", r"cavapoo"]):
        data["breed"] = line
        breed_found = True
        data["lines_consumed"] = j + 1
      
      # Check for age
      elif re.search(r"^\d+\.?\d*\s*(yr|mos|wks|mo|wk|years?|months?|weeks?)s?$", line_lower):
        data["age"] = line
        data["lines_consumed"] = j + 1
      
      # Check for sex
      elif line_lower in ["male", "female"]:
        data["sex"] = line.capitalize()
        data["lines_consumed"] = j + 1
      
      # Check for weight
      elif re.search(r"^\d+\s*lbs?$", line_lower):
        match = re.search(r"(\d+)", line)
        if match:
          data["weight"] = int(match.group(1))
        data["lines_consumed"] = j + 1
      
      # Check for location
      elif line.upper() in ["HOU", "DFW", "AUS", "SA", "ATX", "SATX"]:
        data["location"] = line.upper()
        data["lines_consumed"] = j + 1
      
      # If we hit another potential name (no match), stop
      elif len(line) > 2 and not any(c.isdigit() for c in line):
        # Might be next dog's name
        if breed_found:  # We got at least a breed, this is valid
          break
    
    # Only return if we found at least a breed (indicates this is a real dog entry)
    if breed_found:
      return data
    
    return None
  
  def _create_dog(self, data: dict, status: str) -> Optional[Dog]:
    """Create Dog object from parsed data"""
    name = data["name"]
    
    # Clean up name
    name = re.sub(r"\s*-\s*applications?\s*closed", "", name, flags=re.IGNORECASE)
    name = name.strip()
    
    if not name or len(name) < 2:
      return None
    
    # Parse age into category
    age_str = data.get("age", "")
    age_category = self._categorize_age(age_str)
    
    # Determine shedding based on breed
    breed = data.get("breed", "")
    shedding = self._guess_shedding(breed)
    
    dog = Dog(
      dog_id=self.create_dog_id(name),
      dog_name=name,
      rescue_name=self.rescue_name,
      breed=breed,
      weight=data.get("weight"),
      age_range=age_str,
      age_category=age_category,
      sex=data.get("sex", ""),
      shedding=shedding,
      energy_level=self._guess_energy(age_str, breed),
      good_with_kids="Unknown",
      good_with_dogs="Unknown",
      good_with_cats="Unknown",
      platform=self.platform,
      location=data.get("location", self.location),
      status=status,
      image_url=data.get("image_url", ""),
      date_collected=get_current_date()
    )
    
    # Calculate fit score
    dog.fit_score = calculate_fit_score(dog)
    dog.watch_list = check_watch_list(dog)
    
    return dog
  
  def _categorize_age(self, age_str: str) -> str:
    """Categorize age into Puppy/Adult/Senior"""
    if not age_str:
      return ""
    
    age_lower = age_str.lower()
    
    # Check for weeks/months (puppy)
    if "wk" in age_lower or "week" in age_lower:
      return "Puppy"
    if "mo" in age_lower or "month" in age_lower:
      match = re.search(r"(\d+)", age_str)
      if match:
        months = int(match.group(1))
        if months < 12:
          return "Puppy"
        else:
          return "Adult"
      return "Puppy"
    
    # Check for years
    if "yr" in age_lower or "year" in age_lower:
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
  
  def _guess_shedding(self, breed: str) -> str:
    """Guess shedding level based on breed"""
    breed_lower = breed.lower()
    
    # Poodle mixes are typically low/no shedding
    if "poodle" in breed_lower or "doodle" in breed_lower or "poo" in breed_lower:
      return "Low"
    
    return "Unknown"
  
  def _guess_energy(self, age_str: str, breed: str) -> str:
    """Guess energy level based on age and breed"""
    # Puppies are typically high energy
    if self._categorize_age(age_str) == "Puppy":
      return "High"
    
    # Seniors are typically lower energy
    if self._categorize_age(age_str) == "Senior":
      return "Low"
    
    # Default for doodles is medium
    return "Medium"
