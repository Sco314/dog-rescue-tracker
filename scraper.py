#!/usr/bin/env python3
"""
Dog Rescue Scraper - Main Runner
v1.0.0

Scrapes all configured rescue websites, updates database,
detects changes, and sends notifications.

Usage:
  python scraper.py              # Run full scrape
  python scraper.py --test       # Test mode (no notifications)
  python scraper.py --report     # Show current dog summary
  python scraper.py --export     # Export to CSV
"""
import sys
import os
import time
import argparse
from datetime import datetime
from typing import List, Dict

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import RESCUES
from database import (
  init_database, update_dog, mark_dogs_inactive,
  record_scrape_run, get_all_active_dogs, get_high_fit_dogs,
  get_watch_list_dogs, get_pending_notifications, mark_notified
)
from scrapers import PoodlePatchScraper, DoodleRockScraper, DoodleDandyScraper
from notifications import send_notification, is_configured as email_configured
from models import ChangeRecord


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
  
  # Initialize database
  init_database()
  
  all_changes = []
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
      # Scrape dogs
      dogs = scraper.scrape()
      
      # Track IDs for this rescue
      scraped_ids = []
      new_count = 0
      
      # Update database
      for dog in dogs:
        scraped_ids.append(dog.dog_id)
        changes = update_dog(dog)
        all_changes.extend(changes)
        
        # Count new dogs
        for c in changes:
          if c.change_type == "new_dog":
            new_count += 1
      
      # Mark missing dogs as inactive
      if scraped_ids:
        inactive_changes = mark_dogs_inactive(scraped_ids, rescue_config["name"])
        all_changes.extend(inactive_changes)
      
      # Record scrape run
      duration = time.time() - start_time
      change_count = len([c for c in all_changes if c.dog_name])  # Rough count
      record_scrape_run(
        rescue_config["name"],
        len(dogs),
        new_count,
        change_count,
        "",
        duration
      )
      
      total_dogs += len(dogs)
      total_new += new_count
      
      print(f"\n  📊 Summary: {len(dogs)} dogs, {new_count} new, {duration:.1f}s")
      
    except Exception as e:
      error_msg = f"{rescue_config['name']}: {str(e)}"
      errors.append(error_msg)
      print(f"  ❌ Error: {e}")
      
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
  print(f"   Changes detected: {len(all_changes)}")
  if errors:
    print(f"   Errors: {len(errors)}")
    for err in errors:
      print(f"     - {err}")
  
  # Send notifications (unless test mode)
  if all_changes and not test_mode:
    print("\n📧 Sending notifications...")
    
    # Get pending notifications with full dog info
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
    "changes": len(all_changes),
    "errors": errors
  }


def show_report():
  """Show summary report of current dogs"""
  init_database()
  
  print("\n" + "=" * 60)
  print("🐕 DOG RESCUE TRACKER - Current Status")
  print("=" * 60)
  
  # Watch list
  watch_dogs = get_watch_list_dogs()
  print(f"\n🔔 WATCH LIST ({len(watch_dogs)} dogs)")
  print("-" * 40)
  for dog in watch_dogs:
    print(f"  {dog['dog_name']} | {dog['rescue_name']} | {dog['status']} | Fit: {dog['fit_score']}")
  
  # High fit dogs
  high_fit = get_high_fit_dogs(5)
  print(f"\n⭐ HIGH FIT DOGS (score >= 5) ({len(high_fit)} dogs)")
  print("-" * 40)
  for dog in high_fit[:10]:  # Top 10
    print(f"  {dog['dog_name']} ({dog['fit_score']}) | {dog['rescue_name']} | {dog['status']}")
    if dog.get('weight'):
      print(f"    Weight: {dog['weight']}lbs | {dog.get('breed', '?')}")
  
  # All active dogs by rescue
  all_dogs = get_all_active_dogs()
  print(f"\n📋 ALL ACTIVE DOGS ({len(all_dogs)} total)")
  print("-" * 40)
  
  by_rescue = {}
  for dog in all_dogs:
    rescue = dog['rescue_name']
    if rescue not in by_rescue:
      by_rescue[rescue] = []
    by_rescue[rescue].append(dog)
  
  for rescue, dogs in by_rescue.items():
    print(f"\n  {rescue} ({len(dogs)} dogs):")
    for dog in sorted(dogs, key=lambda d: -(d['fit_score'] or 0)):
      status_emoji = {"Available": "✅", "Pending": "⏳", "Upcoming": "🔜"}.get(dog['status'], "❓")
      print(f"    {status_emoji} {dog['dog_name']} (Fit: {dog['fit_score'] or '?'}) - {dog['status']}")


def export_csv():
  """Export current dogs to CSV"""
  import csv
  
  init_database()
  dogs = get_all_active_dogs()
  
  filename = f"dogs_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
  
  with open(filename, "w", newline="") as f:
    if dogs:
      writer = csv.DictWriter(f, fieldnames=dogs[0].keys())
      writer.writeheader()
      writer.writerows(dogs)
  
  print(f"✅ Exported {len(dogs)} dogs to {filename}")


def main():
  parser = argparse.ArgumentParser(description="Dog Rescue Scraper")
  parser.add_argument("--test", action="store_true", help="Test mode (no notifications)")
  parser.add_argument("--report", action="store_true", help="Show current dog summary")
  parser.add_argument("--export", action="store_true", help="Export to CSV")
  
  args = parser.parse_args()
  
  if args.report:
    show_report()
  elif args.export:
    export_csv()
  else:
    run_scrape(test_mode=args.test)


if __name__ == "__main__":
  main()
