#!/usr/bin/env python3
"""
Dog Details Page Generator
v1.0.0 - Phase 2

Generates a clean, professional dog profile page using the new DAL.

Features:
- Header with photo, name, status, key facts
- Fit Score breakdown with edit capability
- Bio & adoption requirements
- Event timeline
- User overrides
- Mobile-friendly

Usage:
  python dog_details.py <dog_id>           # Generate single dog page
  python dog_details.py --all              # Generate all dog pages
  python dog_details.py --server           # Run local server
"""
import os
import sys
import argparse
from datetime import datetime
from typing import Optional
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dal import get_dal, DAL
from schema import Dog, UserDogState, DogEvent, events_to_timeline


def generate_dog_details_html(dog: Dog, dal: DAL, user_id: str = "default_user") -> str:
  """Generate HTML for a single dog's detail page"""
  
  # Get user state and events
  user_state = dal.get_user_dog_state(user_id, dog.dog_id)
  events = dal.get_dog_events(dog.dog_id, limit=20)
  timeline = events_to_timeline(events)
  
  # Compute score with user overrides
  prefs = dal.get_user_preferences(user_id)
  computed_score = dal.compute_fit_score(dog, user_state.overrides, prefs.scoring_config)
  
  # Status styling
  status_colors = {
    "Available": ("#10b981", "✅"),
    "Pending": ("#f59e0b", "⏳"),
    "Upcoming": ("#3b82f6", "🔜"),
    "Adopted": ("#6b7280", "🏠"),
  }
  status_color, status_icon = status_colors.get(dog.status, ("#6b7280", "❓"))
  
  # Watch star
  watch_star = "⭐" if user_state.favorite else "☆"
  watch_class = "active" if user_state.favorite else ""
  
  # Image URL with fallback
  image_url = dog.primary_image_url or dog.image_url or ""
  image_html = f'<img src="{image_url}" alt="{dog.dog_name}" class="dog-photo">' if image_url else '<div class="dog-photo-placeholder">🐕</div>'
  
  # Build timeline HTML
  timeline_html = ""
  if timeline:
    for item in timeline[:10]:
      date_display = item['date'][:10] if item.get('date') else ""
      timeline_html += f'''
        <div class="timeline-item">
          <span class="timeline-icon">{item.get('icon', '📋')}</span>
          <span class="timeline-date">{date_display}</span>
          <span class="timeline-text">{item.get('summary', '')}</span>
        </div>
      '''
  else:
    timeline_html = '<div class="timeline-empty">No events recorded yet</div>'
  
  # Build score breakdown
  breakdown_html = generate_score_breakdown_html(dog, user_state, prefs.scoring_config, dal)
  
  # Compatibility icons
  compat_dogs = get_compat_display(dog.good_with_dogs)
  compat_kids = get_compat_display(dog.good_with_kids)
  compat_cats = get_compat_display(dog.good_with_cats)
  
  # Bio text
  bio_text = ""
  if dog.rescue_meta and dog.rescue_meta.bio_text:
    bio_text = dog.rescue_meta.bio_text[:1000]
  
  # Adoption requirements
  adoption_req = ""
  if dog.rescue_meta and dog.rescue_meta.adoption_requirements_text:
    adoption_req = dog.rescue_meta.adoption_requirements_text
  
  html = f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{dog.dog_name} - Dog Details</title>
  <style>
    :root {{
      --bg-primary: #121212;
      --bg-secondary: #1e1e1e;
      --bg-card: #252525;
      --text-primary: #e2e8f0;
      --text-secondary: #94a3b8;
      --accent: #3b82f6;
      --success: #10b981;
      --warning: #f59e0b;
      --danger: #ef4444;
      --star: #fbbf24;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      background: var(--bg-primary);
      color: var(--text-primary);
      line-height: 1.6;
    }}
    
    /* Header */
    .header {{
      background: var(--bg-secondary);
      padding: 15px 20px;
      display: flex;
      align-items: center;
      gap: 15px;
      border-bottom: 1px solid #333;
    }}
    .back-btn {{
      background: none;
      border: 1px solid #444;
      color: var(--text-primary);
      padding: 8px 16px;
      border-radius: 6px;
      cursor: pointer;
      text-decoration: none;
      font-size: 0.9rem;
    }}
    .back-btn:hover {{ background: #333; }}
    .header-title {{
      flex: 1;
      font-size: 1.1rem;
      color: var(--text-secondary);
    }}
    
    /* Main Layout */
    .container {{
      max-width: 1000px;
      margin: 0 auto;
      padding: 20px;
    }}
    
    /* Hero Section */
    .hero {{
      display: grid;
      grid-template-columns: 300px 1fr;
      gap: 30px;
      margin-bottom: 30px;
    }}
    @media (max-width: 768px) {{
      .hero {{ grid-template-columns: 1fr; }}
    }}
    
    .dog-photo {{
      width: 100%;
      aspect-ratio: 1;
      object-fit: cover;
      border-radius: 12px;
      background: var(--bg-card);
    }}
    .dog-photo-placeholder {{
      width: 100%;
      aspect-ratio: 1;
      background: var(--bg-card);
      border-radius: 12px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 5rem;
    }}
    
    .hero-info {{
      display: flex;
      flex-direction: column;
      gap: 15px;
    }}
    
    .name-row {{
      display: flex;
      align-items: center;
      gap: 15px;
    }}
    .dog-name {{
      font-size: 2.5rem;
      font-weight: 700;
    }}
    .watch-btn {{
      font-size: 2rem;
      background: none;
      border: none;
      cursor: pointer;
      opacity: 0.5;
      transition: all 0.2s;
    }}
    .watch-btn:hover, .watch-btn.active {{
      opacity: 1;
      transform: scale(1.1);
    }}
    
    .status-badge {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 6px 14px;
      border-radius: 20px;
      font-weight: 600;
      font-size: 0.9rem;
      background: {status_color}22;
      color: {status_color};
      border: 1px solid {status_color}44;
    }}
    
    .key-facts {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
      gap: 12px;
      margin-top: 10px;
    }}
    .fact {{
      background: var(--bg-card);
      padding: 12px;
      border-radius: 8px;
      text-align: center;
    }}
    .fact-label {{
      font-size: 0.75rem;
      color: var(--text-secondary);
      text-transform: uppercase;
      margin-bottom: 4px;
    }}
    .fact-value {{
      font-size: 1.1rem;
      font-weight: 600;
    }}
    
    .rescue-link {{
      margin-top: 15px;
    }}
    .rescue-link a {{
      color: var(--accent);
      text-decoration: none;
      font-size: 0.9rem;
    }}
    .rescue-link a:hover {{ text-decoration: underline; }}
    
    /* Sections */
    .section {{
      background: var(--bg-card);
      border-radius: 12px;
      padding: 20px;
      margin-bottom: 20px;
    }}
    .section-title {{
      font-size: 1.1rem;
      font-weight: 600;
      margin-bottom: 15px;
      padding-bottom: 10px;
      border-bottom: 1px solid #333;
    }}
    
    /* Fit Score */
    .score-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 15px;
    }}
    .score-value {{
      font-size: 2.5rem;
      font-weight: 700;
      color: var(--accent);
      background: rgba(59, 130, 246, 0.15);
      padding: 8px 20px;
      border-radius: 10px;
    }}
    .score-items {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
    }}
    .score-item {{
      display: flex;
      justify-content: space-between;
      padding: 8px 12px;
      background: var(--bg-secondary);
      border-radius: 6px;
    }}
    .score-label {{ color: var(--text-secondary); }}
    .score-points {{ font-weight: 600; }}
    .score-points.positive {{ color: var(--success); }}
    .score-points.negative {{ color: var(--danger); }}
    .score-points.neutral {{ color: var(--text-secondary); }}
    
    .override-note {{
      margin-top: 15px;
      padding: 10px;
      background: var(--warning)22;
      border: 1px solid var(--warning)44;
      border-radius: 6px;
      font-size: 0.85rem;
      color: var(--warning);
    }}
    
    /* Compatibility */
    .compat-grid {{
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 15px;
    }}
    .compat-item {{
      text-align: center;
      padding: 15px;
      background: var(--bg-secondary);
      border-radius: 8px;
    }}
    .compat-icon {{ font-size: 1.5rem; margin-bottom: 5px; }}
    .compat-label {{ font-size: 0.85rem; color: var(--text-secondary); }}
    .compat-value {{ font-weight: 600; margin-top: 5px; }}
    .compat-yes {{ color: var(--success); }}
    .compat-no {{ color: var(--danger); }}
    .compat-unknown {{ color: var(--text-secondary); }}
    
    /* Bio */
    .bio-text {{
      line-height: 1.8;
      color: var(--text-secondary);
    }}
    
    /* Timeline */
    .timeline-item {{
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 10px 0;
      border-bottom: 1px solid #333;
    }}
    .timeline-item:last-child {{ border-bottom: none; }}
    .timeline-icon {{ font-size: 1.2rem; }}
    .timeline-date {{
      font-size: 0.8rem;
      color: var(--text-secondary);
      min-width: 80px;
    }}
    .timeline-text {{ flex: 1; }}
    .timeline-empty {{
      color: var(--text-secondary);
      text-align: center;
      padding: 20px;
    }}
    
    /* Notes */
    .notes-textarea {{
      width: 100%;
      min-height: 100px;
      padding: 12px;
      background: var(--bg-secondary);
      border: 1px solid #333;
      border-radius: 8px;
      color: var(--text-primary);
      font-family: inherit;
      font-size: 0.9rem;
      resize: vertical;
    }}
    .notes-textarea:focus {{
      outline: none;
      border-color: var(--accent);
    }}
    
    .save-btn {{
      margin-top: 15px;
      padding: 12px 24px;
      background: var(--success);
      border: none;
      border-radius: 8px;
      color: white;
      font-weight: 600;
      cursor: pointer;
    }}
    .save-btn:hover {{ opacity: 0.9; }}
    
    /* Toast */
    .toast {{
      position: fixed;
      bottom: 20px;
      right: 20px;
      padding: 15px 25px;
      background: var(--success);
      color: white;
      border-radius: 8px;
      z-index: 1000;
      display: none;
    }}
    .toast.show {{ display: block; animation: slideIn 0.3s ease; }}
    @keyframes slideIn {{
      from {{ transform: translateX(100%); opacity: 0; }}
      to {{ transform: translateX(0); opacity: 1; }}
    }}
  </style>
</head>
<body>
  <div class="header">
    <a href="dashboard.html" class="back-btn">← Back to Dashboard</a>
    <div class="header-title">{dog.rescue_name}</div>
  </div>
  
  <div class="container">
    <!-- Hero Section -->
    <div class="hero">
      <div class="photo-column">
        {image_html}
      </div>
      
      <div class="hero-info">
        <div class="name-row">
          <h1 class="dog-name">{dog.dog_name}</h1>
          <button class="watch-btn {watch_class}" onclick="toggleWatch()" title="Add to watch list">{watch_star}</button>
        </div>
        
        <div class="status-badge">{status_icon} {dog.status}</div>
        
        <div class="key-facts">
          <div class="fact">
            <div class="fact-label">Breed</div>
            <div class="fact-value">{dog.breed or "Unknown"}</div>
          </div>
          <div class="fact">
            <div class="fact-label">Weight</div>
            <div class="fact-value">{f"{dog.weight_lbs or dog.weight} lbs" if (dog.weight_lbs or dog.weight) else "?"}</div>
          </div>
          <div class="fact">
            <div class="fact-label">Age</div>
            <div class="fact-value">{dog.age_display or dog.age_range or "?"}</div>
          </div>
          <div class="fact">
            <div class="fact-label">Sex</div>
            <div class="fact-value">{dog.sex or "?"}</div>
          </div>
          <div class="fact">
            <div class="fact-label">Location</div>
            <div class="fact-value">{dog.location or "?"}</div>
          </div>
        </div>
        
        <div class="rescue-link">
          <a href="{dog.rescue_dog_url or dog.source_url or '#'}" target="_blank">
            🔗 View on {dog.rescue_name} website
          </a>
        </div>
      </div>
    </div>
    
    <!-- Fit Score Section -->
    <div class="section">
      <div class="score-header">
        <h2 class="section-title" style="border: none; margin: 0; padding: 0;">Fit Score</h2>
        <div class="score-value">{computed_score}</div>
      </div>
      
      <div class="score-items">
        {breakdown_html}
      </div>
      
      {"<div class='override-note'>⚠️ You have custom overrides applied to this dog</div>" if user_state.overrides.has_overrides() else ""}
    </div>
    
    <!-- Compatibility Section -->
    <div class="section">
      <h2 class="section-title">Compatibility</h2>
      <div class="compat-grid">
        <div class="compat-item">
          <div class="compat-icon">🐕</div>
          <div class="compat-label">Other Dogs</div>
          <div class="compat-value {compat_dogs[1]}">{compat_dogs[0]}</div>
        </div>
        <div class="compat-item">
          <div class="compat-icon">👶</div>
          <div class="compat-label">Children</div>
          <div class="compat-value {compat_kids[1]}">{compat_kids[0]}</div>
        </div>
        <div class="compat-item">
          <div class="compat-icon">🐱</div>
          <div class="compat-label">Cats</div>
          <div class="compat-value {compat_cats[1]}">{compat_cats[0]}</div>
        </div>
      </div>
    </div>
    
    <!-- Bio Section -->
    {f'''<div class="section">
      <h2 class="section-title">About {dog.dog_name}</h2>
      <p class="bio-text">{bio_text}</p>
    </div>''' if bio_text else ''}
    
    <!-- Adoption Requirements -->
    {f'''<div class="section">
      <h2 class="section-title">Adoption Requirements</h2>
      <p class="bio-text">{adoption_req}</p>
      {f'<p style="margin-top: 15px;"><strong>Adoption Fee:</strong> {dog.adoption_fee}</p>' if dog.adoption_fee else ''}
    </div>''' if adoption_req or dog.adoption_fee else ''}
    
    <!-- Timeline Section -->
    <div class="section">
      <h2 class="section-title">Timeline</h2>
      <div class="timeline">
        {timeline_html}
      </div>
    </div>
    
    <!-- Notes Section -->
    <div class="section">
      <h2 class="section-title">Your Notes</h2>
      <textarea class="notes-textarea" id="userNotes" placeholder="Add your private notes about this dog...">{user_state.notes}</textarea>
      <button class="save-btn" onclick="saveNotes()">Save Notes</button>
    </div>
  </div>
  
  <div class="toast" id="toast">Saved!</div>
  
  <script>
    const dogId = '{dog.dog_id}';
    const dogData = {json.dumps(dog.to_legacy_dict())};
    
    function toggleWatch() {{
      const btn = document.querySelector('.watch-btn');
      const isActive = btn.classList.contains('active');
      btn.classList.toggle('active');
      btn.textContent = isActive ? '☆' : '⭐';
      showToast(isActive ? 'Removed from watch list' : 'Added to watch list');
      // TODO: Save to backend
    }}
    
    function saveNotes() {{
      const notes = document.getElementById('userNotes').value;
      showToast('Notes saved!');
      // TODO: Save to backend
    }}
    
    function showToast(message) {{
      const toast = document.getElementById('toast');
      toast.textContent = message;
      toast.classList.add('show');
      setTimeout(() => toast.classList.remove('show'), 2000);
    }}
  </script>
</body>
</html>
'''
  return html


def generate_score_breakdown_html(dog: Dog, user_state: UserDogState, config, dal: DAL) -> str:
  """Generate HTML for score breakdown items"""
  items = []
  
  # Weight
  weight = dog.weight_lbs or dog.weight
  if weight and weight >= 40:
    items.append(("Weight ≥40 lbs", 2, "positive"))
  elif weight:
    items.append((f"Weight {weight} lbs", 0, "neutral"))
  else:
    items.append(("Weight unknown", 0, "neutral"))
  
  # Age
  age_str = dog.age_display or dog.age_range or ""
  age_years = dal._parse_age_to_years(age_str)
  if age_years:
    if age_years < 2:
      items.append((f"Age: {age_str}", 2, "positive"))
    elif age_years < 4:
      items.append((f"Age: {age_str}", 1, "positive"))
    elif age_years < 6:
      items.append((f"Age: {age_str}", 0, "neutral"))
    else:
      items.append((f"Age: {age_str}", -4, "negative"))
  else:
    items.append(("Age unknown", 0, "neutral"))
  
  # Shedding
  shedding = dog.shedding or "Unknown"
  shed_scores = {"None": (2, "positive"), "Low": (1, "positive"), "Moderate": (0, "neutral"), "High": (-1, "negative"), "Unknown": (1, "positive")}
  score, cls = shed_scores.get(shedding, (1, "positive"))
  items.append((f"Shedding: {shedding}", score, cls))
  
  # Energy
  energy = dog.energy_level or "Unknown"
  if energy in ["Low", "Medium"]:
    items.append((f"Energy: {energy}", 2, "positive"))
  elif energy == "High":
    items.append((f"Energy: {energy}", 0, "neutral"))
  else:
    items.append(("Energy: Unknown", 1, "positive"))
  
  # Good with dogs
  if dog.good_with_dogs == "Yes":
    items.append(("Good with dogs", 2, "positive"))
  elif dog.good_with_dogs == "No":
    items.append(("Not good with dogs", 0, "neutral"))
  else:
    items.append(("Dogs: Unknown", 0, "neutral"))
  
  # Good with kids
  if dog.good_with_kids == "Yes":
    items.append(("Good with kids", 1, "positive"))
  else:
    items.append(("Kids: Unknown", 0, "neutral"))
  
  # Good with cats
  if dog.good_with_cats == "Yes":
    items.append(("Good with cats", 1, "positive"))
  else:
    items.append(("Cats: Unknown", 0, "neutral"))
  
  # Breed bonus
  breed = dog.breed or ""
  if any(term in breed.lower() for term in ["doodle", "poodle", "poo"]):
    items.append(("Doodle/Poodle breed", 1, "positive"))
  
  # Pending penalty
  if dog.status == "Pending":
    items.append(("Pending status", -8, "negative"))
  
  # User adjustments
  if user_state.overrides.manual_score_adjustment:
    adj = user_state.overrides.manual_score_adjustment
    cls = "positive" if adj > 0 else "negative"
    items.append((f"Your adjustment", adj, cls))
  
  # Build HTML
  html = ""
  for label, points, cls in items:
    sign = "+" if points > 0 else ""
    html += f'''
      <div class="score-item">
        <span class="score-label">{label}</span>
        <span class="score-points {cls}">{sign}{points}</span>
      </div>
    '''
  return html


def get_compat_display(value: Optional[str]) -> tuple:
  """Get display text and CSS class for compatibility value"""
  if value == "Yes":
    return ("Yes ✓", "compat-yes")
  elif value == "No":
    return ("No ✗", "compat-no")
  else:
    return ("Unknown", "compat-unknown")


def generate_dog_page(dog_id: str, output_dir: str = "dog_pages") -> Optional[str]:
  """Generate a detail page for a specific dog"""
  dal = get_dal()
  dal.init_database()
  
  dog = dal.get_dog(dog_id)
  if not dog:
    print(f"❌ Dog not found: {dog_id}")
    return None
  
  html = generate_dog_details_html(dog, dal)
  
  # Ensure output directory exists
  os.makedirs(output_dir, exist_ok=True)
  
  # Write file
  filename = f"{dog_id.replace('/', '_')}.html"
  filepath = os.path.join(output_dir, filename)
  
  with open(filepath, 'w') as f:
    f.write(html)
  
  print(f"✅ Generated: {filepath}")
  return filepath


def generate_all_dog_pages(output_dir: str = "dog_pages"):
  """Generate detail pages for all active dogs"""
  dal = get_dal()
  dal.init_database()
  
  dogs = dal.get_all_dogs(active_only=True)
  print(f"📄 Generating {len(dogs)} dog detail pages...")
  
  for dog in dogs:
    html = generate_dog_details_html(dog, dal)
    
    os.makedirs(output_dir, exist_ok=True)
    filename = f"{dog.dog_id.replace('/', '_')}.html"
    filepath = os.path.join(output_dir, filename)
    
    with open(filepath, 'w') as f:
      f.write(html)
  
  print(f"✅ Generated {len(dogs)} pages in {output_dir}/")


def main():
  parser = argparse.ArgumentParser(description="Dog Details Page Generator")
  parser.add_argument("dog_id", nargs="?", help="Dog ID to generate page for")
  parser.add_argument("--all", action="store_true", help="Generate pages for all dogs")
  parser.add_argument("-o", "--output", default="dog_pages", help="Output directory")
  
  args = parser.parse_args()
  
  if args.all:
    generate_all_dog_pages(args.output)
  elif args.dog_id:
    generate_dog_page(args.dog_id, args.output)
  else:
    # Show available dogs
    dal = get_dal()
    dal.init_database()
    dogs = dal.get_all_dogs(active_only=True)
    
    print("Available dogs:")
    for dog in dogs[:20]:
      print(f"  {dog.dog_id}: {dog.dog_name} ({dog.rescue_name})")
    if len(dogs) > 20:
      print(f"  ... and {len(dogs) - 20} more")
    print("\nUsage: python dog_details.py <dog_id>")
    print("       python dog_details.py --all")


if __name__ == "__main__":
  main()
