"""
Schema Package
v1.0.0 - Phase 1 Foundations

Contains all data models and schemas for the Dog Rescue Tracker.

Modules:
- dog_schema: Universal Dog model and related types
- user_state: User-specific state (overrides, favorites, preferences)
- events: Event timeline system for tracking changes
"""

from .dog_schema import (
  Dog,
  DogImage,
  DogStatus,
  RescueMeta,
  get_current_timestamp,
  get_current_date,
)

from .user_state import (
  UserDogState,
  UserOverrides,
  UserPreferences,
  ScoringConfig,
)

from .events import (
  DogEvent,
  EventType,
  EventSource,
  create_first_seen_event,
  create_status_change_event,
  create_website_update_event,
  create_image_added_event,
  create_admin_edit_event,
  create_fb_post_event,
  detect_changes,
  events_to_timeline,
)

__all__ = [
  # Dog schema
  'Dog',
  'DogImage',
  'DogStatus',
  'RescueMeta',
  'get_current_timestamp',
  'get_current_date',
  
  # User state
  'UserDogState',
  'UserOverrides',
  'UserPreferences',
  'ScoringConfig',
  
  # Events
  'DogEvent',
  'EventType',
  'EventSource',
  'create_first_seen_event',
  'create_status_change_event',
  'create_website_update_event',
  'create_image_added_event',
  'create_admin_edit_event',
  'create_fb_post_event',
  'detect_changes',
  'events_to_timeline',
]
