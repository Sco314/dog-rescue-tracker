#!/usr/bin/env python3
"""
Dog Rescue Scraper - Main Runner
v2.0.0 - Phase 1 Integration

Scrapes all configured rescue websites, updates database via DAL,
detects changes with event system, and sends notifications.

Changes from v1.0:
- Uses DAL for all data operations
- Events generated automatically
- User overrides applied via DAL
- Backward compatible with existing data

Usage:
  python scraper.py              # Run full scrape
  python scraper.py --test       # Test mode (no notifications)
  python scraper.py --report     # Show current dog summary
  python scraper.py --export     # Export to CSV
"""
import sys
import os
import time
import json
import argparse
from datetime import datetime
from typing import List, Dict

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import RESCUES
from dal import DAL, get_dal
from scrapers import PoodlePatchScraper, DoodleRockScraper, DoodleDandyScraper
from notifications import send_notification, is_configured as email_configured
from schema import Dog, get_current_timestamp

# Legacy imports for backward compatibility
from database import (
  init_database as legacy_init_database,
  record_scrape_run,
  get_pending_notifications,
  mark_notified,
  get_connection
)


def get_scraper(rescue_key: str, config: dict):
  """Get appropriate scraper for rescue"""
  scrapers = {
    "poodle_patch": PoodlePatchScraper,
    "doodle_rock": DoodleRockScraper,
    "doodle_dandy": DoodleDandyScraper,
  }
  
  scraper_class = scrapers.get(rescue_key)
  if scraper_class:
    return scraper_class(config)
  return None


def run_scrape(test_mode: bool = False) -> Dict:
  """
  Run full scrape of all configured rescues
  
  Returns:
    Dict with scrape results summary
  """
  print("\n" + "=" * 60)
  print("🐕 DOG RESCUE SCRAPER - Starting")
  print(f"   Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
  print("=" * 60)
  
  # Initialize DAL and database
  dal = get_dal()
  dal.init_database()
  
  all_events = []
  total_dogs = 0
  total_new = 0
  errors = []
  
  # Scrape each rescue
  for rescue_key, rescue_config in RESCUES.items():
    print(f"\n{'─' * 40}")
    print(f"📍 {rescue_config['name']}")
    print(f"{'─' * 40}")
    
    start_time = time.time()
    scraper = get_scraper(rescue_key, rescue_config)
    
    if not scraper:
      print(f"  ⚠️ No scraper configured for {rescue_key}")
      continue
    
    try:
      # Scrape dogs (returns legacy Dog objects from models.py)
      legacy_dogs = scraper.scrape()
      
      # Track IDs for this rescue
      scraped_ids = []
      new_count = 0
      
      # Update database via DAL
      for legacy_dog in legacy_dogs:
        scraped_ids.append(legacy_dog.dog_id)
        
        # Convert legacy Dog to new schema Dog
        # (For now, scrapers still use legacy Dog, we convert here)
        dog = _legacy_to_new_dog(legacy_dog)
        
        # Save via DAL - returns events
        events = dal.save_dog(dog)
        all_events.extend(events)
        
        # Count new dogs
        for event in events:
          if event.event_type == "first_seen":
            new_count += 1
      
      # Mark missing dogs as inactive
      if scraped_ids:
        inactive_events = dal.mark_dogs_inactive(scraped_ids, rescue_config["name"])
        all_events.extend(inactive_events)
      
      # Record scrape run (legacy table for analytics)
      duration = time.time() - start_time
      record_scrape_run(
        rescue_config["name"],
        len(legacy_dogs),
        new_count,
        len(all_events),
        "",
        duration
      )
      
      total_dogs += len(legacy_dogs)
      total_new += new_count
      
      print(f"\n  📊 Summary: {len(legacy_dogs)} dogs, {new_count} new, {duration:.1f}s")
      
    except Exception as e:
      error_msg = f"{rescue_config['name']}: {str(e)}"
      errors.append(error_msg)
      print(f"  ❌ Error: {e}")
      import traceback
      traceback.print_exc()
      
      # Record failed run
      record_scrape_run(
        rescue_config["name"],
        0, 0, 0,
        str(e),
        time.time() - start_time
      )
  
  # Summary
  print("\n" + "=" * 60)
  print("📊 SCRAPE COMPLETE")
  print("=" * 60)
  print(f"   Total dogs found: {total_dogs}")
  print(f"   New dogs: {total_new}")
  print(f"   Events generated: {len(all_events)}")
  if errors:
    print(f"   Errors: {len(errors)}")
    for err in errors:
      print(f"     - {err}")
  
  # Apply user overrides via DAL
  print("\n📋 Applying user overrides...")
  _apply_user_overrides_via_dal(dal)
  
  # Send notifications (unless test mode)
  if all_events and not test_mode:
    print("\n📧 Sending notifications...")
    
    # Get pending notifications with full dog info (legacy system)
    pending = get_pending_notifications()
    
    if pending:
      success = send_notification(pending)
      if success:
        # Mark as notified
        mark_notified([p["id"] for p in pending])
    else:
      print("  ℹ️ No pending notifications")
  elif test_mode:
    print("\n⚠️ Test mode - notifications skipped")
  
  return {
    "total_dogs": total_dogs,
    "new_dogs": total_new,
    "events": len(all_events),
    "errors": errors
  }


def _legacy_to_new_dog(legacy_dog) -> Dog:
  """Convert legacy models.Dog to new schema.Dog"""
  from schema import Dog as NewDog, RescueMeta
  
  # Create rescue meta from legacy notes
  rescue_meta = RescueMeta(
    bio_text=legacy_dog.notes if hasattr(legacy_dog, 'notes') else "",
    adoption_requirements_text=legacy_dog.adoption_req if hasattr(legacy_dog, 'adoption_req') else "",
  )
  
  return NewDog(
    dog_id=legacy_dog.dog_id,
    dog_name=legacy_dog.dog_name,
    rescue_name=legacy_dog.rescue_name,
    rescue_dog_url=legacy_dog.source_url if hasattr(legacy_dog, 'source_url') else None,
    platform=legacy_dog.platform if hasattr(legacy_dog, 'platform') else "",
    status=legacy_dog.status if hasattr(legacy_dog, 'status') else "Unknown",
    is_active=True,
    weight_lbs=legacy_dog.weight if hasattr(legacy_dog, 'weight') else None,
    age_display=legacy_dog.age_range if hasattr(legacy_dog, 'age_range') else None,
    sex=legacy_dog.sex if hasattr(legacy_dog, 'sex') else None,
    breed=legacy_dog.breed if hasattr(legacy_dog, 'breed') else None,
    location=legacy_dog.location if hasattr(legacy_dog, 'location') else None,
    good_with_dogs=legacy_dog.good_with_dogs if hasattr(legacy_dog, 'good_with_dogs') else None,
    good_with_cats=legacy_dog.good_with_cats if hasattr(legacy_dog, 'good_with_cats') else None,
    good_with_kids=legacy_dog.good_with_kids if hasattr(legacy_dog, 'good_with_kids') else None,
    shedding=legacy_dog.shedding if hasattr(legacy_dog, 'shedding') else None,
    energy_level=legacy_dog.energy_level if hasattr(legacy_dog, 'energy_level') else None,
    special_needs=(legacy_dog.special_needs == "Yes") if hasattr(legacy_dog, 'special_needs') else False,
    adoption_fee=legacy_dog.adoption_fee if hasattr(legacy_dog, 'adoption_fee') else None,
    primary_image_url=legacy_dog.image_url if hasattr(legacy_dog, 'image_url') else None,
    base_fit_score=legacy_dog.fit_score if hasattr(legacy_dog, 'fit_score') else None,
    watch_list=legacy_dog.watch_list if hasattr(legacy_dog, 'watch_list') else "",
    rescue_meta=rescue_meta,
    # Legacy aliases for compatibility
    source_url=legacy_dog.source_url if hasattr(legacy_dog, 'source_url') else None,
    image_url=legacy_dog.image_url if hasattr(legacy_dog, 'image_url') else None,
    age_range=legacy_dog.age_range if hasattr(legacy_dog, 'age_range') else None,
    weight=legacy_dog.weight if hasattr(legacy_dog, 'weight') else None,
    fit_score=legacy_dog.fit_score if hasattr(legacy_dog, 'fit_score') else None,
  )


def _apply_user_overrides_via_dal(dal: DAL):
  """Apply user overrides using DAL"""
  # Load user preferences
  prefs = dal.get_user_preferences("default_user")
  
  # Get all active dogs
  dogs = dal.get_all_dogs(active_only=True)
  
  applied_count = 0
  for dog in dogs:
    # Get user state for this dog
    state = dal.get_user_dog_state("default_user", dog.dog_id)
    
    # If user has overrides, recompute score
    if state.overrides.has_overrides():
      new_score = dal.compute_fit_score(dog, state.overrides, prefs.scoring_config)
      
      # Update in database
      with dal._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
          "UPDATE dogs SET fit_score = ? WHERE dog_id = ?",
          (new_score, dog.dog_id)
        )
      applied_count += 1
  
  if applied_count > 0:
    print(f"  ✅ Applied overrides to {applied_count} dogs")


def show_report():
  """Show summary report of current dogs"""
  dal = get_dal()
  dal.init_database()
  
  print("\n" + "=" * 60)
  print("🐕 DOG RESCUE TRACKER - Current Status")
  print("=" * 60)
  
  all_dogs = dal.get_all_dogs(active_only=True)
  
  # Separate by status
  watch_dogs = [d for d in all_dogs if d.watch_list == "Yes"]
  high_fit = [d for d in all_dogs if (d.fit_score or 0) >= 5]
  
  # Watch list
  print(f"\n🔔 WATCH LIST ({len(watch_dogs)} dogs)")
  print("-" * 40)
  for dog in watch_dogs:
    print(f"  {dog.dog_name} | {dog.rescue_name} | {dog.status} | Fit: {dog.fit_score}")
  
  # High fit dogs
  print(f"\n⭐ HIGH FIT DOGS (score >= 5) ({len(high_fit)} dogs)")
  print("-" * 40)
  high_fit_sorted = sorted(high_fit, key=lambda d: -(d.fit_score or 0))
  for dog in high_fit_sorted[:10]:  # Top 10
    print(f"  {dog.dog_name} ({dog.fit_score}) | {dog.rescue_name} | {dog.status}")
    if dog.weight_lbs:
      print(f"    Weight: {dog.weight_lbs}lbs | {dog.breed or '?'}")
  
  # All active dogs by rescue
  print(f"\n📋 ALL ACTIVE DOGS ({len(all_dogs)} total)")
  print("-" * 40)
  
  by_rescue = {}
  for dog in all_dogs:
    rescue = dog.rescue_name
    if rescue not in by_rescue:
      by_rescue[rescue] = []
    by_rescue[rescue].append(dog)
  
  for rescue, dogs in by_rescue.items():
    print(f"\n  {rescue} ({len(dogs)} dogs):")
    for dog in sorted(dogs, key=lambda d: -(d.fit_score or 0)):
      status_emoji = {"Available": "✅", "Pending": "⏳", "Upcoming": "🔜"}.get(dog.status, "❓")
      print(f"    {status_emoji} {dog.dog_name} (Fit: {dog.fit_score or '?'}) - {dog.status}")


def show_events(dog_id: str = None, limit: int = 20):
  """Show recent events"""
  dal = get_dal()
  dal.init_database()
  
  print("\n" + "=" * 60)
  print("📋 EVENT TIMELINE")
  print("=" * 60)
  
  if dog_id:
    events = dal.get_dog_events(dog_id, limit=limit)
    dog = dal.get_dog(dog_id)
    if dog:
      print(f"\nEvents for: {dog.dog_name}")
  else:
    events = dal.get_recent_events(limit=limit)
    print(f"\nRecent events (all dogs)")
  
  print("-" * 40)
  
  if not events:
    print("  No events found")
    return
  
  for event in events:
    icon = {
      "first_seen": "🆕",
      "status_change": "📢",
      "website_update": "📝",
      "fb_post": "📘",
      "admin_edit": "✏️",
    }.get(event.event_type, "📋")
    
    date_str = event.timestamp[:10] if event.timestamp else "?"
    print(f"  {icon} [{date_str}] {event.summary}")


def export_csv():
  """Export current dogs to CSV"""
  import csv
  
  dal = get_dal()
  dal.init_database()
  
  dogs = dal.get_all_dogs(active_only=True)
  
  filename = f"dogs_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
  
  with open(filename, "w", newline="") as f:
    if dogs:
      # Convert to legacy dict format for CSV
      rows = [d.to_legacy_dict() for d in dogs]
      writer = csv.DictWriter(f, fieldnames=rows[0].keys())
      writer.writeheader()
      writer.writerows(rows)
  
  print(f"✅ Exported {len(dogs)} dogs to {filename}")


def main():
  parser = argparse.ArgumentParser(description="Dog Rescue Scraper v2.0")
  parser.add_argument("--test", action="store_true", help="Test mode (no notifications)")
  parser.add_argument("--report", action="store_true", help="Show current dog summary")
  parser.add_argument("--events", action="store_true", help="Show recent events")
  parser.add_argument("--dog", type=str, help="Show events for specific dog ID")
  parser.add_argument("--export", action="store_true", help="Export to CSV")
  
  args = parser.parse_args()
  
  if args.report:
    show_report()
  elif args.events or args.dog:
    show_events(dog_id=args.dog)
  elif args.export:
    export_csv()
  else:
    run_scrape(test_mode=args.test)


if __name__ == "__main__":
  main()
