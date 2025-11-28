"""
Scraper for Poodle Patch Rescue (Texarkana, TX)
WordPress-based site - more static HTML friendly
"""
import re
from typing import List, Optional
from bs4 import BeautifulSoup
from scrapers.base_scraper import BaseScraper
from models import Dog, get_current_date
from scoring import calculate_fit_score, check_watch_list


class PoodlePatchScraper(BaseScraper):
  """Scraper for poodlepatchrescue.com"""
  
  def __init__(self, config: dict):
    super().__init__("Poodle Patch Rescue", config)
    self.platform = "poodlepatchrescue.com"
    self.location = config.get("location", "Texarkana, TX")
  
  def scrape(self) -> List[Dog]:
    """Scrape all dogs from Poodle Patch Rescue"""
    dogs = []
    
    # Scrape adoptable pets category page
    available_url = self.config.get("available_url")
    if available_url:
      print(f"\n🐩 Scraping Poodle Patch - Available Dogs")
      dogs.extend(self._scrape_listing_page(available_url, "Available"))
    
    # Also check the animals page
    animals_url = self.config.get("animals_url")
    if animals_url and animals_url != available_url:
      print(f"\n🐩 Scraping Poodle Patch - Animals Page")
      dogs.extend(self._scrape_listing_page(animals_url, "Available"))
    
    # Deduplicate by dog_id
    seen = set()
    unique_dogs = []
    for dog in dogs:
      if dog.dog_id not in seen:
        seen.add(dog.dog_id)
        unique_dogs.append(dog)
    
    print(f"  ✅ Found {len(unique_dogs)} unique dogs from Poodle Patch")
    return unique_dogs
  
  def _scrape_listing_page(self, url: str, status: str) -> List[Dog]:
    """Scrape a listing page and follow links to individual dog pages"""
    dogs = []
    soup = self.fetch_page(url)
    
    if not soup:
      return dogs
    
    # Build a map of dog URLs to their thumbnail images from the listing page
    # The listing page has articles with post-img-wrap containing the thumbnail
    image_map = {}
    
    for article in soup.find_all("article", class_=re.compile(r"post")):
      # Find the dog page link
      title_link = article.find("h1", class_="entry-title")
      if title_link:
        a_tag = title_link.find("a", href=True)
        if a_tag:
          dog_url = a_tag["href"]
          
          # Find the thumbnail image in post-img-wrap
          img_wrap = article.find("div", class_="post-img-wrap")
          if img_wrap:
            img = img_wrap.find("img")
            if img:
              # Get the best resolution image from srcset or src
              srcset = img.get("srcset", "")
              src = img.get("src", "")
              
              # Parse srcset to get largest image
              if srcset:
                # srcset format: "url1 250w, url2 400w, url3 600w"
                best_url = src
                best_size = 0
                for part in srcset.split(","):
                  part = part.strip()
                  if " " in part:
                    img_url, size_str = part.rsplit(" ", 1)
                    size = int(re.sub(r"[^\d]", "", size_str) or 0)
                    if size > best_size:
                      best_size = size
                      best_url = img_url.strip()
                image_map[dog_url] = best_url
              elif src:
                image_map[dog_url] = src
    
    # Also try finding images via the post-img-wrap > a structure
    for img_wrap in soup.find_all("div", class_="post-img-wrap"):
      a_tag = img_wrap.find("a", href=True)
      if a_tag:
        dog_url = a_tag["href"]
        img = img_wrap.find("img")
        if img and dog_url not in image_map:
          srcset = img.get("srcset", "")
          src = img.get("src", "")
          
          if srcset:
            best_url = src
            best_size = 0
            for part in srcset.split(","):
              part = part.strip()
              if " " in part:
                img_url, size_str = part.rsplit(" ", 1)
                size = int(re.sub(r"[^\d]", "", size_str) or 0)
                if size > best_size:
                  best_size = size
                  best_url = img_url.strip()
            image_map[dog_url] = best_url
          elif src:
            image_map[dog_url] = src
    
    print(f"  📸 Found {len(image_map)} dog images on listing page")
    
    # Now get unique dog URLs
    dog_links = set()
    for link in soup.find_all("a", href=True):
      href = link["href"]
      if re.match(r"https?://poodlepatchrescue\.com/[a-zA-Z0-9-]+/?$", href):
        excluded = ["about-us", "application", "contact", "category", 
                    "our-animals", "adoptable-pets", "donate", "foster",
                    "happy-tails", "author", "tag", "page"]
        slug = href.rstrip("/").split("/")[-1].lower()
        if slug not in excluded and not any(ex in href for ex in excluded):
          dog_links.add(href)
    
    print(f"  🔗 Found {len(dog_links)} potential dog pages")
    
    # Scrape each individual dog page, passing the image URL
    for dog_url in dog_links:
      image_url = image_map.get(dog_url, "")
      dog = self._scrape_dog_page(dog_url, status, image_url)
      if dog:
        dogs.append(dog)
    
    return dogs
  
  def _scrape_dog_page(self, url: str, status: str, listing_image_url: str = "") -> Optional[Dog]:
    """Scrape individual dog profile page"""
    soup = self.fetch_page(url)
    if not soup:
      return None
    
    # Get dog name from title or h1
    name = ""
    title = soup.find("title")
    if title:
      name = title.get_text().split("-")[0].split("|")[0].strip()
    
    if not name:
      h1 = soup.find("h1")
      if h1:
        name = h1.get_text().strip()
    
    if not name:
      print(f"  ⚠️ Could not find dog name at {url}")
      return None
    
    # Clean up name - remove rescue suffix that sometimes appears
    name = re.sub(r"\s*[-–—]\s*Poodle Patch Rescue.*$", "", name, flags=re.IGNORECASE)
    name = name.strip()
    
    # Get description/bio text
    bio = ""
    content_div = soup.find("div", class_=re.compile(r"entry-content|post-content|content"))
    if content_div:
      bio = content_div.get_text(separator=" ", strip=True)
    else:
      # Try main content area
      main = soup.find("main") or soup.find("article")
      if main:
        bio = main.get_text(separator=" ", strip=True)
    
    # Use image from listing page (preferred - it's the actual dog photo)
    # Only fall back to page extraction if we don't have one
    image_url = listing_image_url
    if not image_url:
      image_url = self._extract_image(soup)
    
    # Parse attributes from bio text
    weight = self._extract_weight_from_text(bio)
    age = self._extract_age_from_text(bio)
    sex = self._extract_sex_from_text(bio)
    good_with_dogs = self._extract_compatibility(bio, "dogs")
    good_with_cats = self._extract_compatibility(bio, "cats")
    good_with_kids = self._extract_compatibility(bio, "kids")
    special_needs = self._detect_special_needs(bio)
    adoption_fee = self._extract_adoption_fee(bio)
    
    # Create dog object
    dog = Dog(
      dog_id=self.create_dog_id(name),
      dog_name=name,
      rescue_name=self.rescue_name,
      breed=self._guess_breed(bio),
      weight=weight,
      age_range=age,
      age_category=self._categorize_age(age),
      sex=sex,
      shedding=self._guess_shedding(bio),
      energy_level=self._extract_energy(bio),
      good_with_kids=good_with_kids,
      good_with_dogs=good_with_dogs,
      good_with_cats=good_with_cats,
      special_needs=special_needs,
      health_notes=self._extract_health_notes(bio),
      adoption_req=self._extract_requirements(bio),
      adoption_fee=adoption_fee,
      platform=self.platform,
      location=self.location,
      status=status,
      notes=bio[:500] if bio else "",  # First 500 chars of bio
      source_url=url,
      image_url=image_url,
      date_collected=get_current_date()
    )
    
    # Calculate fit score and check watch list
    dog.fit_score = calculate_fit_score(dog)
    dog.watch_list = check_watch_list(dog)
    
    print(f"  🐕 {name}: {weight or '?'}lbs | Fit: {dog.fit_score} | {status}")
    return dog
  
  def _extract_image(self, soup: BeautifulSoup) -> str:
    """Extract primary dog image from page"""
    # Try featured image first (WordPress)
    featured = soup.find("img", class_=re.compile(r"wp-post-image|featured|attachment"))
    if featured:
      src = featured.get("src", "") or featured.get("data-src", "")
      if src:
        return src
    
    # Try Open Graph image
    og_image = soup.find("meta", property="og:image")
    if og_image and og_image.get("content"):
      return og_image["content"]
    
    # Try first large image in content area
    content = soup.find("div", class_=re.compile(r"entry-content|post-content|content"))
    if content:
      for img in content.find_all("img"):
        src = img.get("src", "") or img.get("data-src", "")
        # Skip tiny images (likely icons)
        width = img.get("width", "")
        if width and width.isdigit() and int(width) < 100:
          continue
        if src and not any(skip in src.lower() for skip in ["icon", "logo", "button", "avatar"]):
          return src
    
    # Fallback: first reasonable image on page
    for img in soup.find_all("img"):
      src = img.get("src", "") or img.get("data-src", "")
      if src and not any(skip in src.lower() for skip in ["icon", "logo", "button", "avatar", "widget"]):
        return src
    
    return ""
  
  def _extract_weight_from_text(self, text: str) -> Optional[int]:
    """Extract weight from bio text"""
    patterns = [
      r"weighs?\s*(\d+)\s*(?:lbs?|pounds?)",
      r"(\d+)\s*(?:lbs?|pounds?)",
      r"weight[:\s]+(\d+)"
    ]
    for pattern in patterns:
      match = re.search(pattern, text.lower())
      if match:
        return int(match.group(1))
    return None
  
  def _extract_age_from_text(self, text: str) -> str:
    """Extract age from bio text"""
    patterns = [
      r"(\d+)\s*(?:years?|yrs?)\s*old",
      r"age[:\s]+(\d+)",
      r"(\d+)\s*(?:months?|mos?)\s*old"
    ]
    for pattern in patterns:
      match = re.search(pattern, text.lower())
      if match:
        num = match.group(1)
        if "month" in pattern:
          return f"{num} months"
        return f"{num} years"
    return ""
  
  def _extract_sex_from_text(self, text: str) -> str:
    """Extract sex from bio text"""
    text_lower = text.lower()
    if re.search(r"\b(female|girl|she|her|spayed)\b", text_lower):
      return "Female"
    elif re.search(r"\b(male|boy|he|him|neutered)\b", text_lower):
      return "Male"
    return ""
  
  def _extract_compatibility(self, text: str, animal_type: str) -> str:
    """Extract compatibility info"""
    text_lower = text.lower()
    
    # Positive indicators
    positive = [
      f"good with {animal_type}",
      f"great with {animal_type}",
      f"loves {animal_type}",
      f"gets along with.*{animal_type}",
      f"friendly with {animal_type}",
      f"ok with {animal_type}"
    ]
    
    # Negative indicators
    negative = [
      f"no {animal_type}",
      f"not good with {animal_type}",
      f"doesn't like {animal_type}",
      f"can't be with {animal_type}"
    ]
    
    for pattern in positive:
      if re.search(pattern, text_lower):
        return "Yes"
    
    for pattern in negative:
      if re.search(pattern, text_lower):
        return "No"
    
    return "Unknown"
  
  def _detect_special_needs(self, text: str) -> str:
    """Detect if dog has special needs"""
    indicators = [
      "special needs", "medical", "medication", "ongoing treatment",
      "blind", "deaf", "diabetic", "seizure", "heart condition",
      "requires", "needs daily", "chronic"
    ]
    text_lower = text.lower()
    for indicator in indicators:
      if indicator in text_lower:
        return "Yes"
    return "No"
  
  def _extract_adoption_fee(self, text: str) -> str:
    """Extract adoption fee"""
    match = re.search(r"adoption\s*fee[:\s]*\$?(\d+)", text.lower())
    if match:
      return f"${match.group(1)}"
    match = re.search(r"\$(\d+)\s*(?:adoption|fee)", text.lower())
    if match:
      return f"${match.group(1)}"
    return ""
  
  def _guess_breed(self, text: str) -> str:
    """Guess breed from bio text"""
    breeds = [
      "poodle", "goldendoodle", "labradoodle", "bernedoodle",
      "aussiedoodle", "sheepadoodle", "poodle mix", "doodle"
    ]
    text_lower = text.lower()
    found = []
    for breed in breeds:
      if breed in text_lower:
        found.append(breed.title())
    return ", ".join(found) if found else "Poodle/Mix"
  
  def _guess_shedding(self, text: str) -> str:
    """Guess shedding level from breed/description"""
    text_lower = text.lower()
    if "non-shedding" in text_lower or "doesn't shed" in text_lower:
      return "None"
    if "low shedding" in text_lower or "minimal shedding" in text_lower:
      return "Low"
    # Poodles and doodles typically low/no shedding
    if "poodle" in text_lower:
      return "Low"
    return "Unknown"
  
  def _extract_energy(self, text: str) -> str:
    """Extract energy level"""
    text_lower = text.lower()
    if any(w in text_lower for w in ["calm", "mellow", "laid back", "lazy", "couch potato"]):
      return "Low"
    if any(w in text_lower for w in ["high energy", "very active", "needs lots of exercise"]):
      return "High"
    if any(w in text_lower for w in ["moderate", "medium energy", "playful"]):
      return "Medium"
    return "Unknown"
  
  def _extract_health_notes(self, text: str) -> str:
    """Extract health-related notes"""
    health_keywords = [
      "vetted", "neutered", "spayed", "vaccinated", "microchipped",
      "heartworm", "health", "medical"
    ]
    notes = []
    for keyword in health_keywords:
      if keyword in text.lower():
        # Find the sentence containing this keyword
        sentences = text.split(".")
        for s in sentences:
          if keyword in s.lower():
            notes.append(s.strip())
            break
    return ". ".join(notes[:3])  # First 3 relevant notes
  
  def _extract_requirements(self, text: str) -> str:
    """Extract adoption requirements"""
    text_lower = text.lower()
    reqs = []
    
    # Distance requirement
    match = re.search(r"within\s*(\d+)\s*miles", text_lower)
    if match:
      reqs.append(f"Within {match.group(1)} miles")
    
    # Fence requirement
    if "fence" in text_lower:
      if "no fence" in text_lower or "fence not required" in text_lower:
        reqs.append("Fence not required")
      else:
        reqs.append("Fenced yard")
    
    return ", ".join(reqs) if reqs else ""
  
  def _categorize_age(self, age_str: str) -> str:
    """Categorize age into Puppy/Adult/Senior"""
    if not age_str:
      return ""
    
    if "month" in age_str.lower():
      return "Puppy"
    
    match = re.search(r"(\d+)", age_str)
    if match:
      years = int(match.group(1))
      if years < 2:
        return "Puppy"
      elif years >= 8:
        return "Senior"
      else:
        return "Adult"
    
    return ""
