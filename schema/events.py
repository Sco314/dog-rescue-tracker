"""
Dog Updates / Event Timeline System
v1.0.0 - Phase 1 Foundations

Standardizes how we record "what changed when" for each dog.
Events are append-only and never corrupt dog data.

Event Types:
- first_seen: Dog first appeared in system
- status_change: Status changed (Available → Pending, etc.)
- website_update: Significant metadata changed on rescue site
- fb_post: Facebook post about this dog
- admin_edit: Admin made manual correction
- user_note: User added a note (stored separately but referenced)
"""
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum
import json


class EventType(str, Enum):
  """Types of events that can occur for a dog"""
  FIRST_SEEN = "first_seen"
  STATUS_CHANGE = "status_change"
  WEBSITE_UPDATE = "website_update"
  FB_POST = "fb_post"
  ADMIN_EDIT = "admin_edit"
  IMAGE_ADDED = "image_added"
  PRICE_CHANGE = "price_change"
  SCRAPE_UPDATE = "scrape_update"


class EventSource(str, Enum):
  """Source of the event"""
  DOODLE_ROCK_SITE = "doodle_rock_site"
  DOODLE_DANDY_SITE = "doodle_dandy_site"
  POODLE_PATCH_SITE = "poodle_patch_site"
  FACEBOOK = "facebook"
  ADMIN = "admin"
  SYSTEM = "system"
  
  @classmethod
  def from_rescue_name(cls, rescue_name: str) -> "EventSource":
    """Map rescue name to event source"""
    mapping = {
      "doodle rock rescue": cls.DOODLE_ROCK_SITE,
      "doodle dandy rescue": cls.DOODLE_DANDY_SITE,
      "poodle patch rescue": cls.POODLE_PATCH_SITE,
    }
    return mapping.get(rescue_name.lower(), cls.SYSTEM)


@dataclass
class DogEvent:
  """
  A single event in a dog's timeline.
  
  Events are immutable once created.
  They provide a complete audit trail of changes.
  """
  # Required fields
  event_id: str              # Unique ID for this event
  dog_id: str                # Which dog this event is for
  event_type: str            # EventType value
  timestamp: str             # ISO format timestamp
  
  # Event details
  source: str = ""           # EventSource value
  summary: str = ""          # Human-readable summary
  details: Optional[Dict[str, Any]] = None  # Type-specific details
  
  # For change events
  field_changed: Optional[str] = None
  old_value: Optional[str] = None
  new_value: Optional[str] = None
  
  # Metadata
  created_by: str = "system"  # Who/what created this event
  
  def to_dict(self) -> Dict:
    """Convert to dictionary for storage"""
    result = {
      'event_id': self.event_id,
      'dog_id': self.dog_id,
      'event_type': self.event_type,
      'timestamp': self.timestamp,
      'source': self.source,
      'summary': self.summary,
    }
    
    if self.details:
      result['details'] = self.details
    if self.field_changed:
      result['field_changed'] = self.field_changed
    if self.old_value:
      result['old_value'] = self.old_value
    if self.new_value:
      result['new_value'] = self.new_value
    if self.created_by != "system":
      result['created_by'] = self.created_by
    
    return result
  
  @classmethod
  def from_dict(cls, data: Dict) -> "DogEvent":
    """Create event from dictionary"""
    valid_fields = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
    return cls(**valid_fields)


def generate_event_id(dog_id: str, event_type: str, timestamp: str) -> str:
  """Generate a unique event ID"""
  # Use timestamp + type + hash for uniqueness
  import hashlib
  content = f"{dog_id}_{event_type}_{timestamp}"
  hash_suffix = hashlib.md5(content.encode()).hexdigest()[:8]
  return f"{dog_id}_{event_type}_{hash_suffix}"


def get_timestamp() -> str:
  """Get current timestamp in ISO format"""
  return datetime.now().isoformat()


# ============================================
# Event Factory Functions
# ============================================

def create_first_seen_event(
  dog_id: str,
  dog_name: str,
  rescue_name: str,
  status: str,
  fit_score: Optional[int] = None
) -> DogEvent:
  """Create event for when a dog is first seen in the system"""
  timestamp = get_timestamp()
  source = EventSource.from_rescue_name(rescue_name)
  
  summary = f"First seen: {status}"
  if fit_score is not None:
    summary += f" (Fit Score: {fit_score})"
  
  return DogEvent(
    event_id=generate_event_id(dog_id, EventType.FIRST_SEEN.value, timestamp),
    dog_id=dog_id,
    event_type=EventType.FIRST_SEEN.value,
    timestamp=timestamp,
    source=source.value,
    summary=summary,
    details={
      'dog_name': dog_name,
      'rescue_name': rescue_name,
      'initial_status': status,
      'initial_fit_score': fit_score,
    }
  )


def create_status_change_event(
  dog_id: str,
  dog_name: str,
  rescue_name: str,
  old_status: str,
  new_status: str
) -> DogEvent:
  """Create event for status changes"""
  timestamp = get_timestamp()
  source = EventSource.from_rescue_name(rescue_name)
  
  # Create descriptive summary
  if new_status.lower() == "pending":
    summary = f"Application submitted - now pending"
  elif new_status.lower() == "available" and old_status.lower() == "pending":
    summary = f"Became available again (adoption fell through?)"
  elif new_status.lower() in ["adopted", "adopted/removed"]:
    summary = f"Adopted! 🎉"
  else:
    summary = f"Status: {old_status} → {new_status}"
  
  return DogEvent(
    event_id=generate_event_id(dog_id, EventType.STATUS_CHANGE.value, timestamp),
    dog_id=dog_id,
    event_type=EventType.STATUS_CHANGE.value,
    timestamp=timestamp,
    source=source.value,
    summary=summary,
    field_changed="status",
    old_value=old_status,
    new_value=new_status,
    details={
      'dog_name': dog_name,
      'from_status': old_status,
      'to_status': new_status,
    }
  )


def create_website_update_event(
  dog_id: str,
  dog_name: str,
  rescue_name: str,
  changes: Dict[str, tuple]  # field: (old_value, new_value)
) -> DogEvent:
  """Create event for website data updates (non-status)"""
  timestamp = get_timestamp()
  source = EventSource.from_rescue_name(rescue_name)
  
  # Build summary from changes
  change_summaries = []
  for field, (old_val, new_val) in changes.items():
    if field == 'weight':
      change_summaries.append(f"Weight: {old_val or '?'} → {new_val} lbs")
    elif field == 'fit_score':
      change_summaries.append(f"Fit Score: {old_val} → {new_val}")
    elif field == 'good_with_dogs':
      change_summaries.append(f"Good with dogs: {new_val}")
    elif field == 'good_with_kids':
      change_summaries.append(f"Good with kids: {new_val}")
    elif field == 'good_with_cats':
      change_summaries.append(f"Good with cats: {new_val}")
    else:
      change_summaries.append(f"{field}: {old_val or '?'} → {new_val}")
  
  summary = "; ".join(change_summaries[:3])  # Limit to 3 changes in summary
  if len(changes) > 3:
    summary += f" (+{len(changes) - 3} more)"
  
  return DogEvent(
    event_id=generate_event_id(dog_id, EventType.WEBSITE_UPDATE.value, timestamp),
    dog_id=dog_id,
    event_type=EventType.WEBSITE_UPDATE.value,
    timestamp=timestamp,
    source=source.value,
    summary=summary,
    details={
      'dog_name': dog_name,
      'changes': {k: {'old': v[0], 'new': v[1]} for k, v in changes.items()},
    }
  )


def create_image_added_event(
  dog_id: str,
  dog_name: str,
  rescue_name: str,
  image_url: str,
  image_source: str = "rescue_website"
) -> DogEvent:
  """Create event for when a new image is added"""
  timestamp = get_timestamp()
  source = EventSource.from_rescue_name(rescue_name)
  
  return DogEvent(
    event_id=generate_event_id(dog_id, EventType.IMAGE_ADDED.value, timestamp),
    dog_id=dog_id,
    event_type=EventType.IMAGE_ADDED.value,
    timestamp=timestamp,
    source=source.value,
    summary=f"New image added from {image_source}",
    details={
      'image_url': image_url,
      'image_source': image_source,
    }
  )


def create_admin_edit_event(
  dog_id: str,
  dog_name: str,
  admin_user: str,
  field_changed: str,
  old_value: str,
  new_value: str,
  reason: str = ""
) -> DogEvent:
  """Create event for admin/manual edits"""
  timestamp = get_timestamp()
  
  summary = f"Admin corrected {field_changed}"
  if reason:
    summary += f": {reason}"
  
  return DogEvent(
    event_id=generate_event_id(dog_id, EventType.ADMIN_EDIT.value, timestamp),
    dog_id=dog_id,
    event_type=EventType.ADMIN_EDIT.value,
    timestamp=timestamp,
    source=EventSource.ADMIN.value,
    summary=summary,
    field_changed=field_changed,
    old_value=old_value,
    new_value=new_value,
    created_by=admin_user,
    details={
      'reason': reason,
    }
  )


def create_fb_post_event(
  dog_id: str,
  dog_name: str,
  rescue_name: str,
  post_url: str,
  post_date: str,
  post_summary: str = ""
) -> DogEvent:
  """Create event for Facebook posts about this dog"""
  timestamp = get_timestamp()
  
  return DogEvent(
    event_id=generate_event_id(dog_id, EventType.FB_POST.value, timestamp),
    dog_id=dog_id,
    event_type=EventType.FB_POST.value,
    timestamp=timestamp,
    source=EventSource.FACEBOOK.value,
    summary=post_summary or f"Featured in Facebook post",
    details={
      'post_url': post_url,
      'post_date': post_date,
      'rescue_name': rescue_name,
    }
  )


# ============================================
# Event Comparison Helpers
# ============================================

def detect_changes(old_data: Dict, new_data: Dict, fields_to_track: List[str]) -> Dict[str, tuple]:
  """
  Compare old and new data, return dict of changes.
  Returns: {field_name: (old_value, new_value)}
  """
  changes = {}
  
  for field in fields_to_track:
    old_val = old_data.get(field)
    new_val = new_data.get(field)
    
    # Normalize for comparison
    old_str = str(old_val) if old_val is not None else ""
    new_str = str(new_val) if new_val is not None else ""
    
    # Only record if actually changed and new value exists
    if old_str != new_str and new_str:
      changes[field] = (old_str, new_str)
  
  return changes


def events_to_timeline(events: List[DogEvent], limit: int = 20) -> List[Dict]:
  """
  Convert events to a display-friendly timeline format.
  Returns most recent events first.
  """
  # Sort by timestamp descending
  sorted_events = sorted(events, key=lambda e: e.timestamp, reverse=True)
  
  timeline = []
  for event in sorted_events[:limit]:
    item = {
      'id': event.event_id,
      'date': event.timestamp,
      'type': event.event_type,
      'icon': _get_event_icon(event.event_type),
      'summary': event.summary,
      'source': event.source,
    }
    
    # Add change details for status changes
    if event.event_type == EventType.STATUS_CHANGE.value:
      item['old_status'] = event.old_value
      item['new_status'] = event.new_value
    
    timeline.append(item)
  
  return timeline


def _get_event_icon(event_type: str) -> str:
  """Get emoji icon for event type"""
  icons = {
    EventType.FIRST_SEEN.value: "🆕",
    EventType.STATUS_CHANGE.value: "📢",
    EventType.WEBSITE_UPDATE.value: "📝",
    EventType.FB_POST.value: "📘",
    EventType.ADMIN_EDIT.value: "✏️",
    EventType.IMAGE_ADDED.value: "📸",
    EventType.PRICE_CHANGE.value: "💰",
    EventType.SCRAPE_UPDATE.value: "🔄",
  }
  return icons.get(event_type, "📋")
