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
    
    /* Score Breakdown Panel */
    .score-breakdown {
      background: var(--bg-card);
      border: 1px solid #374151;
      border-radius: 8px;
      padding: 15px;
      margin-bottom: 20px;
    }
    .score-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 12px;
      padding-bottom: 8px;
      border-bottom: 1px solid #374151;
    }
    .score-title { font-weight: 600; color: var(--text-secondary); }
    .score-total {
      font-size: 1.5rem;
      font-weight: 700;
      color: var(--accent);
      background: rgba(96, 165, 250, 0.15);
      padding: 4px 12px;
      border-radius: 6px;
    }
    .score-items {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 6px 15px;
      font-size: 0.85rem;
    }
    .score-item {
      display: flex;
      justify-content: space-between;
      padding: 4px 0;
    }
    .score-item-label { color: var(--text-secondary); }
    .score-item-value { font-weight: 600; }
    .score-item-value.positive { color: var(--success); }
    .score-item-value.negative { color: var(--danger); }
    .score-item-value.neutral { color: var(--text-secondary); }
    .score-note {
      margin-top: 12px;
      padding-top: 10px;
      border-top: 1px solid #374151;
      font-size: 0.75rem;
      color: var(--warning);
      text-align: center;
    }
    .score-adjust-row {
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .score-adjust-hint {
      font-size: 0.8rem;
      color: var(--text-secondary);
    }
    
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
    .save-status {
      text-align: center;
      margin-top: 10px;
      min-height: 20px;
      font-size: 0.875rem;
    }
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
      <div style="display: flex; justify-content: space-between; align-items: flex-start;">
        <h1>🐕 Dog Rescue Dashboard</h1>
        <button class="export-btn" onclick="openConfigModal()" style="background: var(--bg-card);">⚙️ Settings</button>
      </div>
      <p style="color: var(--text-secondary); margin-bottom: 15px;">
        Last updated: ''' + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + '''
        <span id="syncStatus" style="margin-left: 10px;"></span>
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
        <h3 style="margin-bottom: 10px;">📤 Backup / Restore</h3>
        <p style="font-size: 0.85rem; color: var(--text-secondary); margin-bottom: 10px;">
          Your changes sync automatically to GitHub. Use these buttons to backup or transfer settings.
        </p>
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
        
        <!-- Scoring Breakdown Panel -->
        <div class="score-breakdown" id="scoreBreakdown">
          <div class="score-header">
            <span class="score-title">📊 Fit Score Breakdown</span>
            <span class="score-total" id="scoreTotal">0</span>
          </div>
          <div class="score-items" id="scoreItems">
            <!-- Populated by JS -->
          </div>
          <div class="score-note">
            ⚠️ Changes saved in browser only (localStorage). Export to keep them.
          </div>
        </div>
        
        <div class="form-row">
          <div class="form-group">
            <label class="form-label">Weight (lbs)</label>
            <input type="number" class="form-input score-input" id="editWeight">
          </div>
          <div class="form-group">
            <label class="form-label">Age</label>
            <input type="text" class="form-input score-input" id="editAge" placeholder="e.g., 2 yrs, 8 mos">
          </div>
        </div>
        
        <div class="form-row">
          <div class="form-group">
            <label class="form-label">Energy Level</label>
            <select class="form-select score-input" id="editEnergy">
              <option value="Unknown">Unknown</option>
              <option value="Low">Low</option>
              <option value="Medium">Medium</option>
              <option value="High">High</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">Shedding</label>
            <select class="form-select score-input" id="editShedding">
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
            <select class="form-select score-input" id="editGoodDogs">
              <option value="Unknown">Unknown</option>
              <option value="Yes">Yes</option>
              <option value="No">No</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">Good with Kids</label>
            <select class="form-select score-input" id="editGoodKids">
              <option value="Unknown">Unknown</option>
              <option value="Yes">Yes</option>
              <option value="No">No</option>
            </select>
          </div>
        </div>
        
        <div class="form-row">
          <div class="form-group">
            <label class="form-label">Good with Cats</label>
            <select class="form-select score-input" id="editGoodCats">
              <option value="Unknown">Unknown</option>
              <option value="Yes">Yes</option>
              <option value="No">No</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">Special Needs</label>
            <select class="form-select score-input" id="editSpecialNeeds">
              <option value="No">No</option>
              <option value="Yes">Yes</option>
            </select>
          </div>
        </div>
        
        <div class="form-group">
          <label class="form-label">Manual Score Adjustment</label>
          <div class="score-adjust-row">
            <input type="number" class="form-input score-input" id="editScoreModifier" value="0" style="width: 80px; text-align: center;">
            <span class="score-adjust-hint">Add/subtract from calculated score</span>
          </div>
        </div>
        
        <div class="form-group">
          <label class="form-label">Notes</label>
          <textarea class="form-input" id="editNotes" rows="2" placeholder="Add any notes..."></textarea>
        </div>
        
        <button type="submit" class="save-btn" id="saveBtn">💾 Save Changes</button>
        <div class="save-status" id="saveStatus"></div>
      </form>
    </div>
  </div>
  
  <!-- GitHub Token Config Modal -->
  <div class="modal" id="configModal">
    <div class="modal-content" style="max-width: 450px;">
      <div class="modal-header">
        <h3 class="modal-title">⚙️ Setup GitHub Sync</h3>
        <button class="modal-close" onclick="closeConfigModal()">&times;</button>
      </div>
      <p style="color: var(--text-secondary); margin-bottom: 15px; font-size: 0.9rem;">
        To save changes across devices, enter your GitHub Personal Access Token. 
        This is stored in your browser only.
      </p>
      <div class="form-group">
        <label class="form-label">GitHub Token</label>
        <input type="password" class="form-input" id="githubTokenInput" placeholder="ghp_xxxxxxxxxxxx">
      </div>
      <p style="color: var(--text-secondary); font-size: 0.75rem; margin-bottom: 15px;">
        Create a fine-grained token at GitHub → Settings → Developer settings → Personal access tokens.<br>
        Repository access: Sco314/dog-rescue-tracker only<br>
        Permissions: Contents (Read and write)
      </p>
      <button class="save-btn" onclick="saveGitHubToken()">💾 Save Token</button>
    </div>
  </div>
  
  <script>
    // ===========================================
    // GITHUB CONFIGURATION
    // ===========================================
    const GITHUB_REPO = 'Sco314/dog-rescue-tracker';
    const OVERRIDES_FILE = 'user_overrides.json';
    const GITHUB_API = 'https://api.github.com';
    
    // Get token from localStorage
    let githubToken = localStorage.getItem('githubToken') || '';
    
    // ===========================================
    // DATA
    // ===========================================
    let dogsData = ''' + json.dumps(data['dogs'], default=str) + ''';
    
    // User overrides (loaded from GitHub)
    let userOverrides = { dogs: {} };
    let overridesFileSha = null; // Needed for GitHub updates
    let isSaving = false;
    
    // ===========================================
    // GITHUB SYNC FUNCTIONS  
    // ===========================================
    
    async function loadOverridesFromGitHub() {
      try {
        // Try to fetch from GitHub Pages first (faster, no auth needed)
        const pagesUrl = 'https://sco314.github.io/dog-rescue-tracker/' + OVERRIDES_FILE + '?t=' + Date.now();
        let response = await fetch(pagesUrl);
        
        if (response.ok) {
          userOverrides = await response.json();
          console.log('✅ Loaded overrides from GitHub Pages');
        } else {
          // Fallback to API
          response = await fetch(GITHUB_API + '/repos/' + GITHUB_REPO + '/contents/' + OVERRIDES_FILE);
          if (response.ok) {
            const data = await response.json();
            overridesFileSha = data.sha;
            userOverrides = JSON.parse(atob(data.content));
            console.log('✅ Loaded overrides from GitHub API');
          }
        }
        
        applyOverrides();
      } catch (err) {
        console.log('ℹ️ No overrides file found or error loading:', err.message);
      }
    }
    
    async function saveOverridesToGitHub() {
      if (!githubToken) {
        document.getElementById('configModal').classList.add('active');
        return false;
      }
      
      if (isSaving) return false;
      isSaving = true;
      updateSaveStatus('saving');
      
      try {
        // Update metadata
        userOverrides._meta = userOverrides._meta || {};
        userOverrides._meta.last_updated = new Date().toISOString();
        userOverrides._meta.version = '1.0';
        
        // Get current file SHA (needed for update)
        let sha = overridesFileSha;
        if (!sha) {
          const getResponse = await fetch(GITHUB_API + '/repos/' + GITHUB_REPO + '/contents/' + OVERRIDES_FILE, {
            headers: { 'Authorization': 'Bearer ' + githubToken }
          });
          if (getResponse.ok) {
            const data = await getResponse.json();
            sha = data.sha;
          }
        }
        
        // Prepare content
        const content = btoa(unescape(encodeURIComponent(JSON.stringify(userOverrides, null, 2))));
        
        // Commit to GitHub
        const body = {
          message: '🐕 Update dog overrides from dashboard',
          content: content
        };
        if (sha) body.sha = sha;
        
        const response = await fetch(GITHUB_API + '/repos/' + GITHUB_REPO + '/contents/' + OVERRIDES_FILE, {
          method: 'PUT',
          headers: {
            'Authorization': 'Bearer ' + githubToken,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(body)
        });
        
        if (response.ok) {
          const result = await response.json();
          overridesFileSha = result.content.sha;
          console.log('✅ Saved to GitHub');
          updateSaveStatus('saved');
          isSaving = false;
          return true;
        } else {
          const err = await response.json();
          console.error('❌ GitHub save failed:', err);
          updateSaveStatus('error', err.message);
          isSaving = false;
          return false;
        }
      } catch (err) {
        console.error('❌ GitHub save error:', err);
        updateSaveStatus('error', err.message);
        isSaving = false;
        return false;
      }
    }
    
    function updateSaveStatus(status, message) {
      const el = document.getElementById('saveStatus');
      if (!el) return;
      
      if (status === 'saving') {
        el.innerHTML = '<span style="color: var(--warning);">⏳ Saving...</span>';
      } else if (status === 'saved') {
        el.innerHTML = '<span style="color: var(--success);">✅ Saved to GitHub!</span>';
        setTimeout(() => { el.innerHTML = ''; }, 3000);
      } else if (status === 'error') {
        el.innerHTML = '<span style="color: var(--danger);">❌ Error: ' + (message || 'Save failed') + '</span>';
      } else {
        el.innerHTML = '';
      }
    }
    
    function applyOverrides() {
      dogsData.forEach(dog => {
        const override = userOverrides.dogs[dog.dog_id];
        if (override) {
          Object.assign(dog, override);
          // Recalculate fit score if we have overrides
          if (override.score_modifier !== undefined || override.weight !== undefined) {
            dog.fit_score = calculateFitScoreFromDog(dog);
          }
        }
      });
    }
    
    function saveOverride(dogId, changes) {
      if (!userOverrides.dogs[dogId]) {
        userOverrides.dogs[dogId] = {};
      }
      Object.assign(userOverrides.dogs[dogId], changes);
      
      // Also update local dogsData
      const dog = dogsData.find(d => d.dog_id === dogId);
      if (dog) Object.assign(dog, changes);
    }
    
    // ===========================================
    // CONFIG MODAL
    // ===========================================
    
    function openConfigModal() {
      document.getElementById('githubTokenInput').value = githubToken;
      document.getElementById('configModal').classList.add('active');
    }
    
    function closeConfigModal() {
      document.getElementById('configModal').classList.remove('active');
    }
    
    function saveGitHubToken() {
      githubToken = document.getElementById('githubTokenInput').value.trim();
      localStorage.setItem('githubToken', githubToken);
      closeConfigModal();
      showToast('✅ Token saved!');
    }
    
    // ===========================================
    // WATCH LIST (FAVORITES)
    // ===========================================
    
    async function toggleWatch(dogId) {
      const dog = dogsData.find(d => d.dog_id === dogId);
      if (!dog) return;
      const newValue = dog.watch_list === 'Yes' ? '' : 'Yes';
      saveOverride(dogId, { watch_list: newValue });
      renderDogs();
      updateStats();
      
      // Save to GitHub
      const saved = await saveOverridesToGitHub();
      if (saved) {
        showToast(newValue === 'Yes' ? '⭐ Added to watch list' : 'Removed from watch list');
      }
    }
    
    async function adjustScore(dogId, delta) {
      const dog = dogsData.find(d => d.dog_id === dogId);
      if (!dog) return;
      
      const currentMod = userOverrides.dogs[dogId]?.score_modifier || 0;
      const newMod = currentMod + delta;
      
      // Calculate new score
      dog.score_modifier = newMod;
      const newScore = calculateFitScoreFromDog(dog);
      
      saveOverride(dogId, { score_modifier: newMod, fit_score: newScore });
      renderDogs();
      updateStats();
      
      // Save to GitHub
      const saved = await saveOverridesToGitHub();
      if (saved) {
        showToast('Score adjusted to ' + newScore);
      }
    }
    
    function calculateFitScoreFromDog(dog) {
      let score = 0;
      
      // Weight (40+ = +2)
      if (dog.weight && dog.weight >= 40) score += 2;
      
      // Age scoring
      score += calculateAgeScore(dog.age_range || '');
      
      // Shedding
      const shedding = dog.shedding || 'Unknown';
      if (shedding === 'None') score += 2;
      else if (shedding === 'Low') score += 1;
      else if (shedding === 'High') score -= 1;
      else if (shedding === 'Unknown') score += 1;
      
      // Energy
      const energy = dog.energy_level || 'Unknown';
      if (energy === 'Low' || energy === 'Medium') score += 2;
      else if (energy === 'Unknown') score += 1;
      
      // Compatibility
      if (dog.good_with_dogs === 'Yes') score += 2;
      if (dog.good_with_kids === 'Yes') score += 1;
      if (dog.good_with_cats === 'Yes') score += 1;
      
      // Breed bonus
      const breed = (dog.breed || '').toLowerCase();
      if (breed.includes('doodle') || breed.includes('poodle') || breed.includes('poo')) score += 1;
      
      // Special needs
      if (dog.special_needs === 'Yes') score -= 1;
      
      // Manual modifier
      const mod = dog.score_modifier || 0;
      return Math.max(0, score + mod);
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
      document.getElementById('editScoreModifier').value = localMods[dogId]?.score_modifier || 0;
      document.getElementById('editNotes').value = dog.notes || '';
      updateScoreBreakdown();
      document.getElementById('editModal').classList.add('active');
    }
    
    function updateScoreBreakdown() {
      const dogId = document.getElementById('editDogId').value;
      const dog = dogsData.find(d => d.dog_id === dogId);
      if (!dog) return;
      
      const data = {
        weight: parseInt(document.getElementById('editWeight').value) || null,
        age_range: document.getElementById('editAge').value,
        energy_level: document.getElementById('editEnergy').value,
        shedding: document.getElementById('editShedding').value,
        good_with_dogs: document.getElementById('editGoodDogs').value,
        good_with_kids: document.getElementById('editGoodKids').value,
        good_with_cats: document.getElementById('editGoodCats').value,
        special_needs: document.getElementById('editSpecialNeeds').value,
        breed: dog.breed || ''
      };
      const mod = parseInt(document.getElementById('editScoreModifier').value) || 0;
      
      // Calculate each component
      const breakdown = calculateScoreBreakdown(data);
      breakdown.push({ label: 'Manual Adjust', value: mod });
      
      // Build HTML
      let html = '';
      let total = 0;
      breakdown.forEach(item => {
        const valueClass = item.value > 0 ? 'positive' : (item.value < 0 ? 'negative' : 'neutral');
        const sign = item.value > 0 ? '+' : '';
        html += '<div class="score-item">';
        html += '<span class="score-item-label">' + item.label + '</span>';
        html += '<span class="score-item-value ' + valueClass + '">' + sign + item.value + '</span>';
        html += '</div>';
        total += item.value;
      });
      
      total = Math.max(0, total);
      document.getElementById('scoreItems').innerHTML = html;
      document.getElementById('scoreTotal').textContent = total;
    }
    
    function calculateScoreBreakdown(data) {
      const items = [];
      
      // Weight (40+ lbs = +2)
      if (data.weight && data.weight >= 40) {
        items.push({ label: 'Weight ≥40 lbs', value: 2 });
      } else if (data.weight) {
        items.push({ label: 'Weight <40 lbs', value: 0 });
      } else {
        items.push({ label: 'Weight (unknown)', value: 0 });
      }
      
      // Age scoring
      const ageScore = calculateAgeScore(data.age_range);
      items.push({ label: 'Age: ' + (data.age_range || '?'), value: ageScore });
      
      // Shedding
      const shedScores = { 'None': 2, 'Low': 1, 'Moderate': 0, 'High': -1, 'Unknown': 1 };
      items.push({ label: 'Shedding: ' + data.shedding, value: shedScores[data.shedding] || 1 });
      
      // Energy
      const energyScores = { 'Low': 2, 'Medium': 2, 'High': 0, 'Unknown': 1 };
      items.push({ label: 'Energy: ' + data.energy_level, value: energyScores[data.energy_level] || 1 });
      
      // Good with dogs (+2)
      if (data.good_with_dogs === 'Yes') {
        items.push({ label: 'Good w/ Dogs ✓', value: 2 });
      } else {
        items.push({ label: 'Good w/ Dogs: ' + data.good_with_dogs, value: 0 });
      }
      
      // Good with kids (+1)
      if (data.good_with_kids === 'Yes') {
        items.push({ label: 'Good w/ Kids ✓', value: 1 });
      } else {
        items.push({ label: 'Good w/ Kids: ' + data.good_with_kids, value: 0 });
      }
      
      // Good with cats (+1)
      if (data.good_with_cats === 'Yes') {
        items.push({ label: 'Good w/ Cats ✓', value: 1 });
      } else {
        items.push({ label: 'Good w/ Cats: ' + data.good_with_cats, value: 0 });
      }
      
      // Doodle bonus (+1)
      const breed = (data.breed || '').toLowerCase();
      if (breed.includes('doodle') || breed.includes('poodle') || breed.includes('poo')) {
        items.push({ label: 'Doodle Breed ✓', value: 1 });
      } else {
        items.push({ label: 'Non-doodle breed', value: 0 });
      }
      
      // Special needs (-1)
      if (data.special_needs === 'Yes') {
        items.push({ label: 'Special Needs', value: -1 });
      }
      
      return items;
    }
    
    function calculateAgeScore(ageStr) {
      if (!ageStr) return 0;
      ageStr = ageStr.toLowerCase().replace(/–/g, '-').replace(/—/g, '-');
      
      // Try range first: "1-3 yrs"
      let match = ageStr.match(/(\\d+\\.?\\d*)\\s*-\\s*(\\d+\\.?\\d*)\\s*(yr|year|mo|month|wk|week)/);
      if (match) {
        let min = parseFloat(match[1]);
        let max = parseFloat(match[2]);
        const unit = match[3];
        if (unit.startsWith('mo')) { min /= 12; max /= 12; }
        else if (unit.startsWith('wk') || unit.startsWith('week')) { min /= 52; max /= 52; }
        return Math.max(ageToScore(min), ageToScore(max));
      }
      
      // Single value: "2 yrs", "8 mos"
      match = ageStr.match(/(\\d+\\.?\\d*)\\s*(yr|year|mo|month|wk|week)/);
      if (match) {
        let age = parseFloat(match[1]);
        const unit = match[2];
        if (unit.startsWith('mo')) age /= 12;
        else if (unit.startsWith('wk') || unit.startsWith('week')) age /= 52;
        return ageToScore(age);
      }
      
      return 0;
    }
    
    function ageToScore(years) {
      if (years < 0.75) return 0;
      if (years < 1.0) return 1;
      if (years < 2.0) return 2;
      if (years < 3.0) return 1;
      if (years < 4.0) return 0;
      if (years < 5.0) return -1;
      if (years < 6.0) return -2;
      return -4;
    }
    
    // Add event listeners to update breakdown on field changes
    document.querySelectorAll('.score-input').forEach(el => {
      el.addEventListener('change', updateScoreBreakdown);
      el.addEventListener('input', updateScoreBreakdown);
    });
    
    function closeModal() {
      document.getElementById('editModal').classList.remove('active');
      updateSaveStatus('');
    }
    
    document.getElementById('editForm').addEventListener('submit', async function(e) {
      e.preventDefault();
      const dogId = document.getElementById('editDogId').value;
      const scoreModifier = parseInt(document.getElementById('editScoreModifier').value) || 0;
      const changes = {
        weight: parseInt(document.getElementById('editWeight').value) || null,
        age_range: document.getElementById('editAge').value,
        energy_level: document.getElementById('editEnergy').value,
        shedding: document.getElementById('editShedding').value,
        good_with_dogs: document.getElementById('editGoodDogs').value,
        good_with_kids: document.getElementById('editGoodKids').value,
        good_with_cats: document.getElementById('editGoodCats').value,
        special_needs: document.getElementById('editSpecialNeeds').value,
        notes: document.getElementById('editNotes').value,
        score_modifier: scoreModifier
      };
      
      // Calculate fit score with the new data
      const dog = dogsData.find(d => d.dog_id === dogId);
      if (dog) {
        Object.assign(dog, changes);
        changes.fit_score = calculateFitScoreFromDog(dog);
      }
      
      // Save to userOverrides
      saveOverride(dogId, changes);
      
      // Save to GitHub
      const saved = await saveOverridesToGitHub();
      
      if (saved) {
        closeModal();
        renderDogs();
        updateStats();
        showToast('✅ Changes saved!');
      }
    });
    
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
      const dogId = dog.dog_id;
      
      const card = document.createElement('div');
      card.className = 'dog-card' + (isWatched ? ' watched' : '') + (statusClass === 'pending' ? ' pending' : '');
      
      card.innerHTML = `
        <div class="dog-header">
          <div>
            <div class="dog-name">${dog.dog_name || 'Unknown'}</div>
            <div class="dog-rescue">${dog.rescue_name || 'Unknown Rescue'}</div>
          </div>
          <button class="star-btn ${isWatched ? 'starred' : ''}" data-action="watch" data-id="${dogId}">${isWatched ? '★' : '☆'}</button>
        </div>
        <div class="dog-score">
          <div class="score-display ${scoreClass}">${dog.fit_score || 0}</div>
          <div class="score-controls">
            <button class="score-btn" data-action="score-up" data-id="${dogId}">+</button>
            <button class="score-btn" data-action="score-down" data-id="${dogId}">−</button>
          </div>
          <div class="score-modifier">${modDisplay}</div>
          <span class="dog-status status-${statusClass}">${dog.status || 'Unknown'}</span>
        </div>
        <div class="dog-details">
          <div class="detail"><span class="detail-label">Weight</span><span class="detail-value">${dog.weight ? dog.weight + ' lbs' : '?'}</span></div>
          <div class="detail"><span class="detail-label">Age</span><span class="detail-value">${dog.age_range || '?'}</span></div>
          <div class="detail"><span class="detail-label">Breed</span><span class="detail-value">${dog.breed || '?'}</span></div>
          <div class="detail"><span class="detail-label">Energy</span><span class="detail-value">${dog.energy_level || '?'}</span></div>
          <div class="detail"><span class="detail-label">Dogs</span><span class="detail-value ${valueClass(dog.good_with_dogs)}">${dog.good_with_dogs || '?'}</span></div>
          <div class="detail"><span class="detail-label">Kids</span><span class="detail-value ${valueClass(dog.good_with_kids)}">${dog.good_with_kids || '?'}</span></div>
          <div class="detail"><span class="detail-label">Cats</span><span class="detail-value ${valueClass(dog.good_with_cats)}">${dog.good_with_cats || '?'}</span></div>
          <div class="detail"><span class="detail-label">Shedding</span><span class="detail-value">${dog.shedding || '?'}</span></div>
        </div>
        ${dog.notes ? '<div style="font-size: 0.875rem; color: var(--text-secondary); margin-bottom: 10px;">📝 ' + dog.notes + '</div>' : ''}
        <a href="${url}" target="_blank" class="dog-link">🔗 View on rescue site</a>
        <div class="dog-actions">
          <button class="action-btn" data-action="edit" data-id="${dogId}">✏️ Edit</button>
        </div>
      `;
      
      return card.outerHTML;
    }
    
    // Event delegation for dog card buttons
    document.getElementById('dogGrid').addEventListener('click', function(e) {
      const btn = e.target.closest('button[data-action]');
      if (!btn) return;
      
      const action = btn.dataset.action;
      const dogId = btn.dataset.id;
      
      if (action === 'watch') toggleWatch(dogId);
      else if (action === 'score-up') adjustScore(dogId, 1);
      else if (action === 'score-down') adjustScore(dogId, -1);
      else if (action === 'edit') openEdit(dogId);
    });
    
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
    document.getElementById('configModal').addEventListener('click', function(e) {
      if (e.target === this) closeConfigModal();
    });
    
    // Initialize: Load overrides from GitHub, then render
    (async function init() {
      await loadOverridesFromGitHub();
      renderDogs();
      updateStats();
      
      // Show config hint if no token
      if (!githubToken) {
        setTimeout(() => {
          showToast('⚙️ Set up GitHub sync in settings to save changes', false);
        }, 2000);
      }
    })();
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
