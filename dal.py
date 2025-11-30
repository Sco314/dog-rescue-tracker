"""
Data Access Layer (DAL)
v1.0.0 - Phase 1 Foundations

Central API for all data operations. All code that reads/writes dog data
must go through this layer.

Design Principles:
- Single point of access for all data
- Storage implementation is abstracted (can swap SQLite for Postgres later)
- Atomic writes with validation
- Clear separation of global dog data vs user state
- Event logging for all significant changes

Usage:
  from dal import DAL
  
  dal = DAL()
  dog = dal.get_dog("doodle_rock_rescue_kru")
  user_state = dal.get_user_dog_state("default_user", dog.dog_id)
  score = dal.compute_fit_score(dog, user_state.overrides)
"""
import sqlite3
import json
import os
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
from contextlib import contextmanager

from schema import (
  Dog, DogImage, RescueMeta,
  UserDogState, UserOverrides, UserPreferences, ScoringConfig,
  DogEvent, EventType,
  create_first_seen_event, create_status_change_event, 
  create_website_update_event, detect_changes,
  get_current_timestamp,
)


class DAL:
  """
  Data Access Layer - The single gateway for all data operations.
  
  Responsibilities:
  - CRUD operations for Dogs
  - CRUD operations for UserDogState
  - Event timeline management
  - Fit score computation
  - Data validation
  """
  
  def __init__(self, db_path: str = "dogs.db", user_state_path: str = "user_overrides.json"):
    self.db_path = db_path
    self.user_state_path = user_state_path
    self._user_states_cache: Optional[Dict] = None
    self._user_preferences_cache: Optional[UserPreferences] = None
  
  # ============================================
  # Database Connection Management
  # ============================================
  
  @contextmanager
  def _get_connection(self):
    """Get database connection with automatic cleanup"""
    conn = sqlite3.connect(self.db_path)
    conn.row_factory = sqlite3.Row
    try:
      yield conn
      conn.commit()
    except Exception as e:
      conn.rollback()
      raise
    finally:
      conn.close()
  
  def init_database(self):
    """Initialize database schema"""
    with self._get_connection() as conn:
      cursor = conn.cursor()
      
      # Dogs table (same as existing for backward compatibility)
      cursor.execute("""
        CREATE TABLE IF NOT EXISTS dogs (
          dog_id TEXT PRIMARY KEY,
          dog_name TEXT NOT NULL,
          rescue_name TEXT NOT NULL,
          breed TEXT,
          weight INTEGER,
          age_range TEXT,
          age_category TEXT,
          age_years_min REAL,
          age_years_max REAL,
          age_is_range INTEGER DEFAULT 0,
          age_score INTEGER,
          sex TEXT,
          shedding TEXT,
          energy_level TEXT,
          good_with_kids TEXT,
          good_with_dogs TEXT,
          good_with_cats TEXT,
          training_level TEXT,
          training_notes TEXT,
          special_needs TEXT,
          health_notes TEXT,
          adoption_req TEXT,
          adoption_fee TEXT,
          platform TEXT,
          location TEXT,
          status TEXT,
          notes TEXT,
          source_url TEXT,
          image_url TEXT,
          fit_score INTEGER,
          watch_list TEXT,
          date_first_seen TEXT,
          date_last_updated TEXT,
          date_status_changed TEXT,
          date_went_pending TEXT,
          date_went_unavailable TEXT,
          is_active INTEGER DEFAULT 1,
          -- New schema fields (stored as JSON)
          rescue_meta_json TEXT,
          images_json TEXT
        )
      """)
      
      # Events table (new)
      cursor.execute("""
        CREATE TABLE IF NOT EXISTS dog_events (
          event_id TEXT PRIMARY KEY,
          dog_id TEXT NOT NULL,
          event_type TEXT NOT NULL,
          timestamp TEXT NOT NULL,
          source TEXT,
          summary TEXT,
          field_changed TEXT,
          old_value TEXT,
          new_value TEXT,
          details_json TEXT,
          created_by TEXT DEFAULT 'system',
          FOREIGN KEY (dog_id) REFERENCES dogs(dog_id)
        )
      """)
      
      # Legacy changes table (maintain for backward compatibility)
      cursor.execute("""
        CREATE TABLE IF NOT EXISTS changes (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          dog_id TEXT NOT NULL,
          dog_name TEXT NOT NULL,
          field_changed TEXT NOT NULL,
          old_value TEXT,
          new_value TEXT,
          change_type TEXT NOT NULL,
          timestamp TEXT NOT NULL,
          notified INTEGER DEFAULT 0,
          FOREIGN KEY (dog_id) REFERENCES dogs(dog_id)
        )
      """)
      
      # Indexes
      cursor.execute("CREATE INDEX IF NOT EXISTS idx_dogs_status ON dogs(status)")
      cursor.execute("CREATE INDEX IF NOT EXISTS idx_dogs_rescue ON dogs(rescue_name)")
      cursor.execute("CREATE INDEX IF NOT EXISTS idx_dogs_fit ON dogs(fit_score)")
      cursor.execute("CREATE INDEX IF NOT EXISTS idx_dogs_active ON dogs(is_active)")
      cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_dog ON dog_events(dog_id)")
      cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_type ON dog_events(event_type)")
      cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_time ON dog_events(timestamp)")
      
      # Migrations for existing databases
      cursor.execute("PRAGMA table_info(dogs)")
      columns = [col[1] for col in cursor.fetchall()]
      
      if "rescue_meta_json" not in columns:
        cursor.execute("ALTER TABLE dogs ADD COLUMN rescue_meta_json TEXT")
      if "images_json" not in columns:
        cursor.execute("ALTER TABLE dogs ADD COLUMN images_json TEXT")
      
      print("✅ Database initialized")
  
  # ============================================
  # Dog CRUD Operations
  # ============================================
  
  def get_dog(self, dog_id: str) -> Optional[Dog]:
    """Get a single dog by ID"""
    with self._get_connection() as conn:
      cursor = conn.cursor()
      cursor.execute("SELECT * FROM dogs WHERE dog_id = ?", (dog_id,))
      row = cursor.fetchone()
      
      if not row:
        return None
      
      return self._row_to_dog(dict(row))
  
  def get_all_dogs(self, active_only: bool = True) -> List[Dog]:
    """Get all dogs, optionally filtered by active status"""
    with self._get_connection() as conn:
      cursor = conn.cursor()
      
      if active_only:
        cursor.execute("SELECT * FROM dogs WHERE is_active = 1 ORDER BY fit_score DESC")
      else:
        cursor.execute("SELECT * FROM dogs ORDER BY fit_score DESC")
      
      rows = cursor.fetchall()
      return [self._row_to_dog(dict(row)) for row in rows]
  
  def get_dogs_by_rescue(self, rescue_name: str, active_only: bool = True) -> List[Dog]:
    """Get all dogs from a specific rescue"""
    with self._get_connection() as conn:
      cursor = conn.cursor()
      
      if active_only:
        cursor.execute(
          "SELECT * FROM dogs WHERE rescue_name = ? AND is_active = 1 ORDER BY fit_score DESC",
          (rescue_name,)
        )
      else:
        cursor.execute(
          "SELECT * FROM dogs WHERE rescue_name = ? ORDER BY fit_score DESC",
          (rescue_name,)
        )
      
      rows = cursor.fetchall()
      return [self._row_to_dog(dict(row)) for row in rows]
  
  def get_dogs_by_status(self, status: str) -> List[Dog]:
    """Get all dogs with a specific status"""
    with self._get_connection() as conn:
      cursor = conn.cursor()
      cursor.execute(
        "SELECT * FROM dogs WHERE status = ? AND is_active = 1 ORDER BY fit_score DESC",
        (status,)
      )
      rows = cursor.fetchall()
      return [self._row_to_dog(dict(row)) for row in rows]
  
  def save_dog(self, dog: Dog) -> List[DogEvent]:
    """
    Save a dog (insert or update).
    Returns list of events generated.
    """
    existing = self.get_dog(dog.dog_id)
    
    if existing:
      return self._update_dog(dog, existing)
    else:
      return self._insert_dog(dog)
  
  def _insert_dog(self, dog: Dog) -> List[DogEvent]:
    """Insert a new dog"""
    events = []
    now = get_current_timestamp()
    
    # Create first seen event
    event = create_first_seen_event(
      dog_id=dog.dog_id,
      dog_name=dog.dog_name,
      rescue_name=dog.rescue_name,
      status=dog.status,
      fit_score=dog.base_fit_score or dog.fit_score
    )
    events.append(event)
    
    with self._get_connection() as conn:
      cursor = conn.cursor()
      
      # Prepare JSON fields
      rescue_meta_json = json.dumps(dog.rescue_meta.to_dict()) if dog.rescue_meta else None
      images_json = json.dumps([img.to_dict() for img in dog.images]) if dog.images else None
      
      cursor.execute("""
        INSERT INTO dogs (
          dog_id, dog_name, rescue_name, breed, weight, age_range, age_category,
          sex, shedding, energy_level, good_with_kids, good_with_dogs, good_with_cats,
          special_needs, adoption_fee, platform, location, status, notes, source_url,
          image_url, fit_score, watch_list, date_first_seen, date_last_updated,
          date_status_changed, is_active, rescue_meta_json, images_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
      """, (
        dog.dog_id, dog.dog_name, dog.rescue_name, dog.breed,
        dog.weight_lbs or dog.weight,
        dog.age_display or dog.age_range, "",
        dog.sex, dog.shedding, dog.energy_level,
        dog.good_with_kids, dog.good_with_dogs, dog.good_with_cats,
        'Yes' if dog.special_needs else 'No',
        dog.adoption_fee, dog.platform, dog.location, dog.status,
        dog.rescue_meta.bio_text if dog.rescue_meta else "",
        dog.rescue_dog_url or dog.source_url,
        dog.primary_image_url or dog.image_url,
        dog.base_fit_score or dog.fit_score,
        dog.watch_list, now, now, now, 1,
        rescue_meta_json, images_json
      ))
      
      # Save event
      self._save_event(cursor, event)
      
      # Also save to legacy changes table
      cursor.execute("""
        INSERT INTO changes (dog_id, dog_name, field_changed, old_value, new_value, change_type, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?)
      """, (
        dog.dog_id, dog.dog_name, "dog", "",
        f"New: {dog.status} | Fit: {dog.fit_score} | {dog.breed}",
        "new_dog", now
      ))
    
    print(f"  🆕 New dog: {dog.dog_name} ({dog.rescue_name}) - Fit: {dog.fit_score}")
    return events
  
  def _update_dog(self, dog: Dog, existing: Dog) -> List[DogEvent]:
    """Update an existing dog, detecting and recording changes"""
    events = []
    now = get_current_timestamp()
    
    # Detect changes
    tracked_fields = [
      'status', 'weight', 'shedding', 'energy_level',
      'good_with_kids', 'good_with_dogs', 'good_with_cats',
      'special_needs', 'adoption_fee', 'fit_score'
    ]
    
    old_data = existing.to_legacy_dict()
    new_data = dog.to_legacy_dict()
    changes = detect_changes(old_data, new_data, tracked_fields)
    
    # Handle status change separately
    if 'status' in changes:
      old_status, new_status = changes.pop('status')
      event = create_status_change_event(
        dog_id=dog.dog_id,
        dog_name=dog.dog_name,
        rescue_name=dog.rescue_name,
        old_status=old_status,
        new_status=new_status
      )
      events.append(event)
      print(f"  📢 Status change: {dog.dog_name} | {old_status} → {new_status}")
    
    # Handle other changes
    if changes:
      event = create_website_update_event(
        dog_id=dog.dog_id,
        dog_name=dog.dog_name,
        rescue_name=dog.rescue_name,
        changes=changes
      )
      events.append(event)
    
    # Update database
    with self._get_connection() as conn:
      cursor = conn.cursor()
      
      rescue_meta_json = json.dumps(dog.rescue_meta.to_dict()) if dog.rescue_meta else None
      images_json = json.dumps([img.to_dict() for img in dog.images]) if dog.images else None
      
      cursor.execute("""
        UPDATE dogs SET
          dog_name = ?, rescue_name = ?, breed = ?, weight = ?,
          age_range = ?, sex = ?, shedding = ?, energy_level = ?,
          good_with_kids = ?, good_with_dogs = ?, good_with_cats = ?,
          special_needs = ?, adoption_fee = ?, platform = ?, location = ?,
          status = ?, notes = ?, source_url = ?, image_url = ?, fit_score = ?,
          date_last_updated = ?, is_active = 1,
          rescue_meta_json = ?, images_json = ?
        WHERE dog_id = ?
      """, (
        dog.dog_name, dog.rescue_name, dog.breed,
        dog.weight_lbs or dog.weight,
        dog.age_display or dog.age_range,
        dog.sex, dog.shedding, dog.energy_level,
        dog.good_with_kids, dog.good_with_dogs, dog.good_with_cats,
        'Yes' if dog.special_needs else 'No',
        dog.adoption_fee, dog.platform, dog.location, dog.status,
        dog.rescue_meta.bio_text if dog.rescue_meta else "",
        dog.rescue_dog_url or dog.source_url,
        dog.primary_image_url or dog.image_url,
        dog.base_fit_score or dog.fit_score,
        now, rescue_meta_json, images_json, dog.dog_id
      ))
      
      # Save events
      for event in events:
        self._save_event(cursor, event)
        
        # Also save to legacy changes table
        cursor.execute("""
          INSERT INTO changes (dog_id, dog_name, field_changed, old_value, new_value, change_type, timestamp)
          VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
          event.dog_id, dog.dog_name, event.field_changed or event.event_type,
          event.old_value or "", event.new_value or event.summary,
          event.event_type, event.timestamp
        ))
    
    return events
  
  def mark_dogs_inactive(self, active_dog_ids: List[str], rescue_name: str) -> List[DogEvent]:
    """Mark dogs not in the current scrape as inactive (likely adopted)"""
    events = []
    now = get_current_timestamp()
    
    if not active_dog_ids:
      return events
    
    with self._get_connection() as conn:
      cursor = conn.cursor()
      
      # Find dogs from this rescue that are active but not in current scrape
      placeholders = ",".join("?" * len(active_dog_ids))
      cursor.execute(f"""
        SELECT dog_id, dog_name, status FROM dogs 
        WHERE rescue_name = ? AND is_active = 1 AND dog_id NOT IN ({placeholders})
      """, [rescue_name] + active_dog_ids)
      
      missing_dogs = cursor.fetchall()
      
      for row in missing_dogs:
        dog_id = row['dog_id']
        dog_name = row['dog_name']
        old_status = row['status']
        
        # Create status change event
        event = create_status_change_event(
          dog_id=dog_id,
          dog_name=dog_name,
          rescue_name=rescue_name,
          old_status=old_status,
          new_status="Adopted/Removed"
        )
        events.append(event)
        
        # Update dog
        cursor.execute("""
          UPDATE dogs SET is_active = 0, status = 'Adopted/Removed', 
          date_went_unavailable = ?, date_last_updated = ?
          WHERE dog_id = ?
        """, (now, now, dog_id))
        
        # Save event
        self._save_event(cursor, event)
        
        print(f"  🏠 Likely adopted: {dog_name}")
    
    return events
  
  def _row_to_dog(self, row: Dict) -> Dog:
    """Convert database row to Dog object"""
    # Parse JSON fields
    rescue_meta = None
    if row.get('rescue_meta_json'):
      try:
        rescue_meta = RescueMeta.from_dict(json.loads(row['rescue_meta_json']))
      except:
        pass
    
    images = []
    if row.get('images_json'):
      try:
        images = [DogImage.from_dict(img) for img in json.loads(row['images_json'])]
      except:
        pass
    
    return Dog.from_legacy(row)
  
  def _save_event(self, cursor, event: DogEvent):
    """Save an event to the database"""
    details_json = json.dumps(event.details) if event.details else None
    
    cursor.execute("""
      INSERT OR REPLACE INTO dog_events (
        event_id, dog_id, event_type, timestamp, source, summary,
        field_changed, old_value, new_value, details_json, created_by
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
      event.event_id, event.dog_id, event.event_type, event.timestamp,
      event.source, event.summary, event.field_changed,
      event.old_value, event.new_value, details_json, event.created_by
    ))
  
  # ============================================
  # Event Operations
  # ============================================
  
  def get_dog_events(self, dog_id: str, limit: int = 50) -> List[DogEvent]:
    """Get events for a specific dog"""
    with self._get_connection() as conn:
      cursor = conn.cursor()
      cursor.execute("""
        SELECT * FROM dog_events WHERE dog_id = ?
        ORDER BY timestamp DESC LIMIT ?
      """, (dog_id, limit))
      
      events = []
      for row in cursor.fetchall():
        row_dict = dict(row)
        if row_dict.get('details_json'):
          row_dict['details'] = json.loads(row_dict['details_json'])
        del row_dict['details_json']
        events.append(DogEvent.from_dict(row_dict))
      
      return events
  
  def get_recent_events(self, limit: int = 100, event_type: Optional[str] = None) -> List[DogEvent]:
    """Get recent events across all dogs"""
    with self._get_connection() as conn:
      cursor = conn.cursor()
      
      if event_type:
        cursor.execute("""
          SELECT * FROM dog_events WHERE event_type = ?
          ORDER BY timestamp DESC LIMIT ?
        """, (event_type, limit))
      else:
        cursor.execute("""
          SELECT * FROM dog_events ORDER BY timestamp DESC LIMIT ?
        """, (limit,))
      
      events = []
      for row in cursor.fetchall():
        row_dict = dict(row)
        if row_dict.get('details_json'):
          row_dict['details'] = json.loads(row_dict['details_json'])
        del row_dict['details_json']
        events.append(DogEvent.from_dict(row_dict))
      
      return events
  
  def append_dog_event(self, dog_id: str, event: DogEvent):
    """Append an event to a dog's timeline"""
    with self._get_connection() as conn:
      cursor = conn.cursor()
      self._save_event(cursor, event)
  
  # ============================================
  # User State Operations
  # ============================================
  
  def _load_user_states(self) -> Dict:
    """Load user states from JSON file"""
    if self._user_states_cache is not None:
      return self._user_states_cache
    
    if os.path.exists(self.user_state_path):
      try:
        with open(self.user_state_path, 'r') as f:
          data = json.load(f)
          self._user_states_cache = data
          return data
      except Exception as e:
        print(f"⚠️ Error loading user states: {e}")
    
    self._user_states_cache = {"dogs": {}, "acknowledgedChanges": [], "scoringConfig": {}}
    return self._user_states_cache
  
  def _save_user_states(self, data: Dict):
    """Save user states to JSON file"""
    self._user_states_cache = data
    try:
      with open(self.user_state_path, 'w') as f:
        json.dump(data, f, indent=2)
    except Exception as e:
      print(f"⚠️ Error saving user states: {e}")
  
  def get_user_dog_state(self, user_id: str, dog_id: str) -> UserDogState:
    """Get user's state for a specific dog"""
    data = self._load_user_states()
    dog_data = data.get("dogs", {}).get(dog_id, {})
    
    state = UserDogState.from_legacy_override(dog_id, dog_data)
    state.user_id = user_id
    
    # Check acknowledged changes
    state.acknowledged_changes = data.get("acknowledgedChanges", [])
    
    return state
  
  def save_user_dog_state(self, state: UserDogState):
    """Save user's state for a dog"""
    data = self._load_user_states()
    
    if "dogs" not in data:
      data["dogs"] = {}
    
    # Convert to legacy format for now
    legacy_data = state.to_legacy_format()
    if legacy_data:
      data["dogs"][state.dog_id] = legacy_data
    elif state.dog_id in data["dogs"]:
      del data["dogs"][state.dog_id]
    
    self._save_user_states(data)
  
  def get_user_preferences(self, user_id: str = "default_user") -> UserPreferences:
    """Get user's global preferences"""
    data = self._load_user_states()
    
    prefs = UserPreferences(user_id=user_id)
    
    if "scoringConfig" in data:
      prefs.scoring_config = ScoringConfig.from_dict(data["scoringConfig"])
    
    return prefs
  
  def save_user_preferences(self, prefs: UserPreferences):
    """Save user's global preferences"""
    data = self._load_user_states()
    data["scoringConfig"] = prefs.scoring_config.to_dict()
    self._save_user_states(data)
  
  # ============================================
  # Fit Score Computation
  # ============================================
  
  def compute_fit_score(
    self, 
    dog: Dog, 
    overrides: Optional[UserOverrides] = None,
    config: Optional[ScoringConfig] = None
  ) -> int:
    """
    Compute fit score for a dog with optional user overrides.
    
    This is THE canonical way to compute scores:
    score = compute_fit_score(dog, user_overrides, scoring_config)
    """
    if config is None:
      config = ScoringConfig()
    
    score = 0
    
    # Get effective values (override if provided)
    weight = overrides.weight_lbs if (overrides and overrides.weight_lbs) else (dog.weight_lbs or dog.weight)
    shedding = overrides.shedding if (overrides and overrides.shedding) else dog.shedding
    energy = overrides.energy_level if (overrides and overrides.energy_level) else dog.energy_level
    good_dogs = overrides.good_with_dogs if (overrides and overrides.good_with_dogs) else dog.good_with_dogs
    good_kids = overrides.good_with_kids if (overrides and overrides.good_with_kids) else dog.good_with_kids
    good_cats = overrides.good_with_cats if (overrides and overrides.good_with_cats) else dog.good_with_cats
    special_needs = overrides.special_needs if (overrides and overrides.special_needs is not None) else dog.special_needs
    
    # Weight scoring
    if weight and weight >= 40:
      score += config.weight_40_plus
    
    # Age scoring
    age_years = overrides.age_years if (overrides and overrides.age_years) else dog.age_years
    if age_years is None:
      # Try to parse from age_display/age_range
      age_years = self._parse_age_to_years(dog.age_display or dog.age_range)
    
    if age_years is not None:
      if age_years < 0.75:
        pass  # Very young puppies - neutral
      elif age_years < 2.0:
        score += config.age_sweet_spot
      elif age_years < 4.0:
        score += config.age_good
      elif age_years < 6.0:
        score += config.age_neutral
      elif age_years < 8.0:
        score += config.age_older
      else:
        score += config.age_senior
    
    # Shedding scoring
    if shedding:
      shedding_lower = shedding.lower()
      if shedding_lower == "none":
        score += config.shedding_none
      elif shedding_lower == "low":
        score += config.shedding_low
      elif shedding_lower == "high":
        score += config.shedding_high
      elif shedding_lower == "unknown":
        score += config.shedding_unknown
    else:
      score += config.shedding_unknown
    
    # Energy scoring
    if energy:
      energy_lower = energy.lower()
      if energy_lower in ["low", "medium"]:
        score += config.energy_low_med
    else:
      score += config.energy_unknown
    
    # Compatibility scoring
    if good_dogs == "Yes":
      score += config.good_with_dogs
    if good_kids == "Yes":
      score += config.good_with_kids
    if good_cats == "Yes":
      score += config.good_with_cats
    
    # Breed bonus
    breed = dog.breed or ""
    if any(term in breed.lower() for term in ["doodle", "poodle", "poo"]):
      score += config.doodle_breed
    
    # Special needs penalty
    if special_needs:
      score += config.special_needs
    
    # Pending penalty
    if dog.status == "Pending":
      score += config.pending_penalty
    
    # Manual adjustment
    if overrides and overrides.manual_score_adjustment:
      score += overrides.manual_score_adjustment
    
    return max(0, score)
  
  def _parse_age_to_years(self, age_str: Optional[str]) -> Optional[float]:
    """Parse age string to years"""
    if not age_str:
      return None
    
    import re
    age_str = age_str.lower().replace("–", "-").replace("—", "-")
    
    # Range: "1-3 yrs"
    match = re.search(r"(\d+\.?\d*)\s*-\s*(\d+\.?\d*)\s*(yr|year|mo|month)", age_str)
    if match:
      min_val = float(match.group(1))
      max_val = float(match.group(2))
      unit = match.group(3)
      if unit.startswith("mo"):
        min_val /= 12
        max_val /= 12
      return (min_val + max_val) / 2
    
    # Single: "2 yrs" or "8 mos"
    match = re.search(r"(\d+\.?\d*)\s*(yr|year|mo|month|wk|week)", age_str)
    if match:
      val = float(match.group(1))
      unit = match.group(2)
      if unit.startswith("mo"):
        val /= 12
      elif unit.startswith("wk") or unit.startswith("week"):
        val /= 52
      return val
    
    return None
  
  # ============================================
  # Convenience Methods
  # ============================================
  
  def get_dashboard_data(self) -> Dict:
    """Get all data needed for the dashboard (for backward compatibility)"""
    dogs = self.get_all_dogs(active_only=True)
    
    # Get recent changes from legacy table for now
    with self._get_connection() as conn:
      cursor = conn.cursor()
      cursor.execute("""
        SELECT c.*, d.fit_score as current_fit
        FROM changes c
        LEFT JOIN dogs d ON c.dog_id = d.dog_id
        WHERE c.timestamp > datetime('now', '-7 days')
        ORDER BY c.timestamp DESC
        LIMIT 100
      """)
      changes = [dict(row) for row in cursor.fetchall()]
    
    return {
      "dogs": [d.to_legacy_dict() for d in dogs],
      "changes": changes,
      "generated_at": get_current_timestamp()
    }
  
  def apply_user_overrides_to_dogs(self, dogs: List[Dog], user_id: str = "default_user") -> List[Dog]:
    """Apply user overrides to a list of dogs and recompute scores"""
    prefs = self.get_user_preferences(user_id)
    
    for dog in dogs:
      state = self.get_user_dog_state(user_id, dog.dog_id)
      dog.fit_score = self.compute_fit_score(dog, state.overrides, prefs.scoring_config)
      dog.watch_list = "Yes" if state.favorite else ""
    
    return dogs


# Create a default instance for easy importing
_default_dal: Optional[DAL] = None

def get_dal() -> DAL:
  """Get the default DAL instance"""
  global _default_dal
  if _default_dal is None:
    _default_dal = DAL()
  return _default_dal
