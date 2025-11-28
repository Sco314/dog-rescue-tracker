"""
Calculate fit score for dogs based on desired characteristics
"""
from models import Dog
from config import SCORING_WEIGHTS, WATCH_LIST_DOGS


def calculate_fit_score(dog: Dog) -> int:
  """
  Calculate fit score based on dog characteristics
  
  Scoring:
  - Weight >= 40 lbs: +2
  - Shedding (None: +2, Low: +1, Unknown: +1 for doodles)
  - Energy (Low/Medium: +2, High: 0, Unknown: +1)
  - Good with dogs: +2 (important for Darwin!)
  - Good with kids: +1
  - Good with cats: +1
  - Doodle/Poodle breed: +1
  - Special needs: -1
  """
  score = 0
  
  # Weight score
  if dog.weight and dog.weight >= SCORING_WEIGHTS["weight_threshold"]:
    score += SCORING_WEIGHTS["weight_points"]
  
  # Shedding score
  shedding_value = dog.shedding.strip() if dog.shedding else "Unknown"
  if shedding_value in SCORING_WEIGHTS["shedding"]:
    score += SCORING_WEIGHTS["shedding"][shedding_value]
  else:
    score += SCORING_WEIGHTS["shedding"].get("Unknown", 0)
  
  # Energy level score
  energy_value = dog.energy_level.strip() if dog.energy_level else "Unknown"
  if energy_value in SCORING_WEIGHTS["energy"]:
    score += SCORING_WEIGHTS["energy"][energy_value]
  else:
    score += SCORING_WEIGHTS["energy"].get("Unknown", 0)
  
  # Good with kids
  if dog.good_with_kids.strip().lower() == "yes":
    score += SCORING_WEIGHTS["good_with_kids"]
  
  # Good with dogs - extra important!
  if dog.good_with_dogs.strip().lower() == "yes":
    score += SCORING_WEIGHTS["good_with_dogs"]
  
  # Good with cats
  if dog.good_with_cats.strip().lower() == "yes":
    score += SCORING_WEIGHTS["good_with_cats"]
  
  # Special needs penalty
  if dog.special_needs.strip().lower() == "yes":
    score += SCORING_WEIGHTS["special_needs_penalty"]
  
  # Doodle/Poodle bonus
  breed_lower = dog.breed.lower() if dog.breed else ""
  if any(b in breed_lower for b in ["doodle", "poodle", "poo"]):
    score += SCORING_WEIGHTS.get("doodle_bonus", 0)
  
  return max(0, score)  # Don't go below 0


def check_watch_list(dog: Dog) -> str:
  """Check if dog is on watch list"""
  if dog.dog_name in WATCH_LIST_DOGS:
    return "Yes"
  return ""


def is_good_fit(dog: Dog, min_score: int = 5) -> bool:
  """
  Determine if dog is a good fit based on score threshold
  Default threshold: 5 (adjustable)
  """
  return dog.fit_score >= min_score if dog.fit_score else False
