"""
Scraper for Doodle Dandy Rescue (DFW/Houston/Austin/SA)
v3.2.0 - Fixed Load More detection + block junk names + thorough scrolling

Changes in v3.2.0:
- Fixed Load More detection to stop when no new dogs load (was clicking 25x pointlessly)
- Added "Austin", "More", "Load More", "Gallery", "SAN" to skip patterns (were being picked up as dog names)
- Added thorough scrolling to trigger lazy-loaded Wix gallery content
- More specific Load More button detection (exact text match, not contains)

The site is Wix-based and uses a "Load More" button to paginate dogs.
This scraper uses Playwright to click the button and load all dogs.

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
    
    # Determine if Playwright is available
    use_playwright = self._playwright_available()
    if use_playwright:
      print("  🎭 Using Playwright for JS rendering + Load More handling")
    else:
      print("  ⚠️ Playwright not available - using basic fetch (may miss dogs behind Load More)")
    
    # Available dogs
    available_url = self.config.get("available_url")
    if available_url:
      print(f"\n🐩 Scraping Doodle Dandy - Available Dogs")
      if use_playwright:
        dogs.extend(self._scrape_with_playwright(available_url, "Available"))
      else:
        dogs.extend(self._scrape_page(available_url, "Available"))
    
    # Pending dogs
    pending_url = self.config.get("pending_url")
    if pending_url:
      print(f"\n🐩 Scraping Doodle Dandy - Pending Dogs")
      if use_playwright:
        dogs.extend(self._scrape_with_playwright(pending_url, "Pending"))
      else:
        dogs.extend(self._scrape_page(pending_url, "Pending"))
    
    # Upcoming/foster dogs
    upcoming_url = self.config.get("upcoming_url")
    if upcoming_url:
      print(f"\n🐩 Scraping Doodle Dandy - Coming Soon")
      if use_playwright:
        dogs.extend(self._scrape_with_playwright(upcoming_url, "Upcoming"))
      else:
        dogs.extend(self._scrape_page(upcoming_url, "Upcoming"))
    
    # Deduplicate by dog_id
    seen = set()
    unique_dogs = []
    for dog in dogs:
      if dog.dog_id not in seen:
        seen.add(dog.dog_id)
        unique_dogs.append(dog)
    
    # Print summary of all dogs found
    print(f"\n  ✅ Found {len(unique_dogs)} unique dogs from Doodle Dandy")
    print(f"  📋 Dogs list:")
    for dog in unique_dogs:
      status_emoji = "🟢" if dog.status == "Available" else "🟡" if dog.status == "Upcoming" else "🔴"
      img_emoji = "📷" if dog.image_url else "  "
      print(f"    {status_emoji} {img_emoji} {dog.dog_name} ({dog.breed}, {dog.weight or '?'}lbs) - {dog.status}")
    
    return unique_dogs
  
  def _playwright_available(self) -> bool:
    """Check if Playwright is available"""
    try:
      from playwright.sync_api import sync_playwright
      return True
    except ImportError:
      return False
  
  def _scrape_with_playwright(self, url: str, status: str) -> List[Dog]:
    """
    Scrape using Playwright for full JS rendering and Load More button handling.
    Clicks the Load More button repeatedly until all dogs are loaded.
    """
    dogs = []
    
    try:
      from playwright.sync_api import sync_playwright
      
      with sync_playwright() as p:
        # Launch browser
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        print(f"  🔍 Fetching: {url}")
        page.goto(url, wait_until="networkidle", timeout=60000)
        
        # Wait for initial content to load
        page.wait_for_timeout(2000)
        
        # Count initial dogs visible
        initial_count = page.evaluate("""
          () => {
            // Count wixstatic images that are likely dog photos
            const imgs = document.querySelectorAll('img[src*="wixstatic"]');
            let count = 0;
            for (const img of imgs) {
              const src = img.src || '';
              // Skip small images (icons)
              if (src.includes('w_') && src.includes('h_')) {
                const match = src.match(/w_(\\d+)/);
                if (match && parseInt(match[1]) >= 100) count++;
              }
            }
            return count;
          }
        """)
        print(f"    ↳ Initial dog images visible: {initial_count}")
        
        # Click "Load More" button repeatedly until all dogs are loaded
        load_more_clicks = 0
        max_clicks = 15  # Reasonable limit
        last_count = initial_count
        no_change_count = 0
        
        while load_more_clicks < max_clicks:
          # Use JavaScript to find and click Load More button
          # Be more specific: look for Wix gallery load more buttons
          clicked = page.evaluate("""
            () => {
              // Wix sites often use specific patterns for Load More
              // Look for elements with exact "Load More" text
              const loadMoreTexts = ['load more', 'show more'];
              
              // Method 1: Look for buttons with Load More text
              const buttons = document.querySelectorAll('button, [role="button"], [data-testid*="load"], [data-testid*="more"]');
              for (const btn of buttons) {
                const text = (btn.textContent || '').toLowerCase().trim();
                if (loadMoreTexts.some(t => text === t) && btn.offsetParent !== null) {
                  btn.click();
                  return 'button';
                }
              }
              
              // Method 2: Look for Wix-specific gallery load more
              const wixLoadMore = document.querySelector('[data-hook="load-more-button"], .load-more-button, [class*="loadMore"]');
              if (wixLoadMore && wixLoadMore.offsetParent !== null) {
                wixLoadMore.click();
                return 'wix-hook';
              }
              
              // Method 3: Look for clickable spans/divs with EXACT "Load More" text
              const allElements = document.querySelectorAll('span, div, a, p');
              for (const el of allElements) {
                const text = (el.textContent || '').toLowerCase().trim();
                // Must be EXACT match or very close, not just contains
                if ((text === 'load more' || text === 'show more') && el.offsetParent !== null) {
                  const style = window.getComputedStyle(el);
                  if (style.cursor === 'pointer' || el.onclick) {
                    el.click();
                    return 'span-exact';
                  }
                }
              }
              
              return false;
            }
          """)
          
          if clicked:
            load_more_clicks += 1
            print(f"    ↳ Clicked Load More (#{load_more_clicks}) via {clicked}")
            # Wait for new content to load
            page.wait_for_timeout(2000)
            
            # Check if dog count increased
            new_count = page.evaluate("""
              () => {
                const imgs = document.querySelectorAll('img[src*="wixstatic"]');
                let count = 0;
                for (const img of imgs) {
                  const src = img.src || '';
                  if (src.includes('w_') && src.includes('h_')) {
                    const match = src.match(/w_(\\d+)/);
                    if (match && parseInt(match[1]) >= 100) count++;
                  }
                }
                return count;
              }
            """)
            
            if new_count > last_count:
              print(f"    ↳ Dogs increased: {last_count} → {new_count}")
              last_count = new_count
              no_change_count = 0
            else:
              no_change_count += 1
              if no_change_count >= 2:
                print(f"    ↳ No new dogs after {no_change_count} clicks, stopping")
                break
          else:
            # No more Load More button - all dogs loaded
            if load_more_clicks == 0:
              print(f"    ↳ No Load More button found on this page")
            else:
              print(f"    ↳ All content loaded")
            break
        
        if load_more_clicks > 0:
          print(f"    ✅ Clicked Load More {load_more_clicks} time(s)")
        
        # Thorough scrolling to trigger ALL lazy-loaded content
        # Wix galleries often lazy-load as you scroll
        print(f"    ↳ Scrolling through page to trigger lazy loading...")
        page.evaluate("""
          async () => {
            const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
            const height = document.body.scrollHeight;
            const step = window.innerHeight / 2;
            
            // Scroll down in steps
            for (let y = 0; y < height; y += step) {
              window.scrollTo(0, y);
              await delay(300);
            }
            
            // Scroll to bottom and wait
            window.scrollTo(0, document.body.scrollHeight);
            await delay(500);
            
            // Scroll back up in steps (sometimes triggers more loading)
            for (let y = document.body.scrollHeight; y >= 0; y -= step) {
              window.scrollTo(0, y);
              await delay(200);
            }
            
            window.scrollTo(0, 0);
          }
        """)
        page.wait_for_timeout(1500)
        
        # Count final dogs visible
        final_count = page.evaluate("""
          () => {
            const imgs = document.querySelectorAll('img[src*="wixstatic"]');
            let count = 0;
            for (const img of imgs) {
              const src = img.src || '';
              if (src.includes('w_') && src.includes('h_')) {
                const match = src.match(/w_(\\d+)/);
                if (match && parseInt(match[1]) >= 100) count++;
              }
            }
            return count;
          }
        """)
        print(f"    ↳ Final dog images visible: {final_count}")
        
        # Get final page content
        html = page.content()
        browser.close()
        
        # Parse with BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        
        # Extract images and parse dogs
        image_urls = self._extract_images(soup, url)
        text = soup.get_text(separator="\n", strip=True)
        dogs = self._parse_dog_cards(text, status, image_urls)
        
    except Exception as e:
      print(f"  ❌ Playwright error: {e}")
      # Fallback to basic fetch
      print(f"  ⚠️ Falling back to basic fetch")
      dogs = self._scrape_page(url, status)
    
    return dogs
  
  def _scrape_page(self, url: str, status: str) -> List[Dog]:
    """Scrape a listing page (basic fetch - may miss Load More content)"""
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
    
    Strategy: Find image+name pairs by looking at the DOM structure.
    Wix typically places image and name in adjacent/nearby elements.
    """
    images = {}
    
    # Determine the base path based on page URL
    base_paths = [
      "/all-adoptable-doodles/",
      "/adoption-pending-doodles/",
      "/doodles-coming-soon/"
    ]
    
    # Pattern 1: Find all links that point to individual dog pages (available/pending)
    for a_tag in soup.find_all("a", href=True):
      href = a_tag.get("href", "")
      
      is_dog_link = False
      for base in base_paths:
        if base in href and href != base.rstrip("/"):
          is_dog_link = True
          break
      
      if not is_dog_link:
        continue
      
      slug = href.rstrip("/").split("/")[-1].lower()
      if not slug or len(slug) < 2:
        continue
      
      img = a_tag.find("img")
      if img:
        src = img.get("src", "") or img.get("data-src", "")
        alt = img.get("alt", "").strip()
        
        if src and "wixstatic" in src:
          src = re.sub(r"/v1/fill/w_\d+,h_\d+", "/v1/fill/w_400,h_400", src)
          images[slug] = src
          
          if alt:
            alt_clean = re.sub(r"[^a-z]", "", alt.lower())
            if alt_clean:
              images[alt_clean] = src
    
    # Pattern 2: For coming-soon page - use SEQUENTIAL pairing
    # The page structure is: image1, name1, breed1, ..., image2, name2, breed2, ...
    # We need to extract images and names IN ORDER and pair them sequentially
    
    # First, collect all dog-sized images in DOM order
    all_dog_images = []
    for img in soup.find_all("img"):
      src = img.get("src", "") or img.get("data-src", "")
      
      if not src or "wixstatic" not in src:
        continue
      
      # Skip tiny icons and UI elements
      if any(skip in src.lower() for skip in ["logo", "icon", "button", "social", "arrow"]):
        continue
      
      # Check for size in URL (wix uses w_NNN,h_NNN format)
      size_match = re.search(r"w_(\d+),h_(\d+)", src)
      if size_match:
        w, h = int(size_match.group(1)), int(size_match.group(2))
        if w < 100 or h < 100:
          continue
      
      # Upgrade to larger size
      src = re.sub(r"/v1/fill/w_\d+,h_\d+", "/v1/fill/w_400,h_400", src)
      
      # Avoid duplicates (same image URL)
      if src not in all_dog_images:
        all_dog_images.append(src)
    
    # Now find dog names in order by looking for the Name/Breed/Age/Sex/Weight/Location pattern
    text = soup.get_text(separator="\n", strip=True)
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    
    breed_patterns = [r"doodle", r"poo\b", r"poodle", r"maltipoo", r"shih-?poo", r"cavapoo"]
    dog_names_in_order = []
    
    i = 0
    while i < len(lines):
      line = lines[i]
      
      # Skip if this looks like a breed, age, weight, sex, or location
      line_lower = line.lower()
      is_breed = any(re.search(p, line_lower) for p in breed_patterns)
      is_age = re.search(r"\d+\.?\d*\s*(yr|mos|wks|mo|wk|year|month|week)", line_lower)
      is_weight = re.search(r"^\d+\s*lbs?$", line_lower)
      is_sex = line_lower in ["male", "female"]
      is_location = line.upper() in ["HOU", "DFW", "AUS", "SA", "ATX", "SATX", "AUSTIN", "HOUSTON", "DALLAS", "SAN ANTONIO"]
      
      # Skip navigation/UI text
      skip_words = ["adopt", "foster", "home", "about", "contact", "facebook", "instagram", 
                    "application", "policy", "welcome", "rescue", "available", "pending", 
                    "coming soon", "read more", "view", "click", "copyright", "fur-ever"]
      is_skip = any(sw in line_lower for sw in skip_words) and len(line) < 50
      
      if not is_breed and not is_age and not is_weight and not is_sex and not is_location and not is_skip:
        # Check if NEXT line is a breed (strong indicator this is a dog name)
        if i + 1 < len(lines):
          next_line = lines[i + 1].lower()
          if any(re.search(p, next_line) for p in breed_patterns):
            # This is likely a dog name
            name = line.strip()
            # Additional validation
            if (len(name) >= 2 and len(name) <= 30 and 
                not re.search(r"\.(jpg|png|gif|jpeg)$", name.lower()) and
                name.lower() not in ["male", "female"] and
                not re.search(r"^\d+", name)):  # Doesn't start with number
              dog_names_in_order.append(name)
      
      i += 1
    
    # Now pair images with names by position
    # Remove any already-matched names from Pattern 1
    already_matched = set(images.keys())
    
    image_idx = 0
    for name in dog_names_in_order:
      name_clean = re.sub(r"[^a-z]", "", name.lower())
      
      # Skip if already matched via Pattern 1
      if name_clean in already_matched:
        image_idx += 1  # Still advance image index
        continue
      
      if image_idx < len(all_dog_images):
        images[name_clean] = all_dog_images[image_idx]
        image_idx += 1
    
    print(f"  📸 Images mapped: {len(images)} (from {len(all_dog_images)} images, {len(dog_names_in_order)} names)")
    
    # Debug: show first few mappings
    for name, url in list(images.items())[:3]:
      short_url = url.split("/")[-1][:30] if url else "?"
      print(f"    → {name}: {short_url}...")
    
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
    
    # Debug: count potential dog names before filtering
    print(f"  📝 Text has {len(lines)} non-empty lines")
    
    # Words/patterns to skip (not dog names) - EXPANDED LIST
    skip_patterns = [
      # Image files
      r"\.jpg", r"\.png", r"\.gif", r"\.jpeg", r"\.webp",
      r"^img[_-]", r"^frame\s*\d", r"^profile", r"_edited",
      
      # Social media
      r"^facebook$", r"^instagram$", r"^tiktok$", r"^youtube$",
      
      # Navigation and headers
      r"^doodle dandy", r"^welcome", r"^here are", r"^our policy",
      r"^home$", r"^about", r"^contact", r"^blog$", r"^faq",
      r"^happy tails", r"^alumni", r"^foster", r"^donate",
      r"^apply", r"^application", r"^adopt$", r"^available",
      r"^pending", r"^coming soon", r"^upcoming",
      
      # Instructions and legal
      r"^adoption", r"^please", r"^follow", r"^in foster",
      r"^click", r"^read", r"^view", r"^see", r"^learn",
      r"copyright", r"all rights", r"privacy", r"terms",
      r"^our ", r"^the ", r"^this ", r"^that ", r"^these ",
      r"^be sure", r"^make sure", r"^don't forget",
      
      # Labels
      r"^sheds?:", r"^area:", r"^fee:", r"^energy:", r"^weight:",
      
      # Single words that aren't names
      r"^\d+$", r"^yes$", r"^no$", r"^some$", r"^none$",
      r"^low$", r"^medium$", r"^high$", r"^unknown$",
      
      # Status text
      r"^applications? closed", r"^currently", r"^status",
      
      # Common junk phrases
      r"policies and procedures", r"fur-ever", r"forever home",
      r"ready for adoption", r"doodles ready", r"rescue 20",
      r"full bio", r"right for you", r"oster family",
      
      # UI elements that get picked up as names
      r"^load\s*more$", r"^show\s*more$", r"^see\s*more$", r"^more$",
      r"^gallery$", r"^menu$", r"^search$", r"^filter",
      r"^sort", r"^back$", r"^next$", r"^prev",
      
      # Location names (these are NOT dog names!)
      r"^austin$", r"^houston$", r"^dallas$", r"^san\s*antonio$",
      r"^hou$", r"^dfw$", r"^aus$", r"^atx$", r"^satx$", r"^san$", r"^sa$",
      r"^texas$", r"^tx$",
      
      # Fill out form text
      r"^fill\s*out", r"form$", r"^how\s*our",
      
      # Site navigation/footer text that appears as fake dogs
      r"^rehome$", r"^community$", r"^copyright",
    ]
    
    # Valid breeds - expanded to catch all doodle/poo variations
    breed_patterns = [
      r"doodle", r"poo\b", r"poodle", r"bernedoodle", r"goldendoodle",
      r"labradoodle", r"aussiedoodle", r"sheepadoodle", r"maltipoo",
      r"cockapoo", r"shih-?poo", r"cavapoo", r"schnoodle", r"whoodle",
      r"bordoodle", r"newfypoo", r"pyredoodle", r"rottle", r"boxerdoodle",
      r"irish.?doodle", r"double.?doodle", r"mini.?doodle", r"standard.?poodle",
      r"toy.?poodle", r"mini.?poodle", r"bichpoo", r"yorkipoo", r"pomapoo",
      r"havapoo", r"corgipoo", r"eskipoo", r"bassetoodle", r"dalmadoodle",
      r"mountain.?doodle", r"australian.?mountain", r"f1b?\s", r"poo-", r"-poo",
      r"^poo", r"mix$"  # catch "Poo mix" or similar
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
      
      # Skip if line is too short or too long for a name
      if len(line) < 2 or len(line) > 25:
        i += 1
        continue
      
      # Skip if line has too many words (names are usually 1-2 words)
      word_count = len(line.split())
      if word_count > 3:
        i += 1
        continue
      
      # Skip if line contains numbers (except maybe a suffix like "2" or "II")
      if re.search(r"\d{2,}", line):  # 2+ digit numbers
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
    
    print(f"  ✅ Parsed {len(dogs)} dogs from this page")
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
    breed_patterns = [
      r"doodle", r"poo\b", r"poodle", r"maltipoo", r"shih-?poo", r"cavapoo",
      r"schnoodle", r"whoodle", r"bordoodle", r"irish.?doodle", r"mountain.?doodle",
      r"australian", r"f1b?\s", r"poo-", r"-poo", r"mix$"
    ]
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
    
    # FINAL VALIDATION: Reject names that are clearly not dog names
    reject_names = [
      "yes", "no", "some", "none", "all", "any", "other",
      "home", "about", "contact", "blog", "faq", "help",
      "happy tails", "alumni", "foster", "donate", "apply",
      "available", "pending", "upcoming", "coming soon",
      "adoption", "application", "adopt", "rescue",
      "policies", "procedures", "copyright", "privacy",
      "facebook", "instagram", "tiktok", "youtube",
      "male", "female", "hou", "dfw", "aus", "sa", "atx", "satx", "san",
      "low", "medium", "high", "unknown",
      "our policies", "oster family", "happy tails",
      # UI elements
      "load more", "show more", "see more", "more", "gallery",
      "menu", "search", "filter", "sort", "back", "next",
      # Location names
      "austin", "houston", "dallas", "san antonio", "texas",
      # Site navigation text
      "rehome", "community", "copyright",
    ]
    if name.lower() in reject_names:
      return None
    
    # Reject if name contains certain substrings
    reject_substrings = [
      "copyright", "rescue 20", "fur-ever", "forever home",
      "full bio", "policies and procedures", "click here",
      "read more", "learn more", "view all", "see all",
      "ready for adoption", "doodles ready", ".com", ".org",
      "be sure to", "make sure", "don't forget",
    ]
    if any(sub in name.lower() for sub in reject_substrings):
      return None
    
    # Reject if name is mostly non-alpha characters
    alpha_count = sum(1 for c in name if c.isalpha())
    if alpha_count < len(name) * 0.6:  # Less than 60% letters
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
