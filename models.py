"""
Data models for dog rescue scraper
"""
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional, List

@dataclass
class Dog:
  """Represents a dog listing from a rescue"""
  dog_id: str  # Unique ID (rescue_dogname or rescue_url_slug)
  dog_name: str
  rescue_name: str
  breed: str = ""
  weight: Optional[int] = None  # in lbs
  age_range: str = ""  # e.g., "2-3"
  age_category: str = ""  # e.g., "Adult", "Puppy", "Senior"
  sex: str = ""
  shedding: str = ""  # "None", "Low", "Moderate", "High"
  energy_level: str = ""  # "Low", "Medium", "High"
  good_with_kids: str = ""  # "Yes", "No", "Unknown"
  good_with_dogs: str = ""
  good_with_cats: str = ""
  training_level: str = ""
  training_notes: str = ""
  special_needs: str = ""  # "Yes" or "No"
  health_notes: str = ""
  adoption_req: str = ""
  adoption_fee: str = ""
  platform: str = ""  # Website name
  location: str = ""
  status: str = ""  # "Available", "Pending", "Upcoming", "Adopted"
  status_history: str = ""
  notes: str = ""
  source_url: str = ""
  image_url: str = ""  # Primary photo URL
  date_collected: str = ""
  date_posted: str = ""
  date_updated: str = ""
  date_pending: str = ""
  date_unavailable: str = ""
  
  fit_score: Optional[int] = None
  watch_list: str = ""  # "Yes" or ""
  created_at: str = ""
  updated_at: str = ""
  
  def to_row(self) -> List[str]:
    """Convert to spreadsheet row format"""
    return [
      self.dog_id,
      self.dog_name,
      self.rescue_name,
      self.breed,
      str(self.weight) if self.weight else "",
      self.age_range,
      self.age_category,
      self.sex,
      self.shedding,
      self.energy_level,
      self.good_with_kids,
      self.good_with_dogs,
      self.good_with_cats,
      self.training_level,
      self.training_notes,
      self.special_needs,
      self.health_notes,
      self.adoption_req,
      self.adoption_fee,
      self.platform,
      self.location,
      self.status,
      self.status_history,
      self.notes,
      self.source_url,
      self.date_collected,
      self.date_posted,
      self.date_updated,
      self.date_pending,
      self.date_unavailable
    ]


@dataclass
class ChangeRecord:
  """Tracks a change to a dog's status or details"""
  dog_id: str
  dog_name: str
  field_changed: str
  old_value: str
  new_value: str
  timestamp: str
  change_type: str  # "status_change", "new_dog", "field_update"
  
  def to_dict(self):
    return asdict(self)


def get_current_timestamp() -> str:
  """Returns current timestamp in ISO format"""
  return datetime.now().isoformat()


def get_current_date() -> str:
  """Returns current date in YYYY-MM-DD format"""
  return datetime.now().strftime("%Y-%m-%d")
