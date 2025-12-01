#!/usr/bin/env python3
"""
Site Generator for Dog Rescue Tracker
v1.0.0 - Phase 3 Dashboard Integration

Generates complete static site:
- dashboard.html (main page)
- dogs/*.html (detail pages for each dog)

Usage:
  python generate_site.py                    # Generate to ./site/
  python generate_site.py -o ./docs          # Generate to ./docs/ (for GitHub Pages)
  python generate_site.py --dashboard-only   # Only regenerate dashboard
"""

import os
import argparse
import shutil
from typing import Optional

from dal import get_dal
from dashboard import generate_html_dashboard
from dog_details import generate_dog_details_html


def generate_site(output_dir: str = "site", dashboard_only: bool = False) -> dict:
  """
  Generate complete static site.
  
  Returns:
    dict with generation stats
  """
  dal = get_dal()
  dal.init_database()
  
  stats = {
    "dashboard": False,
    "dog_pages": 0,
    "errors": []
  }
  
  # Create output directories
  os.makedirs(output_dir, exist_ok=True)
  dogs_dir = os.path.join(output_dir, "dogs")
  os.makedirs(dogs_dir, exist_ok=True)
  
  # Generate dashboard
  print("📊 Generating dashboard...")
  try:
    dashboard_path = os.path.join(output_dir, "dashboard.html")
    generate_html_dashboard(dashboard_path)
    stats["dashboard"] = True
  except Exception as e:
    stats["errors"].append(f"Dashboard: {e}")
    print(f"  ❌ Dashboard failed: {e}")
  
  if dashboard_only:
    print(f"\n✅ Dashboard generated in {output_dir}/")
    return stats
  
  # Generate dog detail pages
  dogs = dal.get_all_dogs(active_only=True)
  print(f"\n🐕 Generating {len(dogs)} dog detail pages...")
  
  for dog in dogs:
    try:
      html = generate_dog_details_html(dog, dal)
      filename = f"{dog.dog_id.replace('/', '_')}.html"
      filepath = os.path.join(dogs_dir, filename)
      
      with open(filepath, 'w') as f:
        f.write(html)
      
      stats["dog_pages"] += 1
    except Exception as e:
      stats["errors"].append(f"{dog.dog_id}: {e}")
      print(f"  ❌ {dog.dog_id}: {e}")
  
  print(f"  ✅ Generated {stats['dog_pages']} pages in {dogs_dir}/")
  
  # Create index.html redirect to dashboard
  index_html = """<!DOCTYPE html>
<html>
<head>
  <meta http-equiv="refresh" content="0; url=dashboard.html">
  <title>Redirecting...</title>
</head>
<body>
  <p>Redirecting to <a href="dashboard.html">dashboard</a>...</p>
</body>
</html>
"""
  index_path = os.path.join(output_dir, "index.html")
  with open(index_path, 'w') as f:
    f.write(index_html)
  
  # Summary
  print(f"\n{'='*50}")
  print(f"✅ Site generated in {output_dir}/")
  print(f"   Dashboard: {'✓' if stats['dashboard'] else '✗'}")
  print(f"   Dog pages: {stats['dog_pages']}")
  if stats["errors"]:
    print(f"   Errors: {len(stats['errors'])}")
  print(f"\n📁 Structure:")
  print(f"   {output_dir}/")
  print(f"   ├── index.html (redirect)")
  print(f"   ├── dashboard.html")
  print(f"   └── dogs/")
  print(f"       └── *.html ({stats['dog_pages']} files)")
  
  return stats


def main():
  parser = argparse.ArgumentParser(description="Generate Dog Rescue Tracker static site")
  parser.add_argument("-o", "--output", default="site", help="Output directory (default: site)")
  parser.add_argument("--dashboard-only", action="store_true", help="Only regenerate dashboard")
  parser.add_argument("--clean", action="store_true", help="Clean output directory first")
  
  args = parser.parse_args()
  
  if args.clean and os.path.exists(args.output):
    print(f"🧹 Cleaning {args.output}/...")
    shutil.rmtree(args.output)
  
  generate_site(args.output, args.dashboard_only)


if __name__ == "__main__":
  main()
