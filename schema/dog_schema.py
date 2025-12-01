"""
Universal Dog Schema
v1.0.0 - Phase 1 Foundations

This is the single source of truth for dog data structure.
All scrapers, UI, and storage must conform to this schema.

Design Principles:
- Global data (from rescues) is separate from user-specific data
- All fields are nullable to handle incomplete data gracefully
- Original rescue text is preserved in rescue_meta
- Schema supports future multi-user, admin, and gallery features
"""
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
import json


class DogStatus(str, Enum):
  """Standardized dog status values"""
  AVAILABLE = "Available"
  COMING_SOON = "Upcoming"
  PENDING = "Pending"
  ADOPTED = "Adopted"
  INACTIVE = "Inactive"
  UNKNOWN = "Unknown"
  
  @classmethod
  def from_string(cls, value: str) -> "DogStatus":
    """Convert string to DogStatus, handling variations"""
    if not value:
      return cls.UNKNOWN
    
    value_lower = value.lower().strip()
    
    if value_lower in ["available", "adoptable"]:
      return cls.AVAILABLE
    elif value_lower in ["coming soon", "upcoming", "coming_soon"]:
      return cls.COMING_SOON
    elif value_lower in ["pending", "adoption pending"]:
      return cls.PENDING
    elif value_lower in ["adopted", "adopted/removed", "removed", "inactive"]:
      return cls.ADOPTED
    else:
      return cls.UNKNOWN


@dataclass
class DogImage:
  """Represents a single dog image"""
  url: str
  source: str = ""  # "rescue_website", "facebook", "admin_upload"
  priority: int = 0  # Lower = higher priority (0 = primary)
  caption: Optional[str] = None
  added_at: Optional[str] = None
  
  def to_dict(self) -> Dict:
    return asdict(self)
  
  @classmethod
  def from_dict(cls, data: Dict) -> "DogImage":
    return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class RescueMeta:
  """
  Original rescue-specific data, preserved as-is.
  This allows us to show "what the rescue said" vs "what we parsed".
  """
  # Original text fields from rescue
  weight_text: Optional[str] = None  # "About 50 lbs"
  age_text: Optional[str] = None     # "2-3 years old"
  breed_text: Optional[str] = None   # "Goldendoodle F1B"
  bio_html: Optional[str] = None     # Full bio as HTML
  bio_text: Optional[str] = None     # Bio as plain text
  
  # Rescue-specific fields
  rescue_dog_id: Optional[str] = None  # Their internal ID if visible
  rescue_location_code: Optional[str] = None  # "HOU", "DFW", etc.
  
  # Compatibility as stated by rescue
  good_with_dogs_text: Optional[str] = None
  good_with_cats_text: Optional[str] = None
  good_with_kids_text: Optional[str] = None
  
  # Training info
  crate_trained: Optional[str] = None
  potty_trained: Optional[str] = None
  leash_trained: Optional[str] = None
  
  # Health
  spay_neuter_status: Optional[str] = None
  vaccination_status: Optional[str] = None
  heartworm_status: Optional[str] = None
  
  # Adoption
  adoption_fee_text: Optional[str] = None
  adoption_radius_text: Optional[str] = None
  adoption_requirements_text: Optional[str] = None
  
  # Raw data blob for anything else
  extra: Optional[Dict[str, Any]] = None
  
  def to_dict(self) -> Dict:
    result = asdict(self)
    # Remove None values for cleaner storage
    return {k: v for k, v in result.items() if v is not None}
  
  @classmethod
  def from_dict(cls, data: Dict) -> "RescueMeta":
    if not data:
      return cls()
    return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class Dog:
  """
  Universal Dog Schema - Global Data
  
  This represents the shared, authoritative data about a dog.
  User-specific data (overrides, favorites, notes) is stored separately
  in UserDogState.
  
  All fields are optional except dog_id and dog_name.
  """
  
  # ===== IDENTITY (Required) =====
  dog_id: str                    # Stable internal ID (rescue_name + normalized_name)
  dog_name: str                  # Display name
  
  # ===== RESCUE INFO =====
  rescue_name: str = ""          # "Doodle Rock Rescue", etc.
  rescue_dog_url: Optional[str] = None  # Direct link to dog's page
  platform: str = ""             # Website domain
  
  # ===== STATUS =====
  status: str = "Unknown"        # Use DogStatus values
  is_active: bool = True         # False = no longer on website
  
  # ===== CORE ATTRIBUTES (Parsed/Normalized) =====
  weight_lbs: Optional[int] = None
  age_years: Optional[float] = None      # Normalized to years (e.g., 1.5)
  age_display: Optional[str] = None      # Display string "2 yrs", "8 mos"
  sex: Optional[str] = None              # "Male", "Female"
  breed: Optional[str] = None
  location: Optional[str] = None         # City/area
  
  # ===== COMPATIBILITY (Normalized to Yes/No/Unknown) =====
  good_with_dogs: Optional[str] = None
  good_with_cats: Optional[str] = None
  good_with_kids: Optional[str] = None
  
  # ===== CHARACTERISTICS =====
  shedding: Optional[str] = None         # "None", "Low", "Moderate", "High"
  energy_level: Optional[str] = None     # "Low", "Medium", "High"
  special_needs: bool = False
  special_needs_notes: Optional[str] = None
  
  # ===== ADOPTION INFO =====
  adoption_fee: Optional[str] = None
  adoption_radius_miles: Optional[int] = None
  adoption_requirements: Optional[List[str]] = None
  
  # ===== IMAGES =====
  primary_image_url: Optional[str] = None  # Quick access to main photo
  additional_images: List[str] = field(default_factory=list)  # Extra photo URLs
  images: List[DogImage] = field(default_factory=list)  # Full image objects (future)
  
  # ===== RESCUE METADATA (Original Text) =====
  rescue_meta: Optional[RescueMeta] = None
  
  # ===== COMPUTED SCORES (Base, before user overrides) =====
  base_fit_score: Optional[int] = None  # Score without user adjustments
  
  # ===== TIMESTAMPS =====
  created_at: Optional[str] = None       # First seen in system
  updated_at: Optional[str] = None       # Last data update
  rescue_last_scraped_at: Optional[str] = None
  status_changed_at: Optional[str] = None
  
  # ===== LEGACY COMPATIBILITY =====
  # These fields maintain backward compatibility with existing code
  source_url: Optional[str] = None       # Alias for rescue_dog_url
  image_url: Optional[str] = None        # Alias for primary_image_url
  age_range: Optional[str] = None        # Alias for age_display
  weight: Optional[int] = None           # Alias for weight_lbs
  fit_score: Optional[int] = None        # Currently same as base_fit_score
  watch_list: str = ""                   # Legacy - moving to UserDogState
  
  def __post_init__(self):
    """Ensure consistency after initialization"""
    # Sync legacy fields with new fields
    if self.rescue_dog_url and not self.source_url:
      self.source_url = self.rescue_dog_url
    elif self.source_url and not self.rescue_dog_url:
      self.rescue_dog_url = self.source_url
    
    if self.primary_image_url and not self.image_url:
      self.image_url = self.primary_image_url
    elif self.image_url and not self.primary_image_url:
      self.primary_image_url = self.image_url
    
    if self.weight_lbs and not self.weight:
      self.weight = self.weight_lbs
    elif self.weight and not self.weight_lbs:
      self.weight_lbs = self.weight
    
    if self.age_display and not self.age_range:
      self.age_range = self.age_display
    elif self.age_range and not self.age_display:
      self.age_display = self.age_range
    
    if self.base_fit_score and not self.fit_score:
      self.fit_score = self.base_fit_score
    elif self.fit_score and not self.base_fit_score:
      self.base_fit_score = self.fit_score
  
  def to_dict(self) -> Dict:
    """Convert to dictionary for storage"""
    result = {}
    for key, value in asdict(self).items():
      if value is not None:
        if isinstance(value, list):
          # Handle list of dataclasses
          if value and hasattr(value[0], 'to_dict'):
            result[key] = [item.to_dict() if hasattr(item, 'to_dict') else item for item in value]
          else:
            result[key] = value
        elif hasattr(value, 'to_dict'):
          result[key] = value.to_dict()
        else:
          result[key] = value
    return result
  
  @classmethod
  def from_dict(cls, data: Dict) -> "Dog":
    """Create Dog from dictionary"""
    if not data:
      raise ValueError("Cannot create Dog from empty data")
    
    # Handle nested objects
    if 'rescue_meta' in data and isinstance(data['rescue_meta'], dict):
      data['rescue_meta'] = RescueMeta.from_dict(data['rescue_meta'])
    
    if 'images' in data and isinstance(data['images'], list):
      data['images'] = [
        DogImage.from_dict(img) if isinstance(img, dict) else img 
        for img in data['images']
      ]
    
    # Filter to only valid fields
    valid_fields = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
    return cls(**valid_fields)
  
  @classmethod
  def from_legacy(cls, legacy_data: Dict) -> "Dog":
    """
    Create Dog from legacy database format.
    Maps old field names to new schema.
    """
    # Direct mappings
    dog = cls(
      dog_id=legacy_data.get('dog_id', ''),
      dog_name=legacy_data.get('dog_name', ''),
      rescue_name=legacy_data.get('rescue_name', ''),
      rescue_dog_url=legacy_data.get('source_url'),
      platform=legacy_data.get('platform', ''),
      status=legacy_data.get('status', 'Unknown'),
      is_active=bool(legacy_data.get('is_active', 1)),
      weight_lbs=legacy_data.get('weight'),
      age_display=legacy_data.get('age_range'),
      sex=legacy_data.get('sex'),
      breed=legacy_data.get('breed'),
      location=legacy_data.get('location'),
      good_with_dogs=legacy_data.get('good_with_dogs'),
      good_with_cats=legacy_data.get('good_with_cats'),
      good_with_kids=legacy_data.get('good_with_kids'),
      shedding=legacy_data.get('shedding'),
      energy_level=legacy_data.get('energy_level'),
      special_needs=legacy_data.get('special_needs') == 'Yes',
      adoption_fee=legacy_data.get('adoption_fee'),
      primary_image_url=legacy_data.get('image_url'),
      base_fit_score=legacy_data.get('fit_score'),
      created_at=legacy_data.get('date_first_seen'),
      updated_at=legacy_data.get('date_last_updated'),
      status_changed_at=legacy_data.get('date_status_changed'),
      # Legacy fields
      source_url=legacy_data.get('source_url'),
      image_url=legacy_data.get('image_url'),
      age_range=legacy_data.get('age_range'),
      weight=legacy_data.get('weight'),
      fit_score=legacy_data.get('fit_score'),
      watch_list=legacy_data.get('watch_list', ''),
    )
    
    # Build rescue_meta from legacy fields
    dog.rescue_meta = RescueMeta(
      bio_text=legacy_data.get('notes'),
      adoption_requirements_text=legacy_data.get('adoption_req'),
    )
    
    return dog
  
  def to_legacy_dict(self) -> Dict:
    """
    Convert to legacy database format.
    Used for backward compatibility during transition.
    """
    return {
      'dog_id': self.dog_id,
      'dog_name': self.dog_name,
      'rescue_name': self.rescue_name,
      'breed': self.breed or '',
      'weight': self.weight_lbs,
      'age_range': self.age_display or '',
      'sex': self.sex or '',
      'shedding': self.shedding or '',
      'energy_level': self.energy_level or '',
      'good_with_kids': self.good_with_kids or '',
      'good_with_dogs': self.good_with_dogs or '',
      'good_with_cats': self.good_with_cats or '',
      'special_needs': 'Yes' if self.special_needs else 'No',
      'adoption_fee': self.adoption_fee or '',
      'platform': self.platform or '',
      'location': self.location or '',
      'status': self.status,
      'source_url': self.rescue_dog_url or '',
      'image_url': self.primary_image_url or '',
      'fit_score': self.base_fit_score,
      'watch_list': self.watch_list,
      'is_active': 1 if self.is_active else 0,
      'notes': self.rescue_meta.bio_text if self.rescue_meta else '',
      'adoption_req': self.rescue_meta.adoption_requirements_text if self.rescue_meta else '',
    }


def get_current_timestamp() -> str:
  """Returns current timestamp in ISO format"""
  return datetime.now().isoformat()


def get_current_date() -> str:
  """Returns current date in YYYY-MM-DD format"""
  return datetime.now().strftime("%Y-%m-%d")
