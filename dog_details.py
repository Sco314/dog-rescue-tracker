#!/usr/bin/env python3
"""
Dog Details Page Generator
v2.0.0 - Phase 2 (Editable)

Generates a clean, professional dog profile page with editable scoring.

Features:
- Header with photo, name, status, key facts
- Editable Fit Score with +/- buttons
- Editable parameters (shedding, energy, compatibility) as dropdowns
- Compatibility merged into Fit Score section
- Link to scoring settings
- Save functionality that persists to user_overrides.json
- Event timeline
- Mobile-friendly

Usage:
  python dog_details.py <dog_id>           # Generate single dog page
  python dog_details.py --all              # Generate all dog pages
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
  """Generate HTML for a single dog's detail page with editable scoring"""
  
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
  
  # Bio text
  bio_text = ""
  if dog.rescue_meta and dog.rescue_meta.bio_text:
    bio_text = dog.rescue_meta.bio_text[:1000]
  
  # Adoption requirements
  adoption_req = ""
  if dog.rescue_meta and dog.rescue_meta.adoption_requirements_text:
    adoption_req = dog.rescue_meta.adoption_requirements_text
  
  # Get effective values (user override or rescue value)
  eff_weight = user_state.overrides.weight if user_state.overrides.weight is not None else (dog.weight_lbs or dog.weight)
  eff_age = user_state.overrides.age_years if user_state.overrides.age_years is not None else dal._parse_age_to_years(dog.age_display or dog.age_range or "")
  eff_shedding = user_state.overrides.shedding or dog.shedding or "Unknown"
  eff_energy = user_state.overrides.energy_level or dog.energy_level or "Unknown"
  eff_dogs = user_state.overrides.good_with_dogs or dog.good_with_dogs or "Unknown"
  eff_kids = user_state.overrides.good_with_kids or dog.good_with_kids or "Unknown"
  eff_cats = user_state.overrides.good_with_cats or dog.good_with_cats or "Unknown"
  # Breed bonus: Yes if doodle/poodle, can be overridden
  orig_breed_bonus = "Yes" if any(term in (dog.breed or "").lower() for term in ["doodle", "poodle", "poo"]) else "No"
  eff_breed = user_state.overrides.breed_bonus if user_state.overrides.breed_bonus else orig_breed_bonus
  score_modifier = user_state.overrides.manual_score_adjustment or 0
  
  # Original rescue values for display
  orig_weight = dog.weight_lbs or dog.weight
  orig_age = dal._parse_age_to_years(dog.age_display or dog.age_range or "")
  orig_shedding = dog.shedding or "Unknown"
  orig_energy = dog.energy_level or "Unknown"
  orig_dogs = dog.good_with_dogs or "Unknown"
  orig_kids = dog.good_with_kids or "Unknown"
  orig_cats = dog.good_with_cats or "Unknown"

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
    .header-title {{ flex: 1; font-size: 1.1rem; color: var(--text-secondary); }}
    
    .container {{ max-width: 1000px; margin: 0 auto; padding: 20px; }}
    
    .hero {{
      display: grid;
      grid-template-columns: 280px 1fr;
      gap: 25px;
      margin-bottom: 25px;
    }}
    @media (max-width: 768px) {{ .hero {{ grid-template-columns: 1fr; }} }}
    
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
    
    .hero-info {{ display: flex; flex-direction: column; gap: 12px; }}
    .name-row {{ display: flex; align-items: center; gap: 15px; }}
    .dog-name {{ font-size: 2.2rem; font-weight: 700; }}
    .watch-btn {{
      font-size: 1.8rem;
      background: none;
      border: none;
      cursor: pointer;
      opacity: 0.5;
      transition: all 0.2s;
    }}
    .watch-btn:hover, .watch-btn.active {{ opacity: 1; transform: scale(1.1); }}
    
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
      width: fit-content;
    }}
    
    .key-facts {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(100px, 1fr));
      gap: 10px;
      margin-top: 8px;
    }}
    .fact {{
      background: var(--bg-card);
      padding: 10px;
      border-radius: 8px;
      text-align: center;
    }}
    .fact-label {{ font-size: 0.7rem; color: var(--text-secondary); text-transform: uppercase; margin-bottom: 2px; }}
    .fact-value {{ font-size: 1rem; font-weight: 600; }}
    
    .rescue-link {{ margin-top: 10px; }}
    .rescue-link a {{ color: var(--accent); text-decoration: none; font-size: 0.85rem; }}
    .rescue-link a:hover {{ text-decoration: underline; }}
    
    .section {{
      background: var(--bg-card);
      border-radius: 12px;
      padding: 20px;
      margin-bottom: 20px;
    }}
    .section-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 15px;
      padding-bottom: 12px;
      border-bottom: 1px solid #333;
    }}
    .section-title {{ font-size: 1.1rem; font-weight: 600; }}
    .settings-link {{
      color: var(--text-secondary);
      text-decoration: none;
      font-size: 0.8rem;
    }}
    .settings-link:hover {{ color: var(--accent); }}
    
    /* Score Header */
    .score-main {{
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 15px;
      margin-bottom: 20px;
      padding: 15px;
      background: var(--bg-secondary);
      border-radius: 10px;
    }}
    .score-adjust-btn {{
      width: 44px;
      height: 44px;
      border: 2px solid #444;
      background: var(--bg-card);
      color: var(--text-primary);
      font-size: 1.5rem;
      border-radius: 8px;
      cursor: pointer;
      transition: all 0.2s;
    }}
    .score-adjust-btn:hover {{ border-color: var(--accent); background: var(--accent)22; }}
    .score-value {{
      font-size: 3rem;
      font-weight: 700;
      color: var(--accent);
      min-width: 80px;
      text-align: center;
    }}
    .score-label {{ font-size: 0.8rem; color: var(--text-secondary); text-align: center; margin-top: 5px; }}
    
    /* Score Breakdown Grid */
    .score-grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 10px;
    }}
    @media (max-width: 600px) {{ .score-grid {{ grid-template-columns: 1fr; }} }}
    
    .score-row {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 10px 12px;
      background: var(--bg-secondary);
      border-radius: 8px;
    }}
    .score-row-label {{
      display: flex;
      align-items: center;
      gap: 8px;
      color: var(--text-secondary);
      font-size: 0.9rem;
    }}
    .score-row-icon {{ font-size: 1.1rem; }}
    .score-row-right {{ display: flex; align-items: center; gap: 10px; }}
    
    .score-select {{
      background: var(--bg-card);
      border: 1px solid #444;
      color: var(--text-primary);
      padding: 6px 10px;
      border-radius: 6px;
      font-size: 0.85rem;
      cursor: pointer;
    }}
    .score-select:focus {{ outline: none; border-color: var(--accent); }}
    .score-select.modified {{ border-color: var(--warning); background: var(--warning)11; }}
    
    .score-input {{
      background: var(--bg-card);
      border: 1px solid #444;
      color: var(--text-primary);
      padding: 6px 10px;
      border-radius: 6px;
      font-size: 0.85rem;
      width: 70px;
      text-align: center;
    }}
    .score-input:focus {{ outline: none; border-color: var(--accent); }}
    .score-input.modified {{ border-color: var(--warning); background: var(--warning)11; }}
    
    .score-points {{
      min-width: 35px;
      text-align: right;
      font-weight: 600;
      font-size: 0.9rem;
    }}
    .score-points.positive {{ color: var(--success); }}
    .score-points.negative {{ color: var(--danger); }}
    .score-points.neutral {{ color: var(--text-secondary); }}
    
    .rescue-value {{
      font-size: 0.7rem;
      color: var(--text-secondary);
      margin-top: 2px;
    }}
    
    /* Bio */
    .bio-text {{ line-height: 1.8; color: var(--text-secondary); }}
    
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
    .timeline-date {{ font-size: 0.8rem; color: var(--text-secondary); min-width: 80px; }}
    .timeline-text {{ flex: 1; }}
    .timeline-empty {{ color: var(--text-secondary); text-align: center; padding: 20px; }}
    
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
    .notes-textarea:focus {{ outline: none; border-color: var(--accent); }}
    
    .btn-row {{ display: flex; gap: 10px; margin-top: 15px; }}
    .save-btn {{
      flex: 1;
      padding: 12px 24px;
      background: var(--success);
      border: none;
      border-radius: 8px;
      color: white;
      font-weight: 600;
      cursor: pointer;
      font-size: 1rem;
    }}
    .save-btn:hover {{ opacity: 0.9; }}
    .reset-btn {{
      padding: 12px 20px;
      background: var(--bg-secondary);
      border: 1px solid #444;
      border-radius: 8px;
      color: var(--text-secondary);
      cursor: pointer;
      font-size: 0.9rem;
    }}
    .reset-btn:hover {{ border-color: var(--danger); color: var(--danger); }}
    
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
      box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    }}
    .toast.show {{ display: block; animation: slideIn 0.3s ease; }}
    .toast.error {{ background: var(--danger); }}
    @keyframes slideIn {{
      from {{ transform: translateX(100%); opacity: 0; }}
      to {{ transform: translateX(0); opacity: 1; }}
    }}
  </style>
</head>
<body>
  <div class="header">
    <a href="dashboard.html" class="back-btn">← Back</a>
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
          <button class="watch-btn {watch_class}" id="watchBtn" onclick="toggleWatch()" title="Add to watch list">{watch_star}</button>
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
          <a href="{dog.rescue_dog_url or dog.source_url or '#'}" target="_blank">🔗 View on rescue website</a>
        </div>
      </div>
    </div>
    
    <!-- Fit Score Section (Editable) -->
    <div class="section">
      <div class="section-header">
        <h2 class="section-title">Fit Score</h2>
        <a href="#" class="settings-link" onclick="openSettings(); return false;">⚙️ Scoring Settings</a>
      </div>
      
      <!-- Main Score with +/- -->
      <div class="score-main">
        <button class="score-adjust-btn" onclick="adjustScore(-1)">−</button>
        <div>
          <div class="score-value" id="totalScore">{computed_score}</div>
          <div class="score-label">Total Score</div>
        </div>
        <button class="score-adjust-btn" onclick="adjustScore(+1)">+</button>
      </div>
      
      <!-- Score Breakdown Grid -->
      <div class="score-grid">
        <!-- Weight (editable) -->
        <div class="score-row">
          <div class="score-row-label">
            <span class="score-row-icon">⚖️</span>
            <div>
              <span>Weight (lbs)</span>
              <div class="rescue-value">Rescue: {f"{orig_weight} lbs" if orig_weight else "unknown"}</div>
            </div>
          </div>
          <div class="score-row-right">
            <input type="number" class="score-input {'modified' if user_state.overrides.weight is not None else ''}" id="weight" 
                   value="{eff_weight or ''}" min="0" max="200" placeholder="?" onchange="updateScore()">
            <span class="score-points" id="weightPoints">{get_weight_points_from_value(eff_weight)}</span>
          </div>
        </div>
        
        <!-- Age (editable) -->
        <div class="score-row">
          <div class="score-row-label">
            <span class="score-row-icon">🎂</span>
            <div>
              <span>Age (years)</span>
              <div class="rescue-value">Rescue: {f"{orig_age:.1f} yrs" if orig_age else "unknown"}</div>
            </div>
          </div>
          <div class="score-row-right">
            <input type="number" class="score-input {'modified' if user_state.overrides.age_years is not None else ''}" id="age" 
                   value="{f'{eff_age:.1f}' if eff_age else ''}" min="0" max="20" step="0.5" placeholder="?" onchange="updateScore()">
            <span class="score-points" id="agePoints">{get_age_points_from_value(eff_age)}</span>
          </div>
        </div>
        
        <!-- Shedding (editable) -->
        <div class="score-row">
          <div class="score-row-label">
            <span class="score-row-icon">🧹</span>
            <div>
              <span>Shedding</span>
              <div class="rescue-value">Rescue: {orig_shedding}</div>
            </div>
          </div>
          <div class="score-row-right">
            <select class="score-select {'modified' if user_state.overrides.shedding else ''}" id="shedding" onchange="updateScore()">
              <option value="None" {'selected' if eff_shedding == 'None' else ''}>None</option>
              <option value="Low" {'selected' if eff_shedding == 'Low' else ''}>Low</option>
              <option value="Moderate" {'selected' if eff_shedding == 'Moderate' else ''}>Moderate</option>
              <option value="High" {'selected' if eff_shedding == 'High' else ''}>High</option>
              <option value="Unknown" {'selected' if eff_shedding == 'Unknown' else ''}>Unknown</option>
            </select>
            <span class="score-points" id="sheddingPoints">{get_shedding_points(eff_shedding)}</span>
          </div>
        </div>
        
        <!-- Energy (editable) -->
        <div class="score-row">
          <div class="score-row-label">
            <span class="score-row-icon">⚡</span>
            <div>
              <span>Energy</span>
              <div class="rescue-value">Rescue: {orig_energy}</div>
            </div>
          </div>
          <div class="score-row-right">
            <select class="score-select {'modified' if user_state.overrides.energy_level else ''}" id="energy" onchange="updateScore()">
              <option value="Low" {'selected' if eff_energy == 'Low' else ''}>Low</option>
              <option value="Medium" {'selected' if eff_energy == 'Medium' else ''}>Medium</option>
              <option value="High" {'selected' if eff_energy == 'High' else ''}>High</option>
              <option value="Unknown" {'selected' if eff_energy == 'Unknown' else ''}>Unknown</option>
            </select>
            <span class="score-points" id="energyPoints">{get_energy_points(eff_energy)}</span>
          </div>
        </div>
        
        <!-- Good with Dogs (editable) -->
        <div class="score-row">
          <div class="score-row-label">
            <span class="score-row-icon">🐕</span>
            <div>
              <span>Good with Dogs</span>
              <div class="rescue-value">Rescue: {orig_dogs}</div>
            </div>
          </div>
          <div class="score-row-right">
            <select class="score-select {'modified' if user_state.overrides.good_with_dogs else ''}" id="goodDogs" onchange="updateScore()">
              <option value="Yes" {'selected' if eff_dogs == 'Yes' else ''}>Yes</option>
              <option value="No" {'selected' if eff_dogs == 'No' else ''}>No</option>
              <option value="Unknown" {'selected' if eff_dogs == 'Unknown' else ''}>Unknown</option>
            </select>
            <span class="score-points" id="dogsPoints">{get_compat_points(eff_dogs, 2)}</span>
          </div>
        </div>
        
        <!-- Good with Kids (editable) -->
        <div class="score-row">
          <div class="score-row-label">
            <span class="score-row-icon">👶</span>
            <div>
              <span>Good with Kids</span>
              <div class="rescue-value">Rescue: {orig_kids}</div>
            </div>
          </div>
          <div class="score-row-right">
            <select class="score-select {'modified' if user_state.overrides.good_with_kids else ''}" id="goodKids" onchange="updateScore()">
              <option value="Yes" {'selected' if eff_kids == 'Yes' else ''}>Yes</option>
              <option value="No" {'selected' if eff_kids == 'No' else ''}>No</option>
              <option value="Unknown" {'selected' if eff_kids == 'Unknown' else ''}>Unknown</option>
            </select>
            <span class="score-points" id="kidsPoints">{get_compat_points(eff_kids, 1)}</span>
          </div>
        </div>
        
        <!-- Good with Cats (editable) -->
        <div class="score-row">
          <div class="score-row-label">
            <span class="score-row-icon">🐱</span>
            <div>
              <span>Good with Cats</span>
              <div class="rescue-value">Rescue: {orig_cats}</div>
            </div>
          </div>
          <div class="score-row-right">
            <select class="score-select {'modified' if user_state.overrides.good_with_cats else ''}" id="goodCats" onchange="updateScore()">
              <option value="Yes" {'selected' if eff_cats == 'Yes' else ''}>Yes</option>
              <option value="No" {'selected' if eff_cats == 'No' else ''}>No</option>
              <option value="Unknown" {'selected' if eff_cats == 'Unknown' else ''}>Unknown</option>
            </select>
            <span class="score-points" id="catsPoints">{get_compat_points(eff_cats, 1)}</span>
          </div>
        </div>
        
        <!-- Breed (editable) -->
        <div class="score-row">
          <div class="score-row-label">
            <span class="score-row-icon">🐩</span>
            <div>
              <span>Doodle/Poodle</span>
              <div class="rescue-value">Rescue: {orig_breed_bonus} ({dog.breed or 'unknown'})</div>
            </div>
          </div>
          <div class="score-row-right">
            <select class="score-select {'modified' if user_state.overrides.breed_bonus else ''}" id="breed" onchange="updateScore()">
              <option value="Yes" {'selected' if eff_breed == 'Yes' else ''}>Yes</option>
              <option value="No" {'selected' if eff_breed == 'No' else ''}>No</option>
              <option value="Unknown" {'selected' if eff_breed == 'Unknown' else ''}>Unknown</option>
            </select>
            <span class="score-points" id="breedPoints">{"+1" if eff_breed == "Yes" else "0"}</span>
          </div>
        </div>
        
        <!-- Manual Adjustment -->
        <div class="score-row">
          <div class="score-row-label">
            <span class="score-row-icon">✏️</span>
            <span>Your Adjustment</span>
          </div>
          <div class="score-row-right">
            <span class="score-points {'positive' if score_modifier > 0 else 'negative' if score_modifier < 0 else 'neutral'}" id="modifierPoints">{f"+{score_modifier}" if score_modifier > 0 else score_modifier}</span>
          </div>
        </div>
        
        {f'''<!-- Pending Penalty -->
        <div class="score-row">
          <div class="score-row-label">
            <span class="score-row-icon">⏳</span>
            <span>Pending Status</span>
          </div>
          <div class="score-row-right">
            <span class="score-points negative">-8</span>
          </div>
        </div>''' if dog.status == 'Pending' else ''}
      </div>
    </div>
    
    <!-- Bio Section -->
    {f'''<div class="section">
      <div class="section-header">
        <h2 class="section-title">About {dog.dog_name}</h2>
      </div>
      <p class="bio-text">{bio_text}</p>
    </div>''' if bio_text else ''}
    
    <!-- Adoption Requirements -->
    {f'''<div class="section">
      <div class="section-header">
        <h2 class="section-title">Adoption Info</h2>
      </div>
      <p class="bio-text">{adoption_req}</p>
      {f'<p style="margin-top: 15px;"><strong>Adoption Fee:</strong> {dog.adoption_fee}</p>' if dog.adoption_fee else ''}
    </div>''' if adoption_req or dog.adoption_fee else ''}
    
    <!-- Timeline Section -->
    <div class="section">
      <div class="section-header">
        <h2 class="section-title">Timeline</h2>
      </div>
      <div class="timeline">
        {timeline_html}
      </div>
    </div>
    
    <!-- Notes Section -->
    <div class="section">
      <div class="section-header">
        <h2 class="section-title">Your Notes</h2>
      </div>
      <textarea class="notes-textarea" id="userNotes" placeholder="Add your private notes about this dog...">{user_state.notes}</textarea>
      
      <div class="btn-row">
        <button class="save-btn" onclick="saveAll()">💾 Save All Changes</button>
        <button class="reset-btn" onclick="resetOverrides()">Reset to Rescue Values</button>
      </div>
    </div>
  </div>
  
  <div class="toast" id="toast">Saved!</div>
  
  <script>
    const dogId = '{dog.dog_id}';
    const rescueValues = {{
      weight: {orig_weight if orig_weight else 'null'},
      age: {f'{orig_age:.1f}' if orig_age else 'null'},
      shedding: '{orig_shedding}',
      energy: '{orig_energy}',
      goodDogs: '{orig_dogs}',
      goodKids: '{orig_kids}',
      goodCats: '{orig_cats}',
      breed: '{orig_breed_bonus}'
    }};
    
    let scoreModifier = {score_modifier};
    let watchList = {'true' if user_state.favorite else 'false'};
    
    // Score calculation constants
    const SHEDDING_SCORES = {{ 'None': 2, 'Low': 1, 'Moderate': 0, 'High': -1, 'Unknown': 1 }};
    const ENERGY_SCORES = {{ 'Low': 2, 'Medium': 2, 'High': 0, 'Unknown': 1 }};
    
    function getWeightScore(weight) {{
      if (weight === null || weight === '' || isNaN(weight)) return 0;
      return parseFloat(weight) >= 40 ? 2 : 0;
    }}
    
    function getAgeScore(age) {{
      if (age === null || age === '' || isNaN(age)) return 0;
      const years = parseFloat(age);
      if (years < 0.75) return 0;
      if (years < 2) return 2;
      if (years < 4) return 1;
      if (years < 6) return 0;
      return -4;
    }}
    
    function updateScore() {{
      const weight = document.getElementById('weight').value;
      const age = document.getElementById('age').value;
      const shedding = document.getElementById('shedding').value;
      const energy = document.getElementById('energy').value;
      const goodDogs = document.getElementById('goodDogs').value;
      const goodKids = document.getElementById('goodKids').value;
      const goodCats = document.getElementById('goodCats').value;
      const breed = document.getElementById('breed').value;
      
      // Calculate score from all editable fields
      let score = 0;
      
      // Weight
      const weightScore = getWeightScore(weight);
      score += weightScore;
      
      // Age
      const ageScore = getAgeScore(age);
      score += ageScore;
      
      // Shedding
      score += SHEDDING_SCORES[shedding] || 1;
      
      // Energy
      score += ENERGY_SCORES[energy] || 1;
      
      // Compatibility
      score += goodDogs === 'Yes' ? 2 : 0;
      score += goodKids === 'Yes' ? 1 : 0;
      score += goodCats === 'Yes' ? 1 : 0;
      
      // Breed bonus
      const breedScore = breed === 'Yes' ? 1 : 0;
      score += breedScore;
      
      // Pending penalty
      {'score += -8;' if dog.status == 'Pending' else ''}
      
      // Manual modifier
      score += scoreModifier;
      
      score = Math.max(0, score);
      
      // Update display
      document.getElementById('totalScore').textContent = score;
      updatePointsDisplay('weightPoints', weightScore);
      updatePointsDisplay('agePoints', ageScore);
      updatePointsDisplay('sheddingPoints', SHEDDING_SCORES[shedding] || 1);
      updatePointsDisplay('energyPoints', ENERGY_SCORES[energy] || 1);
      updatePointsDisplay('dogsPoints', goodDogs === 'Yes' ? 2 : 0);
      updatePointsDisplay('kidsPoints', goodKids === 'Yes' ? 1 : 0);
      updatePointsDisplay('catsPoints', goodCats === 'Yes' ? 1 : 0);
      updatePointsDisplay('breedPoints', breedScore);
      
      // Mark modified fields
      const weightVal = weight === '' ? null : parseFloat(weight);
      const ageVal = age === '' ? null : parseFloat(age);
      document.getElementById('weight').classList.toggle('modified', weightVal !== rescueValues.weight);
      document.getElementById('age').classList.toggle('modified', ageVal !== rescueValues.age);
      document.getElementById('shedding').classList.toggle('modified', shedding !== rescueValues.shedding);
      document.getElementById('energy').classList.toggle('modified', energy !== rescueValues.energy);
      document.getElementById('goodDogs').classList.toggle('modified', goodDogs !== rescueValues.goodDogs);
      document.getElementById('goodKids').classList.toggle('modified', goodKids !== rescueValues.goodKids);
      document.getElementById('goodCats').classList.toggle('modified', goodCats !== rescueValues.goodCats);
      document.getElementById('breed').classList.toggle('modified', breed !== rescueValues.breed);
    }}
    
    function updatePointsDisplay(id, points) {{
      const el = document.getElementById(id);
      el.textContent = (points > 0 ? '+' : '') + points;
      el.className = 'score-points ' + (points > 0 ? 'positive' : points < 0 ? 'negative' : 'neutral');
    }}
    
    function adjustScore(delta) {{
      scoreModifier += delta;
      document.getElementById('modifierPoints').textContent = (scoreModifier > 0 ? '+' : '') + scoreModifier;
      document.getElementById('modifierPoints').className = 'score-points ' + (scoreModifier > 0 ? 'positive' : scoreModifier < 0 ? 'negative' : 'neutral');
      updateScore();
    }}
    
    function toggleWatch() {{
      watchList = !watchList;
      const btn = document.getElementById('watchBtn');
      btn.textContent = watchList ? '⭐' : '☆';
      btn.classList.toggle('active', watchList);
    }}
    
    function resetOverrides() {{
      if (!confirm('Reset all your overrides to the rescue\\'s original values?')) return;
      
      document.getElementById('weight').value = rescueValues.weight || '';
      document.getElementById('age').value = rescueValues.age || '';
      document.getElementById('shedding').value = rescueValues.shedding;
      document.getElementById('energy').value = rescueValues.energy;
      document.getElementById('goodDogs').value = rescueValues.goodDogs;
      document.getElementById('goodKids').value = rescueValues.goodKids;
      document.getElementById('goodCats').value = rescueValues.goodCats;
      document.getElementById('breed').value = rescueValues.breed;
      scoreModifier = 0;
      document.getElementById('modifierPoints').textContent = '0';
      document.getElementById('modifierPoints').className = 'score-points neutral';
      
      updateScore();
      showToast('Reset to rescue values');
    }}
    
    async function saveAll() {{
      const weightVal = document.getElementById('weight').value;
      const ageVal = document.getElementById('age').value;
      const overrides = {{
        weight: weightVal === '' ? null : parseFloat(weightVal),
        age_years: ageVal === '' ? null : parseFloat(ageVal),
        shedding: document.getElementById('shedding').value,
        energy_level: document.getElementById('energy').value,
        good_with_dogs: document.getElementById('goodDogs').value,
        good_with_kids: document.getElementById('goodKids').value,
        good_with_cats: document.getElementById('goodCats').value,
        breed_bonus: document.getElementById('breed').value,
        score_modifier: scoreModifier,
        watch_list: watchList ? 'Yes' : '',
        notes: document.getElementById('userNotes').value
      }};
      
      // Only include fields that differ from rescue values
      const toSave = {{}};
      if (overrides.weight !== rescueValues.weight) toSave.weight = overrides.weight;
      if (overrides.age_years !== rescueValues.age) toSave.age_years = overrides.age_years;
      if (overrides.shedding !== rescueValues.shedding) toSave.shedding = overrides.shedding;
      if (overrides.energy_level !== rescueValues.energy) toSave.energy_level = overrides.energy_level;
      if (overrides.good_with_dogs !== rescueValues.goodDogs) toSave.good_with_dogs = overrides.good_with_dogs;
      if (overrides.good_with_kids !== rescueValues.goodKids) toSave.good_with_kids = overrides.good_with_kids;
      if (overrides.good_with_cats !== rescueValues.goodCats) toSave.good_with_cats = overrides.good_with_cats;
      if (overrides.breed_bonus !== rescueValues.breed) toSave.breed_bonus = overrides.breed_bonus;
      if (scoreModifier !== 0) toSave.score_modifier = scoreModifier;
      if (watchList) toSave.watch_list = 'Yes';
      
      // Try to save to GitHub (same mechanism as dashboard)
      try {{
        // Load existing overrides
        let userOverrides = {{ dogs: {{}}, acknowledgedChanges: [] }};
        try {{
          const stored = localStorage.getItem('dogTrackerOverrides');
          if (stored) userOverrides = JSON.parse(stored);
        }} catch (e) {{}}
        
        // Update this dog's overrides
        if (Object.keys(toSave).length > 0 || overrides.notes) {{
          userOverrides.dogs[dogId] = {{ ...toSave }};
          if (overrides.notes) userOverrides.dogs[dogId].notes = overrides.notes;
        }} else {{
          delete userOverrides.dogs[dogId];
        }}
        
        // Save to localStorage
        localStorage.setItem('dogTrackerOverrides', JSON.stringify(userOverrides));
        
        showToast('✅ Saved successfully!');
      }} catch (err) {{
        console.error('Save error:', err);
        showToast('❌ Save failed: ' + err.message, true);
      }}
    }}
    
    function openSettings() {{
      alert('Scoring Settings:\\n\\n' +
        'Weight ≥40 lbs: +2\\n' +
        'Age 1-2 yrs: +2, 2-4 yrs: +1, 6+ yrs: -4\\n' +
        'Shedding: None +2, Low +1, High -1\\n' +
        'Energy: Low/Med +2, Unknown +1\\n' +
        'Good with Dogs: +2\\n' +
        'Good with Kids: +1\\n' +
        'Good with Cats: +1\\n' +
        'Doodle/Poodle breed: +1\\n' +
        'Pending status: -8');
    }}
    
    function showToast(message, isError = false) {{
      const toast = document.getElementById('toast');
      toast.textContent = message;
      toast.classList.toggle('error', isError);
      toast.classList.add('show');
      setTimeout(() => toast.classList.remove('show'), 2500);
    }}
    
    // Initial score calculation
    updateScore();
  </script>
</body>
</html>
'''
  return html


# Helper functions for score display
def get_weight_points(dog: Dog) -> str:
  weight = dog.weight_lbs or dog.weight
  if weight and weight >= 40:
    return "+2"
  return "0"

def get_weight_class(dog: Dog) -> str:
  weight = dog.weight_lbs or dog.weight
  if weight and weight >= 40:
    return "positive"
  return "neutral"

def get_age_points(dog: Dog, dal: DAL) -> str:
  age_str = dog.age_display or dog.age_range or ""
  age_years = dal._parse_age_to_years(age_str)
  if age_years:
    if age_years < 2:
      return "+2"
    elif age_years < 4:
      return "+1"
    elif age_years < 6:
      return "0"
    else:
      return "-4"
  return "0"

def get_age_class(dog: Dog, dal: DAL) -> str:
  age_str = dog.age_display or dog.age_range or ""
  age_years = dal._parse_age_to_years(age_str)
  if age_years:
    if age_years < 4:
      return "positive"
    elif age_years < 6:
      return "neutral"
    else:
      return "negative"
  return "neutral"

def get_shedding_points(shedding: str) -> str:
  scores = {"None": "+2", "Low": "+1", "Moderate": "0", "High": "-1", "Unknown": "+1"}
  return scores.get(shedding, "+1")

def get_energy_points(energy: str) -> str:
  if energy in ["Low", "Medium"]:
    return "+2"
  elif energy == "High":
    return "0"
  return "+1"

def get_compat_points(value: str, max_points: int) -> str:
  if value == "Yes":
    return f"+{max_points}"
  return "0"

def get_breed_points(dog: Dog) -> str:
  breed = dog.breed or ""
  if any(term in breed.lower() for term in ["doodle", "poodle", "poo"]):
    return "+1"
  return "0"

def get_breed_class(dog: Dog) -> str:
  breed = dog.breed or ""
  if any(term in breed.lower() for term in ["doodle", "poodle", "poo"]):
    return "positive"
  return "neutral"


def get_weight_points_from_value(weight) -> str:
  """Get points display for a weight value"""
  if weight and weight >= 40:
    return "+2"
  return "0"

def get_age_points_from_value(age_years) -> str:
  """Get points display for an age value in years"""
  if not age_years:
    return "0"
  if age_years < 0.75:
    return "0"
  if age_years < 2:
    return "+2"
  if age_years < 4:
    return "+1"
  if age_years < 6:
    return "0"
  return "-4"


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
