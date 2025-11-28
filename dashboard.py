#!/usr/bin/env python3
"""
Dog Rescue Dashboard Generator
v2.0.0 - Added images, compact recent changes, change acknowledgment

Generates an interactive HTML dashboard from the database.

Usage:
  python dashboard.py              # Generate static HTML
  python dashboard.py -o out.html  # Generate to specific file
"""
import os
import sys
import json
import argparse
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import init_database, get_connection


def get_dashboard_data():
  """Get all data needed for dashboard"""
  conn = get_connection()
  cursor = conn.cursor()
  
  # Get all active dogs
  cursor.execute("""
    SELECT * FROM dogs 
    WHERE is_active = 1 
    ORDER BY fit_score DESC, dog_name ASC
  """)
  dogs = [dict(row) for row in cursor.fetchall()]
  
  # Get recent changes with unique change IDs
  cursor.execute("""
    SELECT c.id, c.dog_id, c.dog_name, c.field_changed, c.old_value, 
           c.new_value, c.change_type, c.timestamp,
           d.fit_score as current_fit, d.image_url
    FROM changes c
    LEFT JOIN dogs d ON c.dog_id = d.dog_id
    WHERE c.timestamp > datetime('now', '-7 days')
    ORDER BY c.timestamp DESC
    LIMIT 100
  """)
  changes = [dict(row) for row in cursor.fetchall()]
  
  conn.close()
  
  return {
    "dogs": dogs,
    "changes": changes,
    "generated_at": datetime.now().isoformat()
  }


def generate_html_dashboard(output_path="dashboard.html"):
  """Generate a standalone HTML dashboard file"""
  init_database()
  data = get_dashboard_data()
  
  # Convert to JSON for embedding
  dogs_json = json.dumps(data["dogs"], default=str)
  changes_json = json.dumps(data["changes"], default=str)
  
  html = f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>🐕 Dog Rescue Dashboard</title>
  <style>
    :root {{
      --bg-primary: #1a1a2e;
      --bg-secondary: #16213e;
      --bg-card: #1f2937;
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
      padding: 20px;
    }}
    .container {{ max-width: 1400px; margin: 0 auto; }}
    header {{
      text-align: center;
      margin-bottom: 20px;
      padding: 20px;
      background: var(--bg-secondary);
      border-radius: 12px;
    }}
    header h1 {{ font-size: 2rem; margin-bottom: 10px; }}
    .stats {{ display: flex; justify-content: center; gap: 30px; flex-wrap: wrap; }}
    .stat {{ text-align: center; }}
    .stat-value {{ font-size: 2rem; font-weight: bold; color: var(--accent); }}
    .stat-label {{ color: var(--text-secondary); font-size: 0.875rem; }}
    
    /* Recent Changes - Compact */
    .recent-changes {{
      background: var(--bg-secondary);
      border-radius: 12px;
      padding: 15px;
      margin-bottom: 20px;
    }}
    .recent-changes-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 10px;
    }}
    .recent-changes h2 {{ font-size: 1.1rem; }}
    .changes-container {{
      max-height: 140px;
      overflow-y: auto;
    }}
    .change-item {{
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 8px 10px;
      background: var(--bg-card);
      border-radius: 8px;
      margin-bottom: 6px;
      font-size: 0.875rem;
    }}
    .change-item.acknowledged {{
      opacity: 0.4;
      text-decoration: line-through;
    }}
    .change-thumb {{
      width: 40px;
      height: 40px;
      border-radius: 6px;
      object-fit: cover;
      background: var(--bg-secondary);
    }}
    .change-icon {{ font-size: 1.2rem; flex-shrink: 0; }}
    .change-details {{ flex: 1; min-width: 0; }}
    .change-dog {{ font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
    .change-msg {{ color: var(--text-secondary); font-size: 0.8rem; }}
    .change-time {{ color: var(--text-secondary); font-size: 0.75rem; flex-shrink: 0; }}
    .ack-btn {{
      padding: 4px 8px;
      border: 1px solid #374151;
      border-radius: 4px;
      background: transparent;
      color: var(--text-secondary);
      cursor: pointer;
      font-size: 0.75rem;
      flex-shrink: 0;
    }}
    .ack-btn:hover {{ background: var(--accent); color: white; border-color: var(--accent); }}
    .ack-btn.acked {{ background: var(--success); color: white; border-color: var(--success); }}
    
    .controls {{
      display: flex;
      gap: 15px;
      margin-bottom: 20px;
      flex-wrap: wrap;
      align-items: center;
    }}
    .search-box {{
      flex: 1;
      min-width: 200px;
      padding: 10px 15px;
      border: 1px solid #374151;
      border-radius: 8px;
      background: var(--bg-card);
      color: var(--text-primary);
      font-size: 1rem;
    }}
    .filter-btn {{
      padding: 10px 20px;
      border: 1px solid #374151;
      border-radius: 8px;
      background: var(--bg-card);
      color: var(--text-primary);
      cursor: pointer;
      transition: all 0.2s;
    }}
    .filter-btn:hover, .filter-btn.active {{
      background: var(--accent);
      border-color: var(--accent);
    }}
    .sort-select {{
      padding: 10px 15px;
      border: 1px solid #374151;
      border-radius: 8px;
      background: var(--bg-card);
      color: var(--text-primary);
      font-size: 0.875rem;
    }}
    .dog-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
      gap: 20px;
    }}
    .dog-card {{
      background: var(--bg-card);
      border-radius: 12px;
      padding: 20px;
      position: relative;
      transition: transform 0.2s, box-shadow 0.2s;
    }}
    .dog-card:hover {{
      transform: translateY(-2px);
      box-shadow: 0 10px 40px rgba(0,0,0,0.3);
    }}
    .dog-card.watched {{ border: 2px solid var(--star); }}
    .dog-card.pending {{ opacity: 0.7; }}
    
    /* Dog card with image */
    .dog-header {{
      display: flex;
      gap: 15px;
      margin-bottom: 15px;
    }}
    .dog-image {{
      width: 80px;
      height: 80px;
      border-radius: 10px;
      object-fit: cover;
      background: var(--bg-secondary);
      flex-shrink: 0;
    }}
    .dog-image-placeholder {{
      width: 80px;
      height: 80px;
      border-radius: 10px;
      background: var(--bg-secondary);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 2rem;
      flex-shrink: 0;
    }}
    .dog-info {{ flex: 1; min-width: 0; }}
    .dog-name-row {{
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
    }}
    .dog-name {{ font-size: 1.3rem; font-weight: 700; }}
    .dog-rescue {{ color: var(--text-secondary); font-size: 0.875rem; margin-top: 2px; }}
    .star-btn {{
      background: transparent;
      border: none;
      font-size: 1.5rem;
      cursor: pointer;
      color: var(--text-secondary);
      padding: 0;
      line-height: 1;
    }}
    .star-btn.starred {{ color: var(--star); }}
    
    .dog-score {{
      display: flex;
      align-items: center;
      gap: 10px;
      margin-bottom: 15px;
    }}
    .score-display {{
      font-size: 1.5rem;
      font-weight: bold;
      width: 45px;
      height: 45px;
      display: flex;
      align-items: center;
      justify-content: center;
      border-radius: 10px;
    }}
    .score-high {{ background: rgba(16, 185, 129, 0.2); color: var(--success); }}
    .score-medium {{ background: rgba(245, 158, 11, 0.2); color: var(--warning); }}
    .score-low {{ background: rgba(239, 68, 68, 0.2); color: var(--danger); }}
    .score-controls {{ display: flex; gap: 5px; }}
    .score-btn {{
      width: 28px;
      height: 28px;
      border: 1px solid #374151;
      border-radius: 6px;
      background: var(--bg-secondary);
      color: var(--text-primary);
      cursor: pointer;
      font-size: 1rem;
    }}
    .score-btn:hover {{ background: var(--accent); }}
    .score-modifier {{ color: var(--text-secondary); font-size: 0.875rem; margin-left: 5px; }}
    .dog-status {{
      display: inline-block;
      padding: 4px 12px;
      border-radius: 20px;
      font-size: 0.875rem;
      font-weight: 500;
    }}
    .status-available {{ background: rgba(16, 185, 129, 0.2); color: var(--success); }}
    .status-pending {{ background: rgba(245, 158, 11, 0.2); color: var(--warning); }}
    .status-upcoming {{ background: rgba(59, 130, 246, 0.2); color: var(--accent); }}
    
    .dog-details {{
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 8px;
      margin-bottom: 15px;
    }}
    .detail {{ display: flex; justify-content: space-between; }}
    .detail-label {{ color: var(--text-secondary); }}
    .detail-value {{ font-weight: 500; }}
    .detail-value.good {{ color: var(--success); }}
    .detail-value.bad {{ color: var(--danger); }}
    .detail-value.unknown {{ color: var(--text-secondary); }}
    
    .dog-link {{
      display: block;
      text-align: center;
      padding: 8px;
      color: var(--accent);
      text-decoration: none;
      font-size: 0.875rem;
    }}
    .dog-link:hover {{ text-decoration: underline; }}
    .dog-actions {{
      display: flex;
      gap: 10px;
      margin-top: 15px;
      padding-top: 15px;
      border-top: 1px solid #374151;
    }}
    .action-btn {{
      flex: 1;
      padding: 8px 15px;
      border: 1px solid #374151;
      border-radius: 6px;
      background: var(--bg-secondary);
      color: var(--text-primary);
      cursor: pointer;
      font-size: 0.875rem;
      transition: all 0.2s;
    }}
    .action-btn:hover {{ background: var(--accent); border-color: var(--accent); }}
    
    /* Modal */
    .modal {{
      display: none;
      position: fixed;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      background: rgba(0,0,0,0.8);
      z-index: 1000;
      justify-content: center;
      align-items: center;
    }}
    .modal.active {{ display: flex; }}
    .modal-content {{
      background: var(--bg-secondary);
      padding: 30px;
      border-radius: 12px;
      width: 90%;
      max-width: 500px;
      max-height: 90vh;
      overflow-y: auto;
    }}
    .modal h2 {{ margin-bottom: 20px; }}
    .form-group {{ margin-bottom: 15px; }}
    .form-group label {{ display: block; margin-bottom: 5px; color: var(--text-secondary); }}
    .form-group input, .form-group select {{
      width: 100%;
      padding: 10px;
      border: 1px solid #374151;
      border-radius: 6px;
      background: var(--bg-card);
      color: var(--text-primary);
    }}
    .modal-buttons {{ display: flex; gap: 10px; margin-top: 20px; }}
    .modal-buttons button {{
      flex: 1;
      padding: 12px;
      border: none;
      border-radius: 6px;
      cursor: pointer;
      font-size: 1rem;
    }}
    .btn-save {{ background: var(--success); color: white; }}
    .btn-cancel {{ background: var(--bg-card); color: var(--text-primary); }}
    
    /* Utility buttons */
    .utility-buttons {{
      display: flex;
      gap: 10px;
      margin-bottom: 20px;
      flex-wrap: wrap;
    }}
    .utility-btn {{
      padding: 8px 15px;
      border: 1px solid #374151;
      border-radius: 6px;
      background: var(--bg-card);
      color: var(--text-secondary);
      cursor: pointer;
      font-size: 0.875rem;
    }}
    .utility-btn:hover {{ background: var(--accent); color: white; }}
    
    /* Toast */
    .toast {{
      position: fixed;
      bottom: 20px;
      right: 20px;
      padding: 15px 25px;
      background: var(--success);
      color: white;
      border-radius: 8px;
      display: none;
      z-index: 2000;
    }}
    .toast.show {{ display: block; animation: fadeIn 0.3s; }}
    @keyframes fadeIn {{ from {{ opacity: 0; transform: translateY(20px); }} to {{ opacity: 1; transform: translateY(0); }} }}
    
    /* Scrollbar */
    ::-webkit-scrollbar {{ width: 8px; height: 8px; }}
    ::-webkit-scrollbar-track {{ background: var(--bg-primary); }}
    ::-webkit-scrollbar-thumb {{ background: #374151; border-radius: 4px; }}
    ::-webkit-scrollbar-thumb:hover {{ background: #4b5563; }}
  </style>
</head>
<body>
  <div class="container">
    <header>
      <h1>🐕 Dog Rescue Dashboard</h1>
      <div class="stats">
        <div class="stat">
          <div class="stat-value" id="totalDogs">0</div>
          <div class="stat-label">Total Dogs</div>
        </div>
        <div class="stat">
          <div class="stat-value" id="watchCount">0</div>
          <div class="stat-label">Watching</div>
        </div>
        <div class="stat">
          <div class="stat-value" id="highFitCount">0</div>
          <div class="stat-label">High Fit (5+)</div>
        </div>
        <div class="stat">
          <div class="stat-value" id="availableCount">0</div>
          <div class="stat-label">Available</div>
        </div>
      </div>
    </header>
    
    <div class="recent-changes">
      <div class="recent-changes-header">
        <h2>📢 Recent Changes</h2>
        <span id="changesCount" style="color: var(--text-secondary); font-size: 0.875rem;"></span>
      </div>
      <div class="changes-container" id="changesContainer"></div>
    </div>
    
    <div class="controls">
      <input type="text" class="search-box" placeholder="Search dogs..." id="searchBox">
      <button class="filter-btn active" data-filter="all">🐕 All Dogs <span id="visibleCount"></span></button>
      <button class="filter-btn" data-filter="watched">⭐ Watched</button>
      <button class="filter-btn" data-filter="high-fit">🎯 High Fit</button>
      <button class="filter-btn" data-filter="available">✅ Available</button>
      <button class="filter-btn" data-filter="upcoming">🔜 Upcoming</button>
      <select class="sort-select" id="sortSelect">
        <option value="fit-desc">Score: High → Low</option>
        <option value="fit-asc">Score: Low → High</option>
        <option value="name-asc">Name: A → Z</option>
        <option value="weight-desc">Weight: Heavy → Light</option>
        <option value="date-desc">Newest First</option>
      </select>
    </div>
    
    <div class="utility-buttons">
      <button class="utility-btn" onclick="exportMods()">📤 Export Changes</button>
      <button class="utility-btn" onclick="document.getElementById('importInput').click()">📥 Import Changes</button>
      <button class="utility-btn" onclick="clearMods()">🗑️ Clear Local Changes</button>
      <input type="file" id="importInput" style="display:none" accept=".json" onchange="importMods(event)">
    </div>
    
    <div class="dog-grid" id="dogGrid"></div>
  </div>
  
  <div class="modal" id="editModal">
    <div class="modal-content">
      <h2>✏️ Edit Dog</h2>
      <input type="hidden" id="editDogId">
      <div class="form-group">
        <label>Weight (lbs)</label>
        <input type="number" id="editWeight">
      </div>
      <div class="form-group">
        <label>Age</label>
        <input type="text" id="editAge" placeholder="e.g., 2 yrs, 6 mos">
      </div>
      <div class="form-group">
        <label>Energy Level</label>
        <select id="editEnergy">
          <option value="">Unknown</option>
          <option value="Low">Low</option>
          <option value="Medium">Medium</option>
          <option value="High">High</option>
        </select>
      </div>
      <div class="form-group">
        <label>Shedding</label>
        <select id="editShedding">
          <option value="">Unknown</option>
          <option value="None">None</option>
          <option value="Low">Low</option>
          <option value="Moderate">Moderate</option>
          <option value="High">High</option>
        </select>
      </div>
      <div class="form-group">
        <label>Good with Dogs</label>
        <select id="editDogs">
          <option value="Unknown">Unknown</option>
          <option value="Yes">Yes</option>
          <option value="No">No</option>
        </select>
      </div>
      <div class="form-group">
        <label>Good with Kids</label>
        <select id="editKids">
          <option value="Unknown">Unknown</option>
          <option value="Yes">Yes</option>
          <option value="No">No</option>
        </select>
      </div>
      <div class="form-group">
        <label>Good with Cats</label>
        <select id="editCats">
          <option value="Unknown">Unknown</option>
          <option value="Yes">Yes</option>
          <option value="No">No</option>
        </select>
      </div>
      <div class="form-group">
        <label>Special Needs</label>
        <select id="editSpecialNeeds">
          <option value="">No</option>
          <option value="Yes">Yes</option>
        </select>
      </div>
      <div class="form-group">
        <label>Notes</label>
        <input type="text" id="editNotes" placeholder="Your notes...">
      </div>
      <div class="modal-buttons">
        <button class="btn-cancel" onclick="closeEdit()">Cancel</button>
        <button class="btn-save" onclick="saveEdit()">Save Changes</button>
      </div>
    </div>
  </div>
  
  <div class="toast" id="toast"></div>
  
  <script>
    // Data from database
    const dogsData = {dogs_json};
    const changesData = {changes_json};
    const generatedAt = "{data['generated_at']}";
    
    // Local modifications stored in localStorage
    // Structure: {{ dogId: {{ watch_list, score_modifier, weight, ... }}, ... }}
    let localMods = JSON.parse(localStorage.getItem('dogMods') || '{{}}');
    
    // Acknowledged changes stored separately
    // Structure: {{ changeId: true, ... }}
    let ackedChanges = JSON.parse(localStorage.getItem('ackedChanges') || '{{}}');
    
    // Apply local mods to dog data
    function applyLocalMods() {{
      dogsData.forEach(dog => {{
        const mod = localMods[dog.dog_id];
        if (mod) {{
          if (mod.watch_list !== undefined) dog.watch_list = mod.watch_list;
          if (mod.score_modifier !== undefined) {{
            const baseScore = calculateFitScore(dog);
            dog.fit_score = Math.max(0, baseScore + mod.score_modifier);
          }}
          if (mod.weight !== undefined) dog.weight = mod.weight;
          if (mod.age_range !== undefined) dog.age_range = mod.age_range;
          if (mod.energy_level !== undefined) dog.energy_level = mod.energy_level;
          if (mod.shedding !== undefined) dog.shedding = mod.shedding;
          if (mod.good_with_dogs !== undefined) dog.good_with_dogs = mod.good_with_dogs;
          if (mod.good_with_kids !== undefined) dog.good_with_kids = mod.good_with_kids;
          if (mod.good_with_cats !== undefined) dog.good_with_cats = mod.good_with_cats;
          if (mod.special_needs !== undefined) dog.special_needs = mod.special_needs;
          if (mod.notes !== undefined) dog.notes = mod.notes;
        }}
      }});
    }}
    
    function calculateFitScore(dog) {{
      let score = 0;
      if ((dog.weight || 0) >= 40) score += 2;
      const shed = (dog.shedding || '').toLowerCase();
      if (shed === 'none') score += 2;
      else if (shed === 'low') score += 1;
      else if (shed === 'high') score -= 1;
      else score += 1;
      const energy = (dog.energy_level || '').toLowerCase();
      if (energy === 'low' || energy === 'medium') score += 2;
      else if (!energy || energy === 'unknown') score += 1;
      if (dog.good_with_dogs === 'Yes') score += 2;
      if (dog.good_with_kids === 'Yes') score += 1;
      if (dog.good_with_cats === 'Yes') score += 1;
      const breed = (dog.breed || '').toLowerCase();
      if (breed.includes('doodle') || breed.includes('poodle')) score += 1;
      if (dog.special_needs === 'Yes') score -= 1;
      if ((dog.status || '').toLowerCase() === 'pending') score -= 2;
      return Math.max(0, score);
    }}
    
    function saveMod(dogId, updates) {{
      if (!localMods[dogId]) localMods[dogId] = {{}};
      Object.assign(localMods[dogId], updates);
      localStorage.setItem('dogMods', JSON.stringify(localMods));
      
      const dog = dogsData.find(d => d.dog_id === dogId);
      if (dog) {{
        Object.assign(dog, updates);
        if (updates.score_modifier !== undefined) {{
          const baseScore = calculateFitScore(dog);
          dog.fit_score = Math.max(0, baseScore + updates.score_modifier);
        }}
      }}
    }}
    
    function toggleWatch(dogId) {{
      const dog = dogsData.find(d => d.dog_id === dogId);
      if (!dog) return;
      
      const newVal = dog.watch_list === 'Yes' ? '' : 'Yes';
      saveMod(dogId, {{ watch_list: newVal }});
      renderDogs();
      updateStats();
      showToast(newVal === 'Yes' ? '⭐ Added to watch list' : '☆ Removed from watch list');
    }}
    
    function adjustScore(dogId, delta) {{
      const mod = localMods[dogId]?.score_modifier || 0;
      saveMod(dogId, {{ score_modifier: mod + delta }});
      renderDogs();
      updateStats();
    }}
    
    function openEdit(dogId) {{
      const dog = dogsData.find(d => d.dog_id === dogId);
      if (!dog) return;
      
      document.getElementById('editDogId').value = dogId;
      document.getElementById('editWeight').value = dog.weight || '';
      document.getElementById('editAge').value = dog.age_range || '';
      document.getElementById('editEnergy').value = dog.energy_level || '';
      document.getElementById('editShedding').value = dog.shedding || '';
      document.getElementById('editDogs').value = dog.good_with_dogs || 'Unknown';
      document.getElementById('editKids').value = dog.good_with_kids || 'Unknown';
      document.getElementById('editCats').value = dog.good_with_cats || 'Unknown';
      document.getElementById('editSpecialNeeds').value = dog.special_needs || '';
      document.getElementById('editNotes').value = dog.notes || '';
      
      document.getElementById('editModal').classList.add('active');
    }}
    
    function closeEdit() {{
      document.getElementById('editModal').classList.remove('active');
    }}
    
    function saveEdit() {{
      const dogId = document.getElementById('editDogId').value;
      const updates = {{
        weight: parseInt(document.getElementById('editWeight').value) || null,
        age_range: document.getElementById('editAge').value,
        energy_level: document.getElementById('editEnergy').value,
        shedding: document.getElementById('editShedding').value,
        good_with_dogs: document.getElementById('editDogs').value,
        good_with_kids: document.getElementById('editKids').value,
        good_with_cats: document.getElementById('editCats').value,
        special_needs: document.getElementById('editSpecialNeeds').value,
        notes: document.getElementById('editNotes').value
      }};
      
      saveMod(dogId, updates);
      
      const dog = dogsData.find(d => d.dog_id === dogId);
      if (dog) {{
        Object.assign(dog, updates);
        const mod = localMods[dogId]?.score_modifier || 0;
        dog.fit_score = Math.max(0, calculateFitScore(dog) + mod);
      }}
      
      closeEdit();
      renderDogs();
      updateStats();
      showToast('✅ Changes saved');
    }}
    
    // Acknowledge a change
    function ackChange(changeId) {{
      ackedChanges[changeId] = true;
      localStorage.setItem('ackedChanges', JSON.stringify(ackedChanges));
      renderChanges();
    }}
    
    function renderChanges() {{
      const container = document.getElementById('changesContainer');
      
      // Filter out acknowledged changes
      const visibleChanges = changesData.filter(c => !ackedChanges[c.id]);
      
      document.getElementById('changesCount').textContent = 
        visibleChanges.length > 0 ? `${{visibleChanges.length}} unacknowledged` : 'All caught up!';
      
      if (changesData.length === 0) {{
        container.innerHTML = '<div class="change-item"><span class="change-msg">No recent changes</span></div>';
        return;
      }}
      
      container.innerHTML = changesData.map(change => {{
        const isAcked = ackedChanges[change.id];
        const changeType = change.change_type || '';
        const dogName = change.dog_name || 'Unknown';
        const oldVal = change.old_value || '';
        const newVal = change.new_value || '';
        const timestamp = change.timestamp || '';
        const imageUrl = change.image_url || '';
        
        let timeStr = '?';
        try {{
          const dt = new Date(timestamp);
          timeStr = dt.toLocaleDateString('en-US', {{ month: 'numeric', day: 'numeric' }}) + ' ' + 
                   dt.toLocaleTimeString('en-US', {{ hour: '2-digit', minute: '2-digit' }});
        }} catch(e) {{}}
        
        let icon = '📝';
        let msg = 'Updated';
        
        if (changeType === 'new_dog') {{
          icon = '🆕';
          msg = 'New dog listed';
        }} else if (changeType === 'status_change') {{
          if ((newVal || '').toLowerCase().includes('pending')) {{
            icon = '⏳';
            msg = 'Now pending';
          }} else if ((newVal || '').toLowerCase().includes('available')) {{
            icon = '✅';
            msg = 'Now available';
          }} else {{
            icon = '📢';
            msg = `${{oldVal}} → ${{newVal}}`;
          }}
        }}
        
        const thumbHtml = imageUrl 
          ? `<img src="${{imageUrl}}" class="change-thumb" onerror="this.style.display='none'">`
          : '';
        
        return `
          <div class="change-item ${{isAcked ? 'acknowledged' : ''}}">
            ${{thumbHtml}}
            <span class="change-icon">${{icon}}</span>
            <div class="change-details">
              <div class="change-dog">${{dogName}}</div>
              <div class="change-msg">${{msg}}</div>
            </div>
            <span class="change-time">${{timeStr}}</span>
            <button class="ack-btn ${{isAcked ? 'acked' : ''}}" onclick="ackChange(${{change.id}})">
              ${{isAcked ? '✓' : 'Ack'}}
            </button>
          </div>
        `;
      }}).join('');
    }}
    
    let currentFilter = 'all';
    let searchTerm = '';
    let sortBy = 'fit-desc';
    
    function renderDogs() {{
      const grid = document.getElementById('dogGrid');
      
      let filtered = dogsData.filter(dog => {{
        if (searchTerm) {{
          const search = searchTerm.toLowerCase();
          const matches = (dog.dog_name || '').toLowerCase().includes(search) ||
                         (dog.breed || '').toLowerCase().includes(search) ||
                         (dog.rescue_name || '').toLowerCase().includes(search);
          if (!matches) return false;
        }}
        
        switch(currentFilter) {{
          case 'watched': return dog.watch_list === 'Yes';
          case 'high-fit': return (dog.fit_score || 0) >= 5;
          case 'available': return (dog.status || '').toLowerCase() === 'available';
          case 'upcoming': return (dog.status || '').toLowerCase() === 'upcoming';
          default: return true;
        }}
      }});
      
      filtered.sort((a, b) => {{
        switch (sortBy) {{
          case 'fit-desc': return (b.fit_score || 0) - (a.fit_score || 0);
          case 'fit-asc': return (a.fit_score || 0) - (b.fit_score || 0);
          case 'name-asc': return (a.dog_name || '').localeCompare(b.dog_name || '');
          case 'weight-desc': return (b.weight || 0) - (a.weight || 0);
          case 'date-desc': return (b.date_first_seen || '').localeCompare(a.date_first_seen || '');
          default: return 0;
        }}
      }});
      
      document.getElementById('visibleCount').textContent = filtered.length;
      grid.innerHTML = filtered.map(dog => generateDogCard(dog)).join('');
    }}
    
    function generateDogCard(dog) {{
      const isWatched = dog.watch_list === 'Yes';
      const scoreClass = (dog.fit_score || 0) >= 5 ? 'score-high' : (dog.fit_score || 0) >= 3 ? 'score-medium' : 'score-low';
      const statusClass = (dog.status || '').toLowerCase();
      const mod = localMods[dog.dog_id]?.score_modifier || 0;
      const modDisplay = mod !== 0 ? '(' + (mod > 0 ? '+' : '') + mod + ')' : '';
      const valueClass = (val) => val === 'Yes' ? 'good' : val === 'No' ? 'bad' : 'unknown';
      const url = dog.source_url || '#';
      const imageUrl = dog.image_url || '';
      const dogId = dog.dog_id;
      
      const card = document.createElement('div');
      card.className = 'dog-card' + (isWatched ? ' watched' : '') + (statusClass === 'pending' ? ' pending' : '');
      
      const imageHtml = imageUrl 
        ? `<img src="${{imageUrl}}" class="dog-image" onerror="this.outerHTML='<div class=\\'dog-image-placeholder\\'>🐕</div>'">`
        : '<div class="dog-image-placeholder">🐕</div>';
      
      card.innerHTML = `
        <div class="dog-header">
          ${{imageHtml}}
          <div class="dog-info">
            <div class="dog-name-row">
              <div class="dog-name">${{dog.dog_name || 'Unknown'}}</div>
              <button class="star-btn ${{isWatched ? 'starred' : ''}}" data-action="watch" data-id="${{dogId}}">${{isWatched ? '★' : '☆'}}</button>
            </div>
            <div class="dog-rescue">${{dog.rescue_name || 'Unknown Rescue'}}</div>
          </div>
        </div>
        <div class="dog-score">
          <div class="score-display ${{scoreClass}}">${{dog.fit_score || 0}}</div>
          <div class="score-controls">
            <button class="score-btn" data-action="score-up" data-id="${{dogId}}">+</button>
            <button class="score-btn" data-action="score-down" data-id="${{dogId}}">−</button>
          </div>
          <div class="score-modifier">${{modDisplay}}</div>
          <span class="dog-status status-${{statusClass}}">${{dog.status || 'Unknown'}}</span>
        </div>
        <div class="dog-details">
          <div class="detail"><span class="detail-label">Weight</span><span class="detail-value">${{dog.weight ? dog.weight + ' lbs' : '?'}}</span></div>
          <div class="detail"><span class="detail-label">Age</span><span class="detail-value">${{dog.age_range || '?'}}</span></div>
          <div class="detail"><span class="detail-label">Breed</span><span class="detail-value">${{dog.breed || '?'}}</span></div>
          <div class="detail"><span class="detail-label">Energy</span><span class="detail-value">${{dog.energy_level || '?'}}</span></div>
          <div class="detail"><span class="detail-label">Dogs</span><span class="detail-value ${{valueClass(dog.good_with_dogs)}}">${{dog.good_with_dogs || '?'}}</span></div>
          <div class="detail"><span class="detail-label">Kids</span><span class="detail-value ${{valueClass(dog.good_with_kids)}}">${{dog.good_with_kids || '?'}}</span></div>
          <div class="detail"><span class="detail-label">Cats</span><span class="detail-value ${{valueClass(dog.good_with_cats)}}">${{dog.good_with_cats || '?'}}</span></div>
          <div class="detail"><span class="detail-label">Shedding</span><span class="detail-value">${{dog.shedding || '?'}}</span></div>
        </div>
        ${{dog.notes ? '<div style="font-size: 0.875rem; color: var(--text-secondary); margin-bottom: 10px;">📝 ' + dog.notes.substring(0, 100) + (dog.notes.length > 100 ? '...' : '') + '</div>' : ''}}
        <a href="${{url}}" target="_blank" class="dog-link">🔗 View on rescue site</a>
        <div class="dog-actions">
          <button class="action-btn" data-action="edit" data-id="${{dogId}}">✏️ Edit</button>
        </div>
      `;
      
      return card.outerHTML;
    }}
    
    // Event delegation for dog card buttons
    document.getElementById('dogGrid').addEventListener('click', function(e) {{
      const btn = e.target.closest('button[data-action]');
      if (!btn) return;
      
      const action = btn.dataset.action;
      const dogId = btn.dataset.id;
      
      if (action === 'watch') toggleWatch(dogId);
      else if (action === 'score-up') adjustScore(dogId, 1);
      else if (action === 'score-down') adjustScore(dogId, -1);
      else if (action === 'edit') openEdit(dogId);
    }});
    
    function updateStats() {{
      document.getElementById('totalDogs').textContent = dogsData.length;
      document.getElementById('watchCount').textContent = dogsData.filter(d => d.watch_list === 'Yes').length;
      document.getElementById('highFitCount').textContent = dogsData.filter(d => (d.fit_score || 0) >= 5).length;
      document.getElementById('availableCount').textContent = dogsData.filter(d => d.status === 'Available').length;
    }}
    
    function exportMods() {{
      const data = JSON.stringify({{ mods: localMods, acked: ackedChanges }}, null, 2);
      const blob = new Blob([data], {{ type: 'application/json' }});
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'dog-dashboard-data.json';
      a.click();
      showToast('📤 Exported changes');
    }}
    
    function importMods(event) {{
      const file = event.target.files[0];
      if (!file) return;
      
      const reader = new FileReader();
      reader.onload = function(e) {{
        try {{
          const data = JSON.parse(e.target.result);
          if (data.mods) {{
            localMods = data.mods;
            localStorage.setItem('dogMods', JSON.stringify(localMods));
          }}
          if (data.acked) {{
            ackedChanges = data.acked;
            localStorage.setItem('ackedChanges', JSON.stringify(ackedChanges));
          }}
          applyLocalMods();
          renderDogs();
          renderChanges();
          updateStats();
          showToast('📥 Imported changes');
        }} catch(err) {{
          showToast('❌ Invalid file format');
        }}
      }};
      reader.readAsText(file);
    }}
    
    function clearMods() {{
      if (confirm('Clear all local changes? This cannot be undone.')) {{
        localMods = {{}};
        ackedChanges = {{}};
        localStorage.removeItem('dogMods');
        localStorage.removeItem('ackedChanges');
        location.reload();
      }}
    }}
    
    function showToast(msg) {{
      const toast = document.getElementById('toast');
      toast.textContent = msg;
      toast.classList.add('show');
      setTimeout(() => toast.classList.remove('show'), 3000);
    }}
    
    // Filter buttons
    document.querySelectorAll('.filter-btn').forEach(btn => {{
      btn.addEventListener('click', () => {{
        document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        currentFilter = btn.dataset.filter;
        renderDogs();
      }});
    }});
    
    // Search
    document.getElementById('searchBox').addEventListener('input', (e) => {{
      searchTerm = e.target.value;
      renderDogs();
    }});
    
    // Sort
    document.getElementById('sortSelect').addEventListener('change', (e) => {{
      sortBy = e.target.value;
      renderDogs();
    }});
    
    // Initialize
    applyLocalMods();
    renderChanges();
    renderDogs();
    updateStats();
  </script>
</body>
</html>'''
  
  # Write to file
  with open(output_path, 'w', encoding='utf-8') as f:
    f.write(html)
  
  print(f"✅ Dashboard generated: {output_path}")
  print(f"   Dogs: {len(data['dogs'])}")
  print(f"   Recent changes: {len(data['changes'])}")
  return output_path


def main():
  parser = argparse.ArgumentParser(description="Generate dog rescue dashboard")
  parser.add_argument("-o", "--output", default="dashboard.html", help="Output file path")
  args = parser.parse_args()
  
  generate_html_dashboard(args.output)


if __name__ == "__main__":
  main()
