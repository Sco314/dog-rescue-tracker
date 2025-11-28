#!/usr/bin/env python3
"""
Dog Rescue Dashboard Generator
v1.0.0

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
  
  # Get recent changes
  cursor.execute("""
    SELECT c.*, d.fit_score as current_fit
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


def generate_changes_html(changes):
  """Generate HTML for recent changes"""
  if not changes:
    return '<div class="change-item"><span class="change-msg">No recent changes</span></div>'
  
  html_parts = []
  for change in changes[:20]:
    change_type = change.get('change_type', '')
    dog_name = change.get('dog_name', 'Unknown')
    old_val = change.get('old_value', '')
    new_val = change.get('new_value', '')
    timestamp = change.get('timestamp', '')
    
    try:
      dt = datetime.fromisoformat(timestamp)
      time_str = dt.strftime('%m/%d %H:%M')
    except:
      time_str = timestamp[:16] if timestamp else '?'
    
    if change_type == 'new_dog':
      icon = '🆕'
      msg = 'New dog listed'
    elif change_type == 'status_change':
      if 'pending' in (new_val or '').lower():
        icon = '⏳'
        msg = f'{old_val} → Pending'
      elif 'available' in (new_val or '').lower():
        icon = '✅'
        msg = f'{old_val} → Available'
      elif 'adopted' in (new_val or '').lower():
        icon = '🏠'
        msg = f'Adopted/Removed'
      else:
        icon = '🔄'
        msg = f'{old_val} → {new_val}'
    else:
      icon = '📝'
      field = change.get('field_changed', '')
      msg = f'{field}: {old_val} → {new_val}'
    
    html_parts.append(f'''
      <div class="change-item">
        <span class="change-icon">{icon}</span>
        <div class="change-details">
          <div class="change-dog">{dog_name}</div>
          <div class="change-msg">{msg}</div>
        </div>
        <span class="change-time">{time_str}</span>
      </div>
    ''')
  
  return ''.join(html_parts)


def generate_html_dashboard(output_path="dashboard.html"):
  """Generate a standalone HTML dashboard file"""
  init_database()
  data = get_dashboard_data()
  
  html = '''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>🐕 Dog Rescue Dashboard</title>
  <style>
    :root {
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
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      background: var(--bg-primary);
      color: var(--text-primary);
      line-height: 1.6;
      padding: 20px;
    }
    .container { max-width: 1400px; margin: 0 auto; }
    header {
      text-align: center;
      margin-bottom: 30px;
      padding: 20px;
      background: var(--bg-secondary);
      border-radius: 12px;
    }
    header h1 { font-size: 2rem; margin-bottom: 10px; }
    .stats { display: flex; justify-content: center; gap: 30px; flex-wrap: wrap; }
    .stat { text-align: center; }
    .stat-value { font-size: 2rem; font-weight: bold; color: var(--accent); }
    .stat-label { color: var(--text-secondary); font-size: 0.875rem; }
    .controls {
      display: flex;
      gap: 15px;
      margin-bottom: 20px;
      flex-wrap: wrap;
      align-items: center;
    }
    .search-box {
      flex: 1;
      min-width: 200px;
      padding: 10px 15px;
      border: 1px solid #374151;
      border-radius: 8px;
      background: var(--bg-card);
      color: var(--text-primary);
      font-size: 1rem;
    }
    .filter-btn {
      padding: 10px 20px;
      border: 1px solid #374151;
      border-radius: 8px;
      background: var(--bg-card);
      color: var(--text-primary);
      cursor: pointer;
      transition: all 0.2s;
    }
    .filter-btn:hover, .filter-btn.active {
      background: var(--accent);
      border-color: var(--accent);
    }
    .sort-select {
      padding: 10px 15px;
      border: 1px solid #374151;
      border-radius: 8px;
      background: var(--bg-card);
      color: var(--text-primary);
      font-size: 1rem;
    }
    .section {
      background: var(--bg-secondary);
      border-radius: 12px;
      padding: 20px;
      margin-bottom: 30px;
    }
    .section-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 15px;
      padding-bottom: 10px;
      border-bottom: 1px solid #374151;
    }
    .section-title {
      font-size: 1.25rem;
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .badge {
      background: var(--accent);
      color: white;
      padding: 2px 10px;
      border-radius: 20px;
      font-size: 0.875rem;
    }
    .dog-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
      gap: 20px;
    }
    .dog-card {
      background: var(--bg-card);
      border-radius: 10px;
      padding: 20px;
      transition: transform 0.2s, box-shadow 0.2s;
    }
    .dog-card:hover {
      transform: translateY(-2px);
      box-shadow: 0 10px 30px rgba(0,0,0,0.3);
    }
    .dog-card.watched { border: 2px solid var(--star); }
    .dog-card.pending { opacity: 0.7; }
    .dog-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 15px;
    }
    .dog-name { font-size: 1.25rem; font-weight: bold; }
    .dog-rescue { font-size: 0.875rem; color: var(--text-secondary); }
    .star-btn {
      background: none;
      border: none;
      font-size: 1.5rem;
      cursor: pointer;
      transition: transform 0.2s;
    }
    .star-btn:hover { transform: scale(1.2); }
    .star-btn.starred { color: var(--star); }
    .star-btn:not(.starred) { color: #4b5563; }
    .dog-score {
      display: flex;
      align-items: center;
      gap: 10px;
      margin-bottom: 15px;
    }
    .score-display {
      font-size: 2rem;
      font-weight: bold;
      min-width: 50px;
      text-align: center;
    }
    .score-high { color: var(--success); }
    .score-medium { color: var(--warning); }
    .score-low { color: var(--danger); }
    .score-controls { display: flex; flex-direction: column; gap: 2px; }
    .score-btn {
      width: 30px;
      height: 24px;
      border: 1px solid #374151;
      border-radius: 4px;
      background: var(--bg-secondary);
      color: var(--text-primary);
      cursor: pointer;
      font-weight: bold;
    }
    .score-btn:hover { background: var(--accent); }
    .score-modifier { font-size: 0.75rem; color: var(--text-secondary); }
    .dog-details {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
      font-size: 0.875rem;
      margin-bottom: 15px;
    }
    .detail { display: flex; justify-content: space-between; }
    .detail-label { color: var(--text-secondary); }
    .detail-value { font-weight: 500; }
    .detail-value.good { color: var(--success); }
    .detail-value.bad { color: var(--danger); }
    .detail-value.unknown { color: var(--text-secondary); }
    .dog-status {
      display: inline-block;
      padding: 4px 12px;
      border-radius: 20px;
      font-size: 0.875rem;
      font-weight: 500;
    }
    .status-available { background: rgba(16, 185, 129, 0.2); color: var(--success); }
    .status-pending { background: rgba(245, 158, 11, 0.2); color: var(--warning); }
    .status-upcoming { background: rgba(59, 130, 246, 0.2); color: var(--accent); }
    .dog-actions {
      display: flex;
      gap: 10px;
      margin-top: 15px;
      padding-top: 15px;
      border-top: 1px solid #374151;
    }
    .action-btn {
      flex: 1;
      padding: 8px 15px;
      border: 1px solid #374151;
      border-radius: 6px;
      background: var(--bg-secondary);
      color: var(--text-primary);
      cursor: pointer;
      font-size: 0.875rem;
      transition: all 0.2s;
    }
    .action-btn:hover { background: var(--accent); border-color: var(--accent); }
    .modal {
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
    }
    .modal.active { display: flex; }
    .modal-content {
      background: var(--bg-secondary);
      border-radius: 12px;
      padding: 30px;
      max-width: 500px;
      width: 90%;
      max-height: 90vh;
      overflow-y: auto;
    }
    .modal-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 20px;
    }
    .modal-title { font-size: 1.5rem; }
    .modal-close {
      background: none;
      border: none;
      font-size: 1.5rem;
      color: var(--text-secondary);
      cursor: pointer;
    }
    .form-group { margin-bottom: 15px; }
    .form-label { display: block; margin-bottom: 5px; color: var(--text-secondary); font-size: 0.875rem; }
    .form-input, .form-select {
      width: 100%;
      padding: 10px;
      border: 1px solid #374151;
      border-radius: 6px;
      background: var(--bg-card);
      color: var(--text-primary);
      font-size: 1rem;
    }
    .form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; }
    .save-btn {
      width: 100%;
      padding: 12px;
      background: var(--success);
      border: none;
      border-radius: 6px;
      color: white;
      font-size: 1rem;
      font-weight: 500;
      cursor: pointer;
      margin-top: 20px;
    }
    .save-btn:hover { opacity: 0.9; }
    .changes-list { max-height: 300px; overflow-y: auto; }
    .change-item {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 10px;
      border-bottom: 1px solid #374151;
    }
    .change-icon { font-size: 1.25rem; }
    .change-details { flex: 1; }
    .change-dog { font-weight: 500; }
    .change-msg { font-size: 0.875rem; color: var(--text-secondary); }
    .change-time { font-size: 0.75rem; color: var(--text-secondary); }
    .toast {
      position: fixed;
      bottom: 20px;
      right: 20px;
      padding: 15px 25px;
      background: var(--success);
      color: white;
      border-radius: 8px;
      z-index: 2000;
      animation: slideIn 0.3s ease;
    }
    @keyframes slideIn {
      from { transform: translateX(100%); opacity: 0; }
      to { transform: translateX(0); opacity: 1; }
    }
    .toast.error { background: var(--danger); }
    .dog-link { color: var(--accent); text-decoration: none; font-size: 0.875rem; }
    .dog-link:hover { text-decoration: underline; }
    @media (max-width: 768px) {
      .dog-grid { grid-template-columns: 1fr; }
      .controls { flex-direction: column; }
      .search-box { width: 100%; }
    }
    .export-section {
      margin-top: 20px;
      padding: 15px;
      background: var(--bg-card);
      border-radius: 8px;
    }
    .export-btn {
      padding: 10px 20px;
      background: var(--accent);
      border: none;
      border-radius: 6px;
      color: white;
      cursor: pointer;
      margin-right: 10px;
    }
    .export-btn:hover { opacity: 0.9; }
  </style>
</head>
<body>
  <div class="container">
    <header>
      <h1>🐕 Dog Rescue Dashboard</h1>
      <p style="color: var(--text-secondary); margin-bottom: 15px;">
        Last updated: ''' + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + '''
      </p>
      <div class="stats">
        <div class="stat">
          <div class="stat-value" id="totalDogs">''' + str(len(data['dogs'])) + '''</div>
          <div class="stat-label">Total Dogs</div>
        </div>
        <div class="stat">
          <div class="stat-value" id="watchCount">''' + str(len([d for d in data['dogs'] if d.get('watch_list') == 'Yes'])) + '''</div>
          <div class="stat-label">Watching</div>
        </div>
        <div class="stat">
          <div class="stat-value" id="highFitCount">''' + str(len([d for d in data['dogs'] if (d.get('fit_score') or 0) >= 5])) + '''</div>
          <div class="stat-label">High Fit (5+)</div>
        </div>
        <div class="stat">
          <div class="stat-value" id="availableCount">''' + str(len([d for d in data['dogs'] if d.get('status') == 'Available'])) + '''</div>
          <div class="stat-label">Available</div>
        </div>
      </div>
    </header>
    
    <div class="controls">
      <input type="text" class="search-box" id="searchBox" placeholder="🔍 Search dogs by name, breed, rescue...">
      <button class="filter-btn active" data-filter="all">All</button>
      <button class="filter-btn" data-filter="watched">⭐ Watched</button>
      <button class="filter-btn" data-filter="high-fit">High Fit</button>
      <button class="filter-btn" data-filter="available">Available</button>
      <button class="filter-btn" data-filter="upcoming">Upcoming</button>
      <select class="sort-select" id="sortSelect">
        <option value="fit-desc">Sort: Fit Score ↓</option>
        <option value="fit-asc">Sort: Fit Score ↑</option>
        <option value="name-asc">Sort: Name A-Z</option>
        <option value="weight-desc">Sort: Weight ↓</option>
        <option value="date-desc">Sort: Newest First</option>
      </select>
    </div>
    
    <div class="section" id="changesSection">
      <div class="section-header">
        <h2 class="section-title">📢 Recent Changes <span class="badge">''' + str(len(data['changes'])) + '''</span></h2>
      </div>
      <div class="changes-list" id="changesList">
        ''' + generate_changes_html(data['changes']) + '''
      </div>
    </div>
    
    <div class="section">
      <div class="section-header">
        <h2 class="section-title">🐕 All Dogs <span class="badge" id="visibleCount">''' + str(len(data['dogs'])) + '''</span></h2>
      </div>
      <div class="dog-grid" id="dogGrid"></div>
      
      <div class="export-section">
        <h3 style="margin-bottom: 10px;">💾 Export Your Changes</h3>
        <p style="font-size: 0.875rem; color: var(--text-secondary); margin-bottom: 15px;">
          Your star ratings, score adjustments, and edits are saved in your browser. 
          Export them to keep a backup or import on another device.
        </p>
        <button class="export-btn" onclick="exportMods()">📥 Export Changes</button>
        <button class="export-btn" onclick="document.getElementById('importFile').click()">📤 Import Changes</button>
        <input type="file" id="importFile" style="display:none" accept=".json" onchange="importMods(event)">
        <button class="export-btn" style="background: var(--danger);" onclick="clearMods()">🗑️ Clear All Changes</button>
      </div>
    </div>
  </div>
  
  <!-- Edit Modal -->
  <div class="modal" id="editModal">
    <div class="modal-content">
      <div class="modal-header">
        <h3 class="modal-title">✏️ Edit Dog</h3>
        <button class="modal-close" onclick="closeModal()">&times;</button>
      </div>
      <form id="editForm">
        <input type="hidden" id="editDogId">
        
        <div class="form-group">
          <label class="form-label">Dog Name</label>
          <input type="text" class="form-input" id="editName" readonly>
        </div>
        
        <div class="form-row">
          <div class="form-group">
            <label class="form-label">Weight (lbs)</label>
            <input type="number" class="form-input" id="editWeight">
          </div>
          <div class="form-group">
            <label class="form-label">Age</label>
            <input type="text" class="form-input" id="editAge" placeholder="e.g., 2 years">
          </div>
        </div>
        
        <div class="form-row">
          <div class="form-group">
            <label class="form-label">Energy Level</label>
            <select class="form-select" id="editEnergy">
              <option value="Unknown">Unknown</option>
              <option value="Low">Low</option>
              <option value="Medium">Medium</option>
              <option value="High">High</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">Shedding</label>
            <select class="form-select" id="editShedding">
              <option value="Unknown">Unknown</option>
              <option value="None">None</option>
              <option value="Low">Low</option>
              <option value="Moderate">Moderate</option>
              <option value="High">High</option>
            </select>
          </div>
        </div>
        
        <div class="form-row">
          <div class="form-group">
            <label class="form-label">Good with Dogs</label>
            <select class="form-select" id="editGoodDogs">
              <option value="Unknown">Unknown</option>
              <option value="Yes">Yes</option>
              <option value="No">No</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">Good with Kids</label>
            <select class="form-select" id="editGoodKids">
              <option value="Unknown">Unknown</option>
              <option value="Yes">Yes</option>
              <option value="No">No</option>
            </select>
          </div>
        </div>
        
        <div class="form-row">
          <div class="form-group">
            <label class="form-label">Good with Cats</label>
            <select class="form-select" id="editGoodCats">
              <option value="Unknown">Unknown</option>
              <option value="Yes">Yes</option>
              <option value="No">No</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">Special Needs</label>
            <select class="form-select" id="editSpecialNeeds">
              <option value="No">No</option>
              <option value="Yes">Yes</option>
            </select>
          </div>
        </div>
        
        <div class="form-group">
          <label class="form-label">Notes</label>
          <textarea class="form-input" id="editNotes" rows="3" placeholder="Add any notes..."></textarea>
        </div>
        
        <button type="submit" class="save-btn">💾 Save Changes</button>
      </form>
    </div>
  </div>
  
  <script>
    // Dog data embedded in page
    let dogsData = ''' + json.dumps(data['dogs'], default=str) + ''';
    
    // Local storage for modifications
    let localMods = JSON.parse(localStorage.getItem('dogMods') || '{}');
    
    function applyLocalMods() {
      dogsData.forEach(dog => {
        if (localMods[dog.dog_id]) {
          Object.assign(dog, localMods[dog.dog_id]);
        }
      });
    }
    
    function saveMod(dogId, changes) {
      if (!localMods[dogId]) localMods[dogId] = {};
      Object.assign(localMods[dogId], changes);
      localStorage.setItem('dogMods', JSON.stringify(localMods));
      const dog = dogsData.find(d => d.dog_id === dogId);
      if (dog) Object.assign(dog, changes);
    }
    
    function toggleWatch(dogId) {
      const dog = dogsData.find(d => d.dog_id === dogId);
      if (!dog) return;
      const newValue = dog.watch_list === 'Yes' ? '' : 'Yes';
      saveMod(dogId, { watch_list: newValue });
      renderDogs();
      updateStats();
      showToast(newValue === 'Yes' ? '⭐ Added to watch list' : 'Removed from watch list');
    }
    
    function adjustScore(dogId, delta) {
      const dog = dogsData.find(d => d.dog_id === dogId);
      if (!dog) return;
      const currentMod = localMods[dogId]?.score_modifier || 0;
      const newMod = currentMod + delta;
      const baseScore = (dog.base_fit_score !== undefined) ? dog.base_fit_score : (dog.fit_score || 0);
      if (dog.base_fit_score === undefined) {
        saveMod(dogId, { base_fit_score: dog.fit_score || 0 });
      }
      const newScore = Math.max(0, baseScore + newMod);
      saveMod(dogId, { score_modifier: newMod, fit_score: newScore });
      renderDogs();
      updateStats();
      showToast('Score adjusted to ' + newScore);
    }
    
    function openEdit(dogId) {
      const dog = dogsData.find(d => d.dog_id === dogId);
      if (!dog) return;
      document.getElementById('editDogId').value = dogId;
      document.getElementById('editName').value = dog.dog_name || '';
      document.getElementById('editWeight').value = dog.weight || '';
      document.getElementById('editAge').value = dog.age_range || '';
      document.getElementById('editEnergy').value = dog.energy_level || 'Unknown';
      document.getElementById('editShedding').value = dog.shedding || 'Unknown';
      document.getElementById('editGoodDogs').value = dog.good_with_dogs || 'Unknown';
      document.getElementById('editGoodKids').value = dog.good_with_kids || 'Unknown';
      document.getElementById('editGoodCats').value = dog.good_with_cats || 'Unknown';
      document.getElementById('editSpecialNeeds').value = dog.special_needs || 'No';
      document.getElementById('editNotes').value = dog.notes || '';
      document.getElementById('editModal').classList.add('active');
    }
    
    function closeModal() {
      document.getElementById('editModal').classList.remove('active');
    }
    
    document.getElementById('editForm').addEventListener('submit', function(e) {
      e.preventDefault();
      const dogId = document.getElementById('editDogId').value;
      const changes = {
        weight: parseInt(document.getElementById('editWeight').value) || null,
        age_range: document.getElementById('editAge').value,
        energy_level: document.getElementById('editEnergy').value,
        shedding: document.getElementById('editShedding').value,
        good_with_dogs: document.getElementById('editGoodDogs').value,
        good_with_kids: document.getElementById('editGoodKids').value,
        good_with_cats: document.getElementById('editGoodCats').value,
        special_needs: document.getElementById('editSpecialNeeds').value,
        notes: document.getElementById('editNotes').value
      };
      changes.fit_score = calculateFitScore(dogId, changes);
      saveMod(dogId, changes);
      closeModal();
      renderDogs();
      updateStats();
      showToast('✅ Changes saved!');
    });
    
    function calculateFitScore(dogId, changes) {
      const dog = dogsData.find(d => d.dog_id === dogId);
      if (!dog) return 0;
      let score = 0;
      const data = { ...dog, ...changes };
      if (data.weight && data.weight >= 40) score += 2;
      if (data.shedding === 'None') score += 2;
      else if (data.shedding === 'Low') score += 1;
      else if (data.shedding === 'High') score -= 1;
      else if (data.shedding === 'Unknown') score += 1;
      if (data.energy_level === 'Low' || data.energy_level === 'Medium') score += 2;
      else if (data.energy_level === 'Unknown') score += 1;
      if (data.good_with_dogs === 'Yes') score += 2;
      if (data.good_with_kids === 'Yes') score += 1;
      if (data.good_with_cats === 'Yes') score += 1;
      const breed = (data.breed || '').toLowerCase();
      if (breed.includes('doodle') || breed.includes('poodle') || breed.includes('poo')) score += 1;
      if (data.special_needs === 'Yes') score -= 1;
      if (data.status === 'Pending') score -= 2;
      const mod = localMods[dogId]?.score_modifier || 0;
      return Math.max(0, score + mod);
    }
    
    function showToast(message, isError = false) {
      const toast = document.createElement('div');
      toast.className = 'toast' + (isError ? ' error' : '');
      toast.textContent = message;
      document.body.appendChild(toast);
      setTimeout(() => toast.remove(), 3000);
    }
    
    function renderDogs() {
      const grid = document.getElementById('dogGrid');
      const searchTerm = document.getElementById('searchBox').value.toLowerCase();
      const activeFilter = document.querySelector('.filter-btn.active').dataset.filter;
      const sortBy = document.getElementById('sortSelect').value;
      
      let filtered = dogsData.filter(dog => {
        const searchMatch = !searchTerm || 
          (dog.dog_name || '').toLowerCase().includes(searchTerm) ||
          (dog.breed || '').toLowerCase().includes(searchTerm) ||
          (dog.rescue_name || '').toLowerCase().includes(searchTerm);
        if (!searchMatch) return false;
        switch (activeFilter) {
          case 'watched': return dog.watch_list === 'Yes';
          case 'high-fit': return (dog.fit_score || 0) >= 5;
          case 'available': return dog.status === 'Available';
          case 'upcoming': return dog.status === 'Upcoming';
          default: return true;
        }
      });
      
      filtered.sort((a, b) => {
        switch (sortBy) {
          case 'fit-desc': return (b.fit_score || 0) - (a.fit_score || 0);
          case 'fit-asc': return (a.fit_score || 0) - (b.fit_score || 0);
          case 'name-asc': return (a.dog_name || '').localeCompare(b.dog_name || '');
          case 'weight-desc': return (b.weight || 0) - (a.weight || 0);
          case 'date-desc': return (b.date_first_seen || '').localeCompare(a.date_first_seen || '');
          default: return 0;
        }
      });
      
      document.getElementById('visibleCount').textContent = filtered.length;
      grid.innerHTML = filtered.map(dog => generateDogCard(dog)).join('');
    }
    
    function generateDogCard(dog) {
      const isWatched = dog.watch_list === 'Yes';
      const scoreClass = (dog.fit_score || 0) >= 5 ? 'score-high' : (dog.fit_score || 0) >= 3 ? 'score-medium' : 'score-low';
      const statusClass = (dog.status || '').toLowerCase();
      const mod = localMods[dog.dog_id]?.score_modifier || 0;
      const modDisplay = mod !== 0 ? '(' + (mod > 0 ? '+' : '') + mod + ')' : '';
      const valueClass = (val) => val === 'Yes' ? 'good' : val === 'No' ? 'bad' : 'unknown';
      const url = dog.source_url || '#';
      
      return '<div class="dog-card ' + (isWatched ? 'watched' : '') + ' ' + (statusClass === 'pending' ? 'pending' : '') + '">' +
        '<div class="dog-header">' +
          '<div>' +
            '<div class="dog-name">' + (dog.dog_name || 'Unknown') + '</div>' +
            '<div class="dog-rescue">' + (dog.rescue_name || 'Unknown Rescue') + '</div>' +
          '</div>' +
          '<button class="star-btn ' + (isWatched ? 'starred' : '') + '" onclick="toggleWatch(\'' + dog.dog_id + '\')">' + (isWatched ? '★' : '☆') + '</button>' +
        '</div>' +
        '<div class="dog-score">' +
          '<div class="score-display ' + scoreClass + '">' + (dog.fit_score || 0) + '</div>' +
          '<div class="score-controls">' +
            '<button class="score-btn" onclick="adjustScore(\'' + dog.dog_id + '\', 1)">+</button>' +
            '<button class="score-btn" onclick="adjustScore(\'' + dog.dog_id + '\', -1)">−</button>' +
          '</div>' +
          '<div class="score-modifier">' + modDisplay + '</div>' +
          '<span class="dog-status status-' + statusClass + '">' + (dog.status || 'Unknown') + '</span>' +
        '</div>' +
        '<div class="dog-details">' +
          '<div class="detail"><span class="detail-label">Weight</span><span class="detail-value">' + (dog.weight ? dog.weight + ' lbs' : '?') + '</span></div>' +
          '<div class="detail"><span class="detail-label">Age</span><span class="detail-value">' + (dog.age_range || '?') + '</span></div>' +
          '<div class="detail"><span class="detail-label">Breed</span><span class="detail-value">' + (dog.breed || '?') + '</span></div>' +
          '<div class="detail"><span class="detail-label">Energy</span><span class="detail-value">' + (dog.energy_level || '?') + '</span></div>' +
          '<div class="detail"><span class="detail-label">Dogs</span><span class="detail-value ' + valueClass(dog.good_with_dogs) + '">' + (dog.good_with_dogs || '?') + '</span></div>' +
          '<div class="detail"><span class="detail-label">Kids</span><span class="detail-value ' + valueClass(dog.good_with_kids) + '">' + (dog.good_with_kids || '?') + '</span></div>' +
          '<div class="detail"><span class="detail-label">Cats</span><span class="detail-value ' + valueClass(dog.good_with_cats) + '">' + (dog.good_with_cats || '?') + '</span></div>' +
          '<div class="detail"><span class="detail-label">Shedding</span><span class="detail-value">' + (dog.shedding || '?') + '</span></div>' +
        '</div>' +
        (dog.notes ? '<div style="font-size: 0.875rem; color: var(--text-secondary); margin-bottom: 10px;">📝 ' + dog.notes + '</div>' : '') +
        '<a href="' + url + '" target="_blank" class="dog-link">🔗 View on rescue site</a>' +
        '<div class="dog-actions">' +
          '<button class="action-btn" onclick="openEdit(\'' + dog.dog_id + '\')">✏️ Edit</button>' +
        '</div>' +
      '</div>';
    }
    
    function updateStats() {
      document.getElementById('totalDogs').textContent = dogsData.length;
      document.getElementById('watchCount').textContent = dogsData.filter(d => d.watch_list === 'Yes').length;
      document.getElementById('highFitCount').textContent = dogsData.filter(d => (d.fit_score || 0) >= 5).length;
      document.getElementById('availableCount').textContent = dogsData.filter(d => d.status === 'Available').length;
    }
    
    function exportMods() {
      const data = JSON.stringify(localMods, null, 2);
      const blob = new Blob([data], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'dog-dashboard-changes.json';
      a.click();
      URL.revokeObjectURL(url);
      showToast('✅ Changes exported!');
    }
    
    function importMods(event) {
      const file = event.target.files[0];
      if (!file) return;
      const reader = new FileReader();
      reader.onload = function(e) {
        try {
          const imported = JSON.parse(e.target.result);
          Object.assign(localMods, imported);
          localStorage.setItem('dogMods', JSON.stringify(localMods));
          applyLocalMods();
          renderDogs();
          updateStats();
          showToast('✅ Changes imported!');
        } catch (err) {
          showToast('❌ Invalid file', true);
        }
      };
      reader.readAsText(file);
    }
    
    function clearMods() {
      if (confirm('Are you sure you want to clear all your changes? This cannot be undone.')) {
        localMods = {};
        localStorage.removeItem('dogMods');
        location.reload();
      }
    }
    
    document.getElementById('searchBox').addEventListener('input', renderDogs);
    document.getElementById('sortSelect').addEventListener('change', renderDogs);
    document.querySelectorAll('.filter-btn').forEach(btn => {
      btn.addEventListener('click', function() {
        document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
        this.classList.add('active');
        renderDogs();
      });
    });
    document.getElementById('editModal').addEventListener('click', function(e) {
      if (e.target === this) closeModal();
    });
    
    applyLocalMods();
    renderDogs();
    updateStats();
  </script>
</body>
</html>
'''
  
  with open(output_path, 'w', encoding='utf-8') as f:
    f.write(html)
  
  print(f"✅ Dashboard generated: {output_path}")
  return output_path


def main():
  parser = argparse.ArgumentParser(description="Dog Rescue Dashboard Generator")
  parser.add_argument("--output", "-o", default="dashboard.html", help="Output HTML file")
  args = parser.parse_args()
  generate_html_dashboard(args.output)


if __name__ == "__main__":
  main()
