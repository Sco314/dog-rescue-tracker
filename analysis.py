"""
Analytics module for dog rescue tracker
v1.0.0

Provides:
- Time-to-adoption predictions
- Status progression analysis
- Fit score correlations
- Application success predictions
"""
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from database import get_connection, DB_FILE


def get_adoption_stats() -> Dict:
  """
  Calculate adoption statistics
  
  Returns dict with:
    - avg_days_to_pending: Average days from Available to Pending
    - avg_days_to_adopted: Average days from first seen to Adopted
    - by_rescue: Stats broken down by rescue
    - by_fit_score: Stats broken down by fit score ranges
  """
  conn = get_connection()
  cursor = conn.cursor()
  
  # Overall time to pending
  cursor.execute("""
    SELECT AVG(days_in_previous_status) as avg_days
    FROM status_history
    WHERE status = 'Pending' AND days_in_previous_status IS NOT NULL
  """)
  row = cursor.fetchone()
  avg_to_pending = row['avg_days'] if row else None
  
  # By rescue
  cursor.execute("""
    SELECT d.rescue_name, AVG(sh.days_in_previous_status) as avg_days
    FROM status_history sh
    JOIN dogs d ON sh.dog_id = d.dog_id
    WHERE sh.status = 'Pending' AND sh.days_in_previous_status IS NOT NULL
    GROUP BY d.rescue_name
  """)
  by_rescue = {row['rescue_name']: row['avg_days'] for row in cursor.fetchall()}
  
  # By fit score range
  cursor.execute("""
    SELECT 
      CASE 
        WHEN d.fit_score >= 7 THEN 'High (7+)'
        WHEN d.fit_score >= 5 THEN 'Medium (5-6)'
        ELSE 'Low (<5)'
      END as score_range,
      AVG(sh.days_in_previous_status) as avg_days,
      COUNT(*) as count
    FROM status_history sh
    JOIN dogs d ON sh.dog_id = d.dog_id
    WHERE sh.status = 'Pending' AND sh.days_in_previous_status IS NOT NULL
    GROUP BY score_range
  """)
  by_fit_score = {row['score_range']: {
    'avg_days': row['avg_days'],
    'count': row['count']
  } for row in cursor.fetchall()}
  
  conn.close()
  
  return {
    'avg_days_to_pending': avg_to_pending,
    'by_rescue': by_rescue,
    'by_fit_score': by_fit_score
  }


def predict_time_to_adoption(dog_id: str) -> Optional[Dict]:
  """
  Predict how long until a dog gets adopted
  Based on similar dogs' historical data
  
  Returns dict with:
    - predicted_days: Estimated days until adoption
    - confidence: low/medium/high
    - similar_dogs: Number of similar dogs used for prediction
  """
  conn = get_connection()
  cursor = conn.cursor()
  
  # Get dog info
  cursor.execute("SELECT * FROM dogs WHERE dog_id = ?", (dog_id,))
  dog = cursor.fetchone()
  if not dog:
    conn.close()
    return None
  
  dog = dict(dog)
  
  # Find similar dogs (same rescue, similar fit score)
  cursor.execute("""
    SELECT sh.days_in_previous_status
    FROM status_history sh
    JOIN dogs d ON sh.dog_id = d.dog_id
    WHERE sh.status IN ('Pending', 'Adopted/Removed')
      AND sh.days_in_previous_status IS NOT NULL
      AND d.rescue_name = ?
      AND d.fit_score BETWEEN ? AND ?
  """, (dog['rescue_name'], (dog['fit_score'] or 0) - 2, (dog['fit_score'] or 0) + 2))
  
  similar = [row['days_in_previous_status'] for row in cursor.fetchall()]
  conn.close()
  
  if not similar:
    return {
      'predicted_days': None,
      'confidence': 'low',
      'similar_dogs': 0,
      'message': 'Not enough historical data'
    }
  
  avg_days = sum(similar) / len(similar)
  
  # Confidence based on sample size
  if len(similar) >= 10:
    confidence = 'high'
  elif len(similar) >= 5:
    confidence = 'medium'
  else:
    confidence = 'low'
  
  return {
    'predicted_days': round(avg_days, 1),
    'confidence': confidence,
    'similar_dogs': len(similar),
    'message': f'Based on {len(similar)} similar dogs'
  }


def get_status_progression_analysis() -> Dict:
  """
  Analyze how dogs progress through statuses
  
  Returns dict with flow analysis:
    - Upcoming -> Available: X days average
    - Available -> Pending: X days average
    - Pending -> Adopted: X days average
  """
  conn = get_connection()
  cursor = conn.cursor()
  
  progressions = {}
  
  # Get transitions
  cursor.execute("""
    SELECT 
      LAG(status) OVER (PARTITION BY dog_id ORDER BY timestamp) as from_status,
      status as to_status,
      days_in_previous_status
    FROM status_history
    WHERE days_in_previous_status IS NOT NULL
  """)
  
  transitions = {}
  for row in cursor.fetchall():
    if row['from_status']:
      key = f"{row['from_status']} -> {row['to_status']}"
      if key not in transitions:
        transitions[key] = []
      transitions[key].append(row['days_in_previous_status'])
  
  conn.close()
  
  # Calculate averages
  for transition, days_list in transitions.items():
    progressions[transition] = {
      'avg_days': round(sum(days_list) / len(days_list), 1),
      'min_days': min(days_list),
      'max_days': max(days_list),
      'count': len(days_list)
    }
  
  return progressions


def get_rescue_performance() -> Dict:
  """
  Compare rescue organizations by various metrics
  """
  conn = get_connection()
  cursor = conn.cursor()
  
  performance = {}
  
  cursor.execute("""
    SELECT 
      rescue_name,
      COUNT(*) as total_dogs,
      AVG(fit_score) as avg_fit_score,
      SUM(CASE WHEN status = 'Available' THEN 1 ELSE 0 END) as available,
      SUM(CASE WHEN status = 'Pending' THEN 1 ELSE 0 END) as pending,
      SUM(CASE WHEN status = 'Upcoming' THEN 1 ELSE 0 END) as upcoming,
      SUM(CASE WHEN is_active = 0 THEN 1 ELSE 0 END) as adopted
    FROM dogs
    GROUP BY rescue_name
  """)
  
  for row in cursor.fetchall():
    performance[row['rescue_name']] = {
      'total_dogs': row['total_dogs'],
      'avg_fit_score': round(row['avg_fit_score'] or 0, 1),
      'available': row['available'],
      'pending': row['pending'],
      'upcoming': row['upcoming'],
      'adopted': row['adopted']
    }
  
  conn.close()
  return performance


def get_application_insights(your_fit_preferences: Dict = None) -> Dict:
  """
  Insights to help with adoption application strategy
  
  Args:
    your_fit_preferences: Dict of your preferences to match against
    
  Returns:
    Recommendations for application timing and approach
  """
  insights = {
    'best_time_to_apply': None,
    'competition_level': None,
    'recommendations': []
  }
  
  stats = get_adoption_stats()
  progressions = get_status_progression_analysis()
  
  # Analyze competition (how fast dogs go pending)
  avg_to_pending = stats.get('avg_days_to_pending')
  if avg_to_pending:
    if avg_to_pending < 3:
      insights['competition_level'] = 'Very High'
      insights['recommendations'].append(
        "⚡ Dogs go pending quickly! Set up notifications and apply immediately when a good match appears."
      )
    elif avg_to_pending < 7:
      insights['competition_level'] = 'High'
      insights['recommendations'].append(
        "🏃 Good dogs don't last long. Apply within 24-48 hours of a new listing."
      )
    else:
      insights['competition_level'] = 'Moderate'
      insights['recommendations'].append(
        "📝 You have a few days to prepare a thoughtful application."
      )
  
  # Fit score insights
  by_fit = stats.get('by_fit_score', {})
  high_fit = by_fit.get('High (7+)', {})
  if high_fit.get('avg_days'):
    insights['recommendations'].append(
      f"⭐ High-fit dogs (7+) go pending in ~{high_fit['avg_days']:.0f} days on average."
    )
  
  # Rescue-specific insights
  rescue_perf = get_rescue_performance()
  for rescue, perf in rescue_perf.items():
    if perf['available'] > 3:
      insights['recommendations'].append(
        f"📍 {rescue} has {perf['available']} dogs available - good selection right now."
      )
  
  return insights


def print_analytics_report():
  """Print a formatted analytics report"""
  print("\n" + "=" * 60)
  print("📊 DOG RESCUE ANALYTICS REPORT")
  print("=" * 60)
  
  # Adoption stats
  stats = get_adoption_stats()
  print("\n📈 ADOPTION TIMING")
  print("-" * 40)
  if stats['avg_days_to_pending']:
    print(f"  Average days to Pending: {stats['avg_days_to_pending']:.1f}")
  
  print("\n  By Rescue:")
  for rescue, days in stats.get('by_rescue', {}).items():
    print(f"    {rescue}: {days:.1f} days avg")
  
  print("\n  By Fit Score:")
  for score_range, data in stats.get('by_fit_score', {}).items():
    print(f"    {score_range}: {data['avg_days']:.1f} days avg ({data['count']} dogs)")
  
  # Status progression
  print("\n🔄 STATUS PROGRESSION")
  print("-" * 40)
  progressions = get_status_progression_analysis()
  for transition, data in progressions.items():
    print(f"  {transition}:")
    print(f"    Avg: {data['avg_days']} days | Range: {data['min_days']}-{data['max_days']} | n={data['count']}")
  
  # Rescue performance
  print("\n🏆 RESCUE PERFORMANCE")
  print("-" * 40)
  performance = get_rescue_performance()
  for rescue, perf in performance.items():
    print(f"\n  {rescue}:")
    print(f"    Total: {perf['total_dogs']} | Avg Fit: {perf['avg_fit_score']}")
    print(f"    Available: {perf['available']} | Pending: {perf['pending']} | Upcoming: {perf['upcoming']}")
  
  # Application insights
  print("\n💡 APPLICATION INSIGHTS")
  print("-" * 40)
  insights = get_application_insights()
  print(f"  Competition Level: {insights.get('competition_level', 'Unknown')}")
  print("\n  Recommendations:")
  for rec in insights.get('recommendations', []):
    print(f"    {rec}")


if __name__ == "__main__":
  print_analytics_report()
