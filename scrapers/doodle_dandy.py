"""
Scraper for Doodle Dandy Rescue (DFW/Houston/Austin/SA)
v3.0.0 - Better filtering of junk entries

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
    
    # Get all text content
    text = soup.get_text(separator="\n", strip=True)
    
    # Parse dog cards from text
    dogs = self._parse_dog_cards(text, status, url)
    
    return dogs
  
  def _is_valid_dog_name(self, name: str) -> bool:
    """Check if a string is a valid dog name (not junk)"""
    if not name or len(name) < 2 or len(name) > 30:
      return False
    
    name_lower = name.lower().strip()
    
    # Explicit junk entries to skip
    junk_names = [
      "more", "load more", "blog", "home", "about", "contact",
      "facebook", "instagram", "tiktok", "youtube", "twitter",
      "foster family", "foster", "adoption", "adopt", "apply",
      "our policies", "policies and procedures", "please make sure",
      "read", "click", "here", "learn more", "view", "see",
      "doodle dandy", "rescue", "available", "pending", "upcoming",
      "no", "yes", "unknown", "male", "female",
      "hou", "dfw", "aus", "sa", "atx", "satx",
      "submit", "application", "form", "email", "phone",
      "donate", "volunteer", "sponsor", "events", "news",
      "privacy", "terms", "copyright", "menu", "close",
      "next", "previous", "back", "forward", "search"
    ]
    
    # Check exact matches
    if name_lower in junk_names:
      return False
    
    # Check if name contains junk phrases
    junk_phrases = [
      "make sure", "click here", "learn more", "read more",
      "load more", "view all", "see all", "our policies",
      "policies and procedures", "foster family", "please"
    ]
    for phrase in junk_phrases:
      if phrase in name_lower:
        return False
    
    # Skip if it's just a number
    if name.isdigit():
      return False
    
    # Skip if it looks like a file extension
    if re.search(r'\.(jpg|png|gif|pdf|doc)$', name_lower):
      return False
    
    # Skip if it starts with common junk patterns
    junk_starts = ["img", "image", "photo", "pic", "frame", "profile", "logo", "icon", "banner"]
    for start in junk_starts:
      if name_lower.startswith(start):
        return False
    
    # Name should start with a letter
    if not name[0].isalpha():
      return False
    
    # Should be mostly letters (allow spaces, apostrophes, hyphens)
    alpha_count = sum(1 for c in name if c.isalpha())
    if alpha_count < len(name) * 0.7:
      return False
    
    return True
  
  def _parse_dog_cards(self, text: str, status: str, page_url: str) -> List[Dog]:
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
    
    # Valid breed patterns
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
      
      # Check if this could be a dog name
      is_breed = any(re.search(p, line.lower()) for p in breed_patterns)
      is_age = re.search(r"\d+\s*(yr|mos|wks|mo|wk|year|month|week)", line.lower())
      is_weight = re.search(r"\d+\s*lbs?", line.lower())
      is_sex = line.lower() in ["male", "female"]
      is_location = line.upper() in locations
      
      # If this line looks like a name (not breed/age/weight/sex/location)
      if not is_breed and not is_age and not is_weight and not is_sex and not is_location:
        # Validate it's a real dog name
        if self._is_valid_dog_name(line):
          # Check if next lines form a dog card
          dog_data = self._try_parse_dog_card(lines, i, breed_patterns, locations)
          
          if dog_data:
            dog = self._create_dog(dog_data, status, page_url)
            if dog:
              dogs.append(dog)
              print(f"  🐕 {dog.dog_name}: {dog.weight or '?'}lbs, {dog.age_range} | Fit: {dog.fit_score} | {status}")
            # Skip past the lines we just parsed
            i += dog_data.get("lines_consumed", 1)
            continue
      
      i += 1
    
    return dogs
  
  def _try_parse_dog_card(self, lines: List[str], start_idx: int, 
                          breed_patterns: List[str], locations: List[str]) -> Optional[dict]:
    """
    Try to parse a dog card starting at given index.
    Returns dict with dog data if successful, None otherwise.
    """
    if start_idx >= len(lines):
      return None
    
    name = lines[start_idx]
    
    # Double-check name validity
    if not self._is_valid_dog_name(name):
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
      if not breed_found and any(re.search(p, line_lower) for p in breed_patterns):
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
      elif line.upper() in locations:
        data["location"] = line.upper()
        data["lines_consumed"] = j + 1
      
      # If we hit another valid name, stop
      elif self._is_valid_dog_name(line) and breed_found:
        break
    
    # Only return if we found at least a breed (indicates this is a real dog entry)
    if breed_found:
      return data
    
    return None
  
  def _create_dog(self, data: dict, status: str, page_url: str) -> Optional[Dog]:
    """Create Dog object from parsed data"""
    name = data["name"]
    
    # Clean up name
    name = re.sub(r"\s*-\s*applications?\s*closed", "", name, flags=re.IGNORECASE)
    name = name.strip()
    
    # Final validation
    if not self._is_valid_dog_name(name):
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
      source_url=page_url,
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
