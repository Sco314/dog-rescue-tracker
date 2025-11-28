"""
SQLite database operations for dog rescue tracker
v2.0.0 - Enhanced date tracking
"""
import sqlite3
from typing import List, Optional, Dict, Any
from datetime import datetime
from models import Dog, ChangeRecord, get_current_timestamp


DB_FILE = "dogs.db"


def get_connection() -> sqlite3.Connection:
  """Get database connection with row factory"""
  conn = sqlite3.connect(DB_FILE)
  conn.row_factory = sqlite3.Row
  return conn


def init_database():
  """Initialize database schema"""
  conn = get_connection()
  cursor = conn.cursor()
  
  # Main dogs table - current state of each dog
  cursor.execute("""
    CREATE TABLE IF NOT EXISTS dogs (
      dog_id TEXT PRIMARY KEY,
      dog_name TEXT NOT NULL,
      rescue_name TEXT NOT NULL,
      breed TEXT,
      weight INTEGER,
      age_range TEXT,
      age_category TEXT,
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
      fit_score INTEGER,
      watch_list TEXT,
      date_first_seen TEXT,
      date_last_updated TEXT,
      date_status_changed TEXT,
      date_went_pending TEXT,
      date_went_available TEXT,
      date_went_unavailable TEXT,
      is_active INTEGER DEFAULT 1
    )
  """)
  
  # Changes table - tracks all changes for analytics
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
  
  # Scrape runs table - tracks each scrape for debugging/analytics
  cursor.execute("""
    CREATE TABLE IF NOT EXISTS scrape_runs (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      timestamp TEXT NOT NULL,
      rescue_name TEXT,
      dogs_found INTEGER,
      new_dogs INTEGER,
      changes_detected INTEGER,
      errors TEXT,
      duration_seconds REAL
    )
  """)
  
  # Status history table - detailed status progression per dog
  cursor.execute("""
    CREATE TABLE IF NOT EXISTS status_history (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      dog_id TEXT NOT NULL,
      status TEXT NOT NULL,
      timestamp TEXT NOT NULL,
      days_in_previous_status INTEGER,
      FOREIGN KEY (dog_id) REFERENCES dogs(dog_id)
    )
  """)
  
  # Create indexes for common queries
  cursor.execute("CREATE INDEX IF NOT EXISTS idx_dogs_status ON dogs(status)")
  cursor.execute("CREATE INDEX IF NOT EXISTS idx_dogs_rescue ON dogs(rescue_name)")
  cursor.execute("CREATE INDEX IF NOT EXISTS idx_dogs_fit ON dogs(fit_score)")
  cursor.execute("CREATE INDEX IF NOT EXISTS idx_dogs_watch ON dogs(watch_list)")
  cursor.execute("CREATE INDEX IF NOT EXISTS idx_changes_dog ON changes(dog_id)")
  cursor.execute("CREATE INDEX IF NOT EXISTS idx_changes_type ON changes(change_type)")
  cursor.execute("CREATE INDEX IF NOT EXISTS idx_changes_timestamp ON changes(timestamp)")
  
  conn.commit()
  conn.close()
  print("✅ Database initialized")


def dog_exists(dog_id: str) -> bool:
  """Check if dog already exists in database"""
  conn = get_connection()
  cursor = conn.cursor()
  cursor.execute("SELECT 1 FROM dogs WHERE dog_id = ?", (dog_id,))
  result = cursor.fetchone()
  conn.close()
  return result is not None


def get_dog(dog_id: str) -> Optional[Dict]:
  """Get dog by ID"""
  conn = get_connection()
  cursor = conn.cursor()
  cursor.execute("SELECT * FROM dogs WHERE dog_id = ?", (dog_id,))
  row = cursor.fetchone()
  conn.close()
  return dict(row) if row else None


def get_all_active_dogs() -> List[Dict]:
  """Get all active dogs"""
  conn = get_connection()
  cursor = conn.cursor()
  cursor.execute("SELECT * FROM dogs WHERE is_active = 1 ORDER BY fit_score DESC")
  rows = cursor.fetchall()
  conn.close()
  return [dict(row) for row in rows]


def insert_dog(dog: Dog) -> List[ChangeRecord]:
  """
  Insert new dog into database
  Returns list of changes (new dog notification)
  """
  changes = []
  now = get_current_timestamp()
  
  conn = get_connection()
  cursor = conn.cursor()
  
  cursor.execute("""
    INSERT INTO dogs (
      dog_id, dog_name, rescue_name, breed, weight, age_range, age_category,
      sex, shedding, energy_level, good_with_kids, good_with_dogs, good_with_cats,
      training_level, training_notes, special_needs, health_notes, adoption_req,
      adoption_fee, platform, location, status, notes, source_url,
      fit_score, watch_list, date_first_seen, date_last_updated, date_status_changed
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
  """, (
    dog.dog_id, dog.dog_name, dog.rescue_name, dog.breed, dog.weight,
    dog.age_range, dog.age_category, dog.sex, dog.shedding, dog.energy_level,
    dog.good_with_kids, dog.good_with_dogs, dog.good_with_cats,
    dog.training_level, dog.training_notes, dog.special_needs, dog.health_notes,
    dog.adoption_req, dog.adoption_fee, dog.platform, dog.location, dog.status,
    dog.notes, dog.source_url, dog.fit_score, dog.watch_list,
    now, now, now
  ))
  
  # Record initial status in history
  cursor.execute("""
    INSERT INTO status_history (dog_id, status, timestamp)
    VALUES (?, ?, ?)
  """, (dog.dog_id, dog.status, now))
  
  # Create change record for new dog
  change = ChangeRecord(
    dog_id=dog.dog_id,
    dog_name=dog.dog_name,
    field_changed="dog",
    old_value="",
    new_value=f"New: {dog.status} | Fit: {dog.fit_score} | {dog.breed}",
    timestamp=now,
    change_type="new_dog"
  )
  changes.append(change)
  
  # Record change in database
  cursor.execute("""
    INSERT INTO changes (dog_id, dog_name, field_changed, old_value, new_value, change_type, timestamp)
    VALUES (?, ?, ?, ?, ?, ?, ?)
  """, (change.dog_id, change.dog_name, change.field_changed, 
        change.old_value, change.new_value, change.change_type, change.timestamp))
  
  conn.commit()
  conn.close()
  
  print(f"  🆕 New dog: {dog.dog_name} ({dog.rescue_name}) - Fit: {dog.fit_score}")
  return changes


def update_dog(dog: Dog) -> List[ChangeRecord]:
  """
  Update existing dog, detect and record changes
  Returns list of changes detected
  """
  changes = []
  now = get_current_timestamp()
  
  existing = get_dog(dog.dog_id)
  if not existing:
    return insert_dog(dog)
  
  conn = get_connection()
  cursor = conn.cursor()
  
  # Fields to track for changes
  tracked_fields = [
    ("status", "status"),
    ("fit_score", "fit_score"),
    ("weight", "weight"),
    ("shedding", "shedding"),
    ("energy_level", "energy_level"),
    ("good_with_kids", "good_with_kids"),
    ("good_with_dogs", "good_with_dogs"),
    ("good_with_cats", "good_with_cats"),
    ("special_needs", "special_needs"),
    ("adoption_fee", "adoption_fee")
  ]
  
  status_changed = False
  new_status = None
  
  for field, attr in tracked_fields:
    old_val = existing.get(field)
    new_val = getattr(dog, attr)
    
    # Normalize for comparison
    old_str = str(old_val) if old_val is not None else ""
    new_str = str(new_val) if new_val is not None else ""
    
    if old_str != new_str and new_str:  # Only if actually changed and new value exists
      change_type = "status_change" if field == "status" else "field_update"
      
      change = ChangeRecord(
        dog_id=dog.dog_id,
        dog_name=dog.dog_name,
        field_changed=field,
        old_value=old_str,
        new_value=new_str,
        timestamp=now,
        change_type=change_type
      )
      changes.append(change)
      
      # Record change
      cursor.execute("""
        INSERT INTO changes (dog_id, dog_name, field_changed, old_value, new_value, change_type, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?)
      """, (change.dog_id, change.dog_name, change.field_changed,
            change.old_value, change.new_value, change.change_type, change.timestamp))
      
      if field == "status":
        status_changed = True
        new_status = new_str
        print(f"  📢 Status change: {dog.dog_name} | {old_str} → {new_str}")
        
        # Calculate days in previous status
        cursor.execute("""
          SELECT timestamp FROM status_history 
          WHERE dog_id = ? ORDER BY timestamp DESC LIMIT 1
        """, (dog.dog_id,))
        last_status = cursor.fetchone()
        
        days_in_prev = None
        if last_status:
          try:
            last_dt = datetime.fromisoformat(last_status['timestamp'])
            days_in_prev = (datetime.now() - last_dt).days
          except:
            pass
        
        # Record new status in history
        cursor.execute("""
          INSERT INTO status_history (dog_id, status, timestamp, days_in_previous_status)
          VALUES (?, ?, ?, ?)
        """, (dog.dog_id, new_str, now, days_in_prev))
  
  # Update the dog record
  update_fields = {
    "breed": dog.breed,
    "weight": dog.weight,
    "age_range": dog.age_range,
    "age_category": dog.age_category,
    "sex": dog.sex,
    "shedding": dog.shedding,
    "energy_level": dog.energy_level,
    "good_with_kids": dog.good_with_kids,
    "good_with_dogs": dog.good_with_dogs,
    "good_with_cats": dog.good_with_cats,
    "training_level": dog.training_level,
    "training_notes": dog.training_notes,
    "special_needs": dog.special_needs,
    "health_notes": dog.health_notes,
    "adoption_req": dog.adoption_req,
    "adoption_fee": dog.adoption_fee,
    "platform": dog.platform,
    "location": dog.location,
    "status": dog.status,
    "notes": dog.notes,
    "source_url": dog.source_url,
    "fit_score": dog.fit_score,
    "watch_list": dog.watch_list,
    "date_last_updated": now,
    "is_active": 1
  }
  
  if status_changed:
    update_fields["date_status_changed"] = now
    if new_status and new_status.lower() == "pending":
      update_fields["date_went_pending"] = now
    elif new_status and new_status.lower() == "available":
      update_fields["date_went_available"] = now
    elif new_status and new_status.lower() in ["adopted", "unavailable", "adopted/removed"]:
      update_fields["date_went_unavailable"] = now
  
  set_clause = ", ".join([f"{k} = ?" for k in update_fields.keys()])
  values = list(update_fields.values()) + [dog.dog_id]
  
  cursor.execute(f"UPDATE dogs SET {set_clause} WHERE dog_id = ?", values)
  
  conn.commit()
  conn.close()
  
  return changes


def mark_dogs_inactive(active_dog_ids: List[str], rescue_name: str) -> List[ChangeRecord]:
  """
  Mark dogs as inactive if they weren't found in current scrape
  (Dog removed from website = likely adopted)
  """
  changes = []
  now = get_current_timestamp()
  
  if not active_dog_ids:
    return changes
  
  conn = get_connection()
  cursor = conn.cursor()
  
  # Find dogs from this rescue that are active but not in current scrape
  placeholders = ",".join("?" * len(active_dog_ids))
  cursor.execute(f"""
    SELECT dog_id, dog_name, status FROM dogs 
    WHERE rescue_name = ? AND is_active = 1 AND dog_id NOT IN ({placeholders})
  """, [rescue_name] + active_dog_ids)
  
  missing_dogs = cursor.fetchall()
  
  for row in missing_dogs:
    # Mark as inactive/adopted
    cursor.execute("""
      UPDATE dogs SET is_active = 0, status = 'Adopted/Removed', 
      date_went_unavailable = ?, date_last_updated = ?, date_status_changed = ?
      WHERE dog_id = ?
    """, (now, now, now, row['dog_id']))
    
    change = ChangeRecord(
      dog_id=row['dog_id'],
      dog_name=row['dog_name'],
      field_changed="status",
      old_value=row['status'],
      new_value="Adopted/Removed",
      timestamp=now,
      change_type="status_change"
    )
    changes.append(change)
    
    cursor.execute("""
      INSERT INTO changes (dog_id, dog_name, field_changed, old_value, new_value, change_type, timestamp)
      VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (change.dog_id, change.dog_name, change.field_changed,
          change.old_value, change.new_value, change.change_type, change.timestamp))
    
    # Record in status history
    cursor.execute("""
      INSERT INTO status_history (dog_id, status, timestamp)
      VALUES (?, ?, ?)
    """, (row['dog_id'], "Adopted/Removed", now))
    
    print(f"  🏠 Likely adopted: {row['dog_name']}")
  
  conn.commit()
  conn.close()
  
  return changes


def record_scrape_run(rescue_name: str, dogs_found: int, new_dogs: int, 
                      changes_detected: int, errors: str, duration: float):
  """Record scrape run statistics"""
  conn = get_connection()
  cursor = conn.cursor()
  cursor.execute("""
    INSERT INTO scrape_runs (timestamp, rescue_name, dogs_found, new_dogs, 
                             changes_detected, errors, duration_seconds)
    VALUES (?, ?, ?, ?, ?, ?, ?)
  """, (get_current_timestamp(), rescue_name, dogs_found, new_dogs, 
        changes_detected, errors, duration))
  conn.commit()
  conn.close()


def get_watch_list_dogs() -> List[Dict]:
  """Get all dogs on watch list"""
  conn = get_connection()
  cursor = conn.cursor()
  cursor.execute("SELECT * FROM dogs WHERE watch_list = 'Yes' AND is_active = 1")
  rows = cursor.fetchall()
  conn.close()
  return [dict(row) for row in rows]


def get_high_fit_dogs(min_score: int = 5) -> List[Dict]:
  """Get all high fit score dogs"""
  conn = get_connection()
  cursor = conn.cursor()
  cursor.execute("""
    SELECT * FROM dogs WHERE fit_score >= ? AND is_active = 1
    ORDER BY fit_score DESC
  """, (min_score,))
  rows = cursor.fetchall()
  conn.close()
  return [dict(row) for row in rows]


def get_pending_notifications() -> List[Dict]:
  """Get changes that haven't been notified yet"""
  conn = get_connection()
  cursor = conn.cursor()
  cursor.execute("""
    SELECT c.*, d.fit_score, d.watch_list, d.rescue_name
    FROM changes c
    JOIN dogs d ON c.dog_id = d.dog_id
    WHERE c.notified = 0
    ORDER BY c.timestamp DESC
  """)
  rows = cursor.fetchall()
  conn.close()
  return [dict(row) for row in rows]


def mark_notified(change_ids: List[int]):
  """Mark changes as notified"""
  if not change_ids:
    return
  conn = get_connection()
  cursor = conn.cursor()
  cursor.execute(
    f"UPDATE changes SET notified = 1 WHERE id IN ({','.join('?' * len(change_ids))})",
    change_ids
  )
  conn.commit()
  conn.close()


def get_recent_changes(hours: int = 48) -> List[Dict]:
  """Get recent changes"""
  conn = get_connection()
  cursor = conn.cursor()
  cursor.execute(f"""
    SELECT c.*, d.fit_score, d.watch_list, d.breed, d.weight, d.rescue_name
    FROM changes c
    LEFT JOIN dogs d ON c.dog_id = d.dog_id
    WHERE c.timestamp > datetime('now', '-{hours} hours')
    ORDER BY c.timestamp DESC
  """)
  rows = cursor.fetchall()
  conn.close()
  return [dict(row) for row in rows]


# Initialize on import
if __name__ == "__main__":
  init_database()
