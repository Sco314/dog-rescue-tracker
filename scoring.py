"""
Calculate fit score for dogs based on desired characteristics
v2.0 - Added age scoring
"""
import re
from models import Dog
from config import SCORING_WEIGHTS, WATCH_LIST_DOGS
from typing import Tuple, Optional


def parse_age_to_years(age_str: str) -> Tuple[Optional[float], Optional[float], bool]:
  """
  Parse age string into numeric years.
  
  Returns: (age_years_min, age_years_max, is_range)
  
  Handles formats:
  - "2 yrs", "2.5 yrs", "3.5 years"
  - "8 mos", "10 months"
  - "12 wks", "8 weeks"
  - "1-3 yrs", "1–3 yrs" (ranges with hyphen or en-dash)
  - "Young (1-3 yrs)", "Adult (3-8 yrs)" (labeled ranges)
  """
  if not age_str:
    return None, None, False
  
  age_str = age_str.lower().strip()
  
  # Normalize dashes (en-dash, em-dash to hyphen)
  age_str = age_str.replace("–", "-").replace("—", "-")
  
  # Try to find range pattern first: "X-Y yrs" or "X - Y years"
  range_match = re.search(r"(\d+\.?\d*)\s*-\s*(\d+\.?\d*)\s*(yr|year|mo|month|wk|week)", age_str)
  if range_match:
    num1 = float(range_match.group(1))
    num2 = float(range_match.group(2))
    unit = range_match.group(3)
    
    # Convert to years
    if "mo" in unit:
      num1 = num1 / 12
      num2 = num2 / 12
    elif "wk" in unit or "week" in unit:
      num1 = num1 / 52
      num2 = num2 / 52
    
    return min(num1, num2), max(num1, num2), True
  
  # Try single value: "2 yrs", "8 mos", "12 wks"
  single_match = re.search(r"(\d+\.?\d*)\s*(yr|year|mo|month|wk|week)", age_str)
  if single_match:
    num = float(single_match.group(1))
    unit = single_match.group(2)
    
    # Convert to years
    if "mo" in unit:
      num = num / 12
    elif "wk" in unit or "week" in unit:
      num = num / 52
    
    return num, num, False
  
  # Try labeled categories without numbers
  if "puppy" in age_str:
    return 0.0, 1.0, True
  elif "young" in age_str:
    return 1.0, 3.0, True
  elif "adult" in age_str:
    return 3.0, 8.0, True
  elif "senior" in age_str:
    return 8.0, 15.0, True
  
  return None, None, False


def calculate_age_score(age_years: float) -> int:
  """
  Calculate age score for a single age value.
  
  Scoring bands:
  - < 0.75 yrs (< 9 months): 0 (too young)
  - 0.75-1.0 yrs: +1
  - 1.0-2.0 yrs: +2 (sweet spot)
  - 2.0-3.0 yrs: +1
  - 3.0-4.0 yrs: 0
  - 4.0-5.0 yrs: -1
  - 5.0-6.0 yrs: -2
  - > 6 yrs: -4
  """
  if age_years < 0.75:
    return 0
  elif age_years < 1.0:
    return 1
  elif age_years < 2.0:
    return 2
  elif age_years < 3.0:
    return 1
  elif age_years < 4.0:
    return 0
  elif age_years < 5.0:
    return -1
  elif age_years < 6.0:
    return -2
  else:
    return -4


def get_age_score(age_min: Optional[float], age_max: Optional[float], is_range: bool) -> int:
  """
  Get final age score, taking the best score if it's a range.
  
  If age is unknown, returns 0 (neutral).
  If age is a range, scores both ends and takes the highest.
  """
  if age_min is None:
    return 0  # Unknown age = neutral
  
  if is_range and age_max is not None and age_max != age_min:
    # Score both ends, take the best
    score_min = calculate_age_score(age_min)
    score_max = calculate_age_score(age_max)
    return max(score_min, score_max)
  else:
    return calculate_age_score(age_min)


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
  - Age: -4 to +2 (based on age bands)
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
  if dog.good_with_kids and dog.good_with_kids.strip().lower() == "yes":
    score += SCORING_WEIGHTS["good_with_kids"]
  
  # Good with dogs - extra important!
  if dog.good_with_dogs and dog.good_with_dogs.strip().lower() == "yes":
    score += SCORING_WEIGHTS["good_with_dogs"]
  
  # Good with cats
  if dog.good_with_cats and dog.good_with_cats.strip().lower() == "yes":
    score += SCORING_WEIGHTS["good_with_cats"]
  
  # Special needs penalty
  if dog.special_needs and dog.special_needs.strip().lower() == "yes":
    score += SCORING_WEIGHTS["special_needs_penalty"]
  
  # Doodle/Poodle bonus
  breed_lower = dog.breed.lower() if dog.breed else ""
  if any(b in breed_lower for b in ["doodle", "poodle", "poo"]):
    score += SCORING_WEIGHTS.get("doodle_bonus", 0)
  
  # Age score - parse and calculate if not already done
  if dog.age_years_min is None and dog.age_range:
    dog.age_years_min, dog.age_years_max, dog.age_is_range = parse_age_to_years(dog.age_range)
  
  age_score = get_age_score(dog.age_years_min, dog.age_years_max, dog.age_is_range)
  dog.age_score = age_score
  score += age_score
  
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
