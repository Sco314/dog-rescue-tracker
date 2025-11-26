"""
Base scraper class for rescue websites
"""
import requests
from bs4 import BeautifulSoup
from typing import List, Optional
import re
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import Dog, get_current_date
from config import USER_AGENT


class BaseScraper:
  """Base class for rescue website scrapers"""
  
  def __init__(self, rescue_name: str, rescue_config: dict):
    self.rescue_name = rescue_config["name"]
    self.location = rescue_config["location"]
    self.config = rescue_config
    self.session = requests.Session()
    self.session.headers.update({"User-Agent": USER_AGENT})
  
  def fetch_page(self, url: str) -> Optional[BeautifulSoup]:
    """Fetch and parse a webpage"""
    try:
      print(f"  🔍 Fetching: {url}")
      response = self.session.get(url, timeout=30)
      response.raise_for_status()
      return BeautifulSoup(response.content, "html.parser")
    except requests.RequestException as e:
      print(f"  ❌ Error fetching {url}: {e}")
      return None
  
  def scrape(self) -> List[Dog]:
    """
    Override this method in child classes
    Returns list of Dog objects
    """
    raise NotImplementedError("Subclass must implement scrape()")
  
  def create_dog_id(self, dog_name: str, rescue_prefix: str = None) -> str:
    """Generate unique dog ID"""
    if not rescue_prefix:
      rescue_prefix = self.rescue_name[:3].lower().replace(" ", "")
    safe_name = dog_name.lower().replace(" ", "_").replace("'", "")
    return f"{rescue_prefix}_{safe_name}"
  
  def extract_weight(self, text: str) -> Optional[int]:
    """Extract weight in pounds from text"""
    if not text:
      return None
    
    # Look for patterns like "45 lbs", "45-50 lbs", "45 pounds", "~50 lbs"
    patterns = [
      r'~?\s*(\d+)\s*(?:-\s*\d+\s*)?(?:lbs?|pounds?)',
      r'(\d+)\s*(?:-\s*\d+\s*)?\s*(?:lbs?|pounds?)'
    ]
    
    for pattern in patterns:
      match = re.search(pattern, text.lower())
      if match:
        return int(match.group(1))
    return None
  
  def extract_age(self, text: str) -> tuple:
    """
    Extract age information
    Returns (age_range, age_category)
    """
    if not text:
      return "", ""
    
    text_lower = text.lower()
    age_range = ""
    age_category = ""
    
    # Extract numeric age
    age_match = re.search(r'(\d+)\s*(?:-\s*(\d+)\s*)?(?:year|yr|month|mo)', text_lower)
    if age_match:
      start = age_match.group(1)
      end = age_match.group(2)
      age_range = f"{start}-{end}" if end else start
    
    # Determine category
    if "puppy" in text_lower or "pup" in text_lower:
      age_category = "Puppy"
    elif "senior" in text_lower:
      age_category = "Senior"
    elif "adult" in text_lower or age_range:
      age_category = "Adult"
    
    return age_range, age_category
  
  def normalize_yes_no(self, value: str) -> str:
    """Normalize yes/no/unknown values"""
    if not value:
      return "Unknown"
    
    value_lower = value.lower().strip()
    
    # Yes patterns
    if any(word in value_lower for word in ["yes", "true", "good", "ok", "friendly", "gets along"]):
      return "Yes"
    
    # No patterns
    elif any(word in value_lower for word in ["no", "false", "not good", "doesn't", "does not"]):
      return "No"
    
    # Unknown patterns
    else:
      return "Unknown"
  
  def normalize_energy(self, value: str) -> str:
    """Normalize energy level"""
    if not value:
      return "Unknown"
    
    value_lower = value.lower().strip()
    
    if any(word in value_lower for word in ["low", "calm", "mellow", "lazy", "couch"]):
      return "Low"
    elif any(word in value_lower for word in ["high", "active", "energetic", "athletic", "hyper"]):
      return "High"
    elif any(word in value_lower for word in ["medium", "moderate", "average"]):
      return "Medium"
    else:
      return "Unknown"
  
  def normalize_shedding(self, value: str) -> str:
    """Normalize shedding level"""
    if not value:
      return "Unknown"
    
    value_lower = value.lower().strip()
    
    if any(word in value_lower for word in ["none", "non-shedding", "doesn't shed", "hypoallergenic"]):
      return "None"
    elif any(word in value_lower for word in ["low", "minimal", "light"]):
      return "Low"
    elif any(word in value_lower for word in ["moderate", "medium", "average"]):
      return "Moderate"
    elif any(word in value_lower for word in ["high", "heavy", "lots"]):
      return "High"
    else:
      return "Unknown"
  
  def normalize_sex(self, value: str) -> str:
    """Normalize sex"""
    if not value:
      return ""
    
    value_lower = value.lower().strip()
    if "male" in value_lower and "female" not in value_lower:
      return "Male"
    elif "female" in value_lower:
      return "Female"
    return ""
  
  def extract_fee(self, text: str) -> str:
    """Extract adoption fee from text"""
    if not text:
      return ""
    
    # Look for dollar amounts
    fee_match = re.search(r'\$\s*(\d+(?:,\d{3})*(?:\.\d{2})?)', text)
    if fee_match:
      return f"${fee_match.group(1)}"
    
    return text.strip()
