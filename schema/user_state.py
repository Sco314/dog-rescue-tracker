"""
User Dog State Schema
v1.0.0 - Phase 1 Foundations

Stores user-specific data about dogs, separate from global dog data.
This separation is critical for future multi-user support.

Design Principles:
- Never modify Dog objects with user-specific data
- All personalization goes through UserDogState
- Fit scores computed as: score = compute_score(dog, user_overrides)
- Ready for multiple users with minimal changes
"""
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any, List
from datetime import datetime


@dataclass
class UserOverrides:
  """
  User's corrections/additions to dog data.
  These override the rescue-provided values for scoring and display.
  """
  # Attribute overrides (user says "actually, shedding is Low")
  shedding: Optional[str] = None
  energy_level: Optional[str] = None
  good_with_dogs: Optional[str] = None
  good_with_cats: Optional[str] = None
  good_with_kids: Optional[str] = None
  weight_lbs: Optional[int] = None
  age_years: Optional[float] = None
  special_needs: Optional[bool] = None
  
  # Direct score adjustment (+/- points)
  manual_score_adjustment: int = 0
  
  def to_dict(self) -> Dict:
    result = {}
    for key, value in asdict(self).items():
      if value is not None and value != 0:
        result[key] = value
    return result
  
  @classmethod
  def from_dict(cls, data: Dict) -> "UserOverrides":
    if not data:
      return cls()
    return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
  
  def has_overrides(self) -> bool:
    """Check if user has any overrides set"""
    for key, value in asdict(self).items():
      if key == 'manual_score_adjustment':
        if value != 0:
          return True
      elif value is not None:
        return True
    return False


@dataclass
class UserDogState:
  """
  User-specific state for a dog.
  
  This is the "personalization layer" that sits on top of global Dog data.
  Each user can have their own UserDogState for each dog.
  """
  # Identity
  user_id: str = "default_user"  # For now, single user
  dog_id: str = ""
  
  # User overrides for scoring
  overrides: UserOverrides = field(default_factory=UserOverrides)
  
  # User preferences
  favorite: bool = False          # Starred/watched
  hidden: bool = False            # User doesn't want to see this dog
  applied: bool = False           # User has applied to adopt
  contacted_rescue: bool = False  # User has contacted rescue about this dog
  
  # User notes
  notes: str = ""                 # Private notes
  
  # Acknowledgments
  acknowledged_changes: List[str] = field(default_factory=list)  # Change IDs user has seen
  
  # Computed (cached) score with overrides
  computed_fit_score: Optional[int] = None
  
  # Timestamps
  created_at: Optional[str] = None
  updated_at: Optional[str] = None
  favorited_at: Optional[str] = None
  
  def __post_init__(self):
    if isinstance(self.overrides, dict):
      self.overrides = UserOverrides.from_dict(self.overrides)
  
  def to_dict(self) -> Dict:
    """Convert to dictionary for storage"""
    result = {
      'user_id': self.user_id,
      'dog_id': self.dog_id,
      'favorite': self.favorite,
      'hidden': self.hidden,
      'applied': self.applied,
      'contacted_rescue': self.contacted_rescue,
      'notes': self.notes,
      'acknowledged_changes': self.acknowledged_changes,
    }
    
    # Only include overrides if they exist
    if self.overrides.has_overrides():
      result['overrides'] = self.overrides.to_dict()
    
    # Only include computed score if set
    if self.computed_fit_score is not None:
      result['computed_fit_score'] = self.computed_fit_score
    
    # Only include timestamps if set
    for ts_field in ['created_at', 'updated_at', 'favorited_at']:
      value = getattr(self, ts_field)
      if value:
        result[ts_field] = value
    
    return result
  
  @classmethod
  def from_dict(cls, data: Dict) -> "UserDogState":
    """Create UserDogState from dictionary"""
    if not data:
      return cls()
    
    # Handle nested overrides
    if 'overrides' in data and isinstance(data['overrides'], dict):
      data['overrides'] = UserOverrides.from_dict(data['overrides'])
    
    # Filter to valid fields
    valid_fields = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
    return cls(**valid_fields)
  
  @classmethod
  def from_legacy_override(cls, dog_id: str, legacy_data: Dict) -> "UserDogState":
    """
    Create from legacy user_overrides.json format.
    Legacy format was: { "dogs": { "dog_id": { field: value, ... } } }
    """
    state = cls(dog_id=dog_id)
    
    if not legacy_data:
      return state
    
    # Map legacy fields to new structure
    overrides = UserOverrides()
    
    # Direct field mappings
    if 'shedding' in legacy_data:
      overrides.shedding = legacy_data['shedding']
    if 'energy_level' in legacy_data:
      overrides.energy_level = legacy_data['energy_level']
    if 'good_with_dogs' in legacy_data:
      overrides.good_with_dogs = legacy_data['good_with_dogs']
    if 'good_with_cats' in legacy_data:
      overrides.good_with_cats = legacy_data['good_with_cats']
    if 'good_with_kids' in legacy_data:
      overrides.good_with_kids = legacy_data['good_with_kids']
    if 'weight' in legacy_data:
      overrides.weight_lbs = legacy_data['weight']
    if 'score_modifier' in legacy_data:
      overrides.manual_score_adjustment = legacy_data['score_modifier']
    
    state.overrides = overrides
    
    # Map watch_list to favorite
    if legacy_data.get('watch_list') == 'Yes':
      state.favorite = True
    
    return state
  
  def to_legacy_format(self) -> Dict:
    """
    Convert to legacy user_overrides.json format.
    Used for backward compatibility during transition.
    """
    result = {}
    
    if self.overrides.shedding:
      result['shedding'] = self.overrides.shedding
    if self.overrides.energy_level:
      result['energy_level'] = self.overrides.energy_level
    if self.overrides.good_with_dogs:
      result['good_with_dogs'] = self.overrides.good_with_dogs
    if self.overrides.good_with_cats:
      result['good_with_cats'] = self.overrides.good_with_cats
    if self.overrides.good_with_kids:
      result['good_with_kids'] = self.overrides.good_with_kids
    if self.overrides.weight_lbs:
      result['weight'] = self.overrides.weight_lbs
    if self.overrides.manual_score_adjustment:
      result['score_modifier'] = self.overrides.manual_score_adjustment
    
    if self.favorite:
      result['watch_list'] = 'Yes'
    
    return result


@dataclass 
class ScoringConfig:
  """
  User's scoring preferences.
  Determines how fit scores are calculated.
  """
  # Weight bonuses
  weight_40_plus: int = 2
  
  # Age scoring
  age_sweet_spot: int = 2      # 1-2 years
  age_good: int = 1            # 2-4 years
  age_neutral: int = 0         # 4-6 years
  age_older: int = -1          # 6-8 years
  age_senior: int = -4         # 8+ years
  
  # Shedding
  shedding_none: int = 2
  shedding_low: int = 1
  shedding_high: int = -1
  shedding_unknown: int = 1
  
  # Energy
  energy_low_med: int = 2
  energy_unknown: int = 1
  
  # Compatibility
  good_with_dogs: int = 2
  good_with_kids: int = 1
  good_with_cats: int = 1
  
  # Breed
  doodle_breed: int = 1
  
  # Penalties
  special_needs: int = -1
  pending_penalty: int = -8
  
  def to_dict(self) -> Dict:
    return asdict(self)
  
  @classmethod
  def from_dict(cls, data: Dict) -> "ScoringConfig":
    if not data:
      return cls()
    return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class UserPreferences:
  """
  Complete user preferences including scoring config.
  """
  user_id: str = "default_user"
  scoring_config: ScoringConfig = field(default_factory=ScoringConfig)
  
  # UI preferences
  default_filter: str = "available"
  default_sort: str = "fit-desc"
  default_rescue: str = "all"
  
  # Notification preferences
  email_notifications: bool = False
  notify_on_new_dogs: bool = True
  notify_on_status_changes: bool = True
  notify_min_fit_score: int = 5
  
  def to_dict(self) -> Dict:
    return {
      'user_id': self.user_id,
      'scoring_config': self.scoring_config.to_dict(),
      'default_filter': self.default_filter,
      'default_sort': self.default_sort,
      'default_rescue': self.default_rescue,
      'email_notifications': self.email_notifications,
      'notify_on_new_dogs': self.notify_on_new_dogs,
      'notify_on_status_changes': self.notify_on_status_changes,
      'notify_min_fit_score': self.notify_min_fit_score,
    }
  
  @classmethod
  def from_dict(cls, data: Dict) -> "UserPreferences":
    if not data:
      return cls()
    
    if 'scoring_config' in data and isinstance(data['scoring_config'], dict):
      data['scoring_config'] = ScoringConfig.from_dict(data['scoring_config'])
    
    valid_fields = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
    return cls(**valid_fields)
