"""
Configuration for dog rescue scraper
"""

# Database configuration
DB_PATH = "dogs.db"

# Email notification settings (configure before first run)
EMAIL_CONFIG = {
  "enabled": False,  # Set to True when ready
  "smtp_server": "smtp.gmail.com",
  "smtp_port": 587,
  "sender_email": "your-email@gmail.com",  # Change this
  "sender_password": "",  # Use app password for Gmail
  "recipient_email": "your-email@gmail.com",  # Change this
  "notify_on_new_dogs": True,
  "notify_on_status_change": True,
  "notify_on_good_fit_only": True,  # Only alert for fit score >= 5
  "min_fit_score_alert": 5
}

# Rescue organizations
RESCUES = {
  "doodle_rock": {
    "name": "Doodle Rock Rescue",
    "location": "Dallas, TX",
    "available_url": "https://doodlerockrescue.org/adopt/available-dogs/",
    "upcoming_url": "https://doodlerockrescue.org/adopt/coming-soon-for-adoption/",
    "alumni_url": "https://doodlerockrescue.org/adopt/alumni/"
  },
  "doodle_dandy": {
    "name": "Doodle Dandy Rescue",
    "location": "DFW/Houston/Austin/SA",
    "available_url": "https://www.doodledandyrescue.org/all-adoptable-doodles",
    "pending_url": "https://www.doodledandyrescue.org/adoption-pending-doodles",
    "upcoming_url": "https://www.doodledandyrescue.org/doodles-coming-soon"
  },
  "poodle_patch": {
    "name": "Poodle Patch Rescue",
    "location": "Texarkana, TX",
    "available_url": "https://poodlepatchrescue.com/category/adoptable-pets/",
    "animals_url": "https://poodlepatchrescue.com/our-animals/"
  }
}

# Watch list dogs (names to flag for close monitoring)
WATCH_LIST_DOGS = [
  "Drizzle",
  "Kru",
  "Nimbi",
  "Zira",
  "Jojo",
  "Skipper",
  "Freddy Faz",
  "Freddy Fax",  # In case of typo variations
]

# Fit Score weights
# NOTE: Since these are doodle-specific rescues, most dogs will be low-shedding
# The scoring reflects YOUR priorities for finding a good match
SCORING_WEIGHTS = {
  "weight_threshold": 40,  # lbs - you want 40+ lb dogs
  "weight_points": 2,
  
  # Shedding - doodles typically low/none, so this is usually +1 or +2
  "shedding": {
    "None": 2,
    "Low": 1,
    "Moderate": 0,
    "High": -1,
    "Unknown": 1  # Assume low for doodles
  },
  
  # Energy - you want moderate, not super high
  "energy": {
    "Low": 2,
    "Medium": 2,
    "High": 0,  # Puppies often high energy - neutral, not negative
    "Unknown": 1
  },
  
  "good_with_kids": 1,
  "good_with_dogs": 2,  # Increased - important for Darwin!
  "good_with_cats": 1,
  
  "special_needs_penalty": -1,
  
  # NEW: Bonus for being a doodle/poodle (your target breeds)
  "doodle_bonus": 1,
  
  # NEW: Penalty for pending status (likely being placed elsewhere)
  "pending_penalty": -2
}

# User agent for web requests
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
