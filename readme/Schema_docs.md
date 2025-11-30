# Dog Schema Documentation

## Overview

This document describes the universal dog schema used throughout Scott's Texas Doodle Rescue Tracker. All scrapers, UI components, and storage layers must conform to this schema.

## Design Principles

1. **Data Integrity First**: All fields are nullable to handle incomplete data gracefully
2. **Separation of Concerns**: Global dog data is separate from user-specific data
3. **Preserve Original Data**: Rescue text is stored faithfully in `rescue_meta`
4. **Future-Ready**: Schema supports multi-user, galleries, and admin features

---

## Core Models

### Dog (Global Data)

The `Dog` class represents authoritative data about a dog from rescues.

```python
from schema import Dog

dog = Dog(
    dog_id="doodle_rock_rescue_kru",
    dog_name="Kru",
    rescue_name="Doodle Rock Rescue",
    status="Available",
    weight_lbs=60,
    ...
)
```

#### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `dog_id` | str | Stable internal ID (rescue_name + normalized_name) |
| `dog_name` | str | Display name |

#### Identity Fields

| Field | Type | Description |
|-------|------|-------------|
| `rescue_name` | str | "Doodle Rock Rescue", "Doodle Dandy Rescue", etc. |
| `rescue_dog_url` | str | Direct link to dog's page on rescue site |
| `platform` | str | Website domain |

#### Status Fields

| Field | Type | Values |
|-------|------|--------|
| `status` | str | "Available", "Upcoming", "Pending", "Adopted", "Inactive" |
| `is_active` | bool | False = no longer on website |

#### Core Attributes

| Field | Type | Description |
|-------|------|-------------|
| `weight_lbs` | int | Weight in pounds |
| `age_years` | float | Normalized age in years (e.g., 1.5) |
| `age_display` | str | Display string "2 yrs", "8 mos" |
| `sex` | str | "Male" or "Female" |
| `breed` | str | "Goldendoodle", "Standard Poodle", etc. |
| `location` | str | City/area |

#### Compatibility

| Field | Type | Values |
|-------|------|--------|
| `good_with_dogs` | str | "Yes", "No", "Unknown" |
| `good_with_cats` | str | "Yes", "No", "Unknown" |
| `good_with_kids` | str | "Yes", "No", "Unknown" |

#### Characteristics

| Field | Type | Values |
|-------|------|--------|
| `shedding` | str | "None", "Low", "Moderate", "High" |
| `energy_level` | str | "Low", "Medium", "High" |
| `special_needs` | bool | True if dog has special needs |
| `special_needs_notes` | str | Details about special needs |

#### Images

| Field | Type | Description |
|-------|------|-------------|
| `primary_image_url` | str | Main photo URL |
| `images` | List[DogImage] | All photos with metadata |

#### Timestamps

| Field | Type | Description |
|-------|------|-------------|
| `created_at` | str | First seen in system (ISO format) |
| `updated_at` | str | Last data update |
| `status_changed_at` | str | Last status change |

---

### RescueMeta (Original Text)

Preserves original rescue-specific data exactly as scraped.

```python
from schema import RescueMeta

meta = RescueMeta(
    weight_text="About 50 lbs",
    age_text="2-3 years old",
    bio_html="<p>Kru is a sweet boy...</p>",
    ...
)
```

| Field | Description |
|-------|-------------|
| `weight_text` | Original weight description |
| `age_text` | Original age description |
| `breed_text` | Original breed description |
| `bio_html` | Full bio as HTML |
| `bio_text` | Bio as plain text |
| `good_with_dogs_text` | Original compatibility text |
| `crate_trained` | "Yes", "No", "Unknown" |
| `potty_trained` | "Yes", "No", "Unknown" |
| `adoption_fee_text` | Original fee text |
| `extra` | Dict for anything else |

---

### UserDogState (User-Specific Data)

Stores user's personal data about a dog. **Never stored on the Dog object.**

```python
from schema import UserDogState, UserOverrides

state = UserDogState(
    user_id="default_user",
    dog_id="doodle_rock_rescue_kru",
    overrides=UserOverrides(
        shedding="Low",
        manual_score_adjustment=2
    ),
    favorite=True,
    notes="Check on cat compatibility."
)
```

| Field | Type | Description |
|-------|------|-------------|
| `user_id` | str | User identifier |
| `dog_id` | str | Which dog this state is for |
| `overrides` | UserOverrides | User's corrections to dog data |
| `favorite` | bool | Starred/watched |
| `hidden` | bool | User doesn't want to see this dog |
| `notes` | str | Private notes |
| `computed_fit_score` | int | Score with user's overrides applied |

---

### DogEvent (Timeline)

Records changes and updates for audit trail.

```python
from schema import create_status_change_event

event = create_status_change_event(
    dog_id="doodle_rock_rescue_kru",
    dog_name="Kru",
    rescue_name="Doodle Rock Rescue",
    old_status="Available",
    new_status="Pending"
)
```

#### Event Types

| Type | Description |
|------|-------------|
| `first_seen` | Dog first appeared in system |
| `status_change` | Status changed (Available → Pending) |
| `website_update` | Significant metadata changed |
| `fb_post` | Facebook post about this dog |
| `admin_edit` | Admin made manual correction |
| `image_added` | New image added |

---

## Data Access Layer (DAL)

All data operations go through the DAL. Never access the database directly.

```python
from dal import get_dal

dal = get_dal()

# Get a dog
dog = dal.get_dog("doodle_rock_rescue_kru")

# Get user state
state = dal.get_user_dog_state("default_user", dog.dog_id)

# Compute fit score with overrides
score = dal.compute_fit_score(dog, state.overrides)

# Save changes
dal.save_dog(dog)
dal.save_user_dog_state(state)
```

### Key Methods

| Method | Description |
|--------|-------------|
| `get_dog(dog_id)` | Get single dog by ID |
| `get_all_dogs()` | Get all active dogs |
| `save_dog(dog)` | Insert or update a dog |
| `get_user_dog_state(user_id, dog_id)` | Get user's state for a dog |
| `save_user_dog_state(state)` | Save user's state |
| `compute_fit_score(dog, overrides, config)` | Compute score with overrides |
| `get_dog_events(dog_id)` | Get event timeline for a dog |

---

## Fit Score Computation

Scores are always computed as:
```
score = compute_fit_score(dog, user_overrides, scoring_config)
```

### Scoring Factors

| Factor | Points |
|--------|--------|
| Weight ≥ 40 lbs | +2 |
| Age 1-2 years | +2 |
| Age 2-4 years | +1 |
| Age 6+ years | -4 |
| No shedding | +2 |
| Low shedding | +1 |
| Low/Medium energy | +2 |
| Good with dogs | +2 |
| Good with kids | +1 |
| Good with cats | +1 |
| Doodle/Poodle breed | +1 |
| Special needs | -1 |
| Pending status | -8 |

---

## Migration Notes

### Legacy Compatibility

The schema includes legacy field aliases for backward compatibility:
- `source_url` ↔ `rescue_dog_url`
- `image_url` ↔ `primary_image_url`
- `age_range` ↔ `age_display`
- `weight` ↔ `weight_lbs`

### Converting Legacy Data

```python
# From legacy database row
dog = Dog.from_legacy(row_dict)

# To legacy format
legacy_dict = dog.to_legacy_dict()
```

---

## Future Extensions

The schema is designed to support:

1. **Multi-User**: UserDogState already uses `user_id`
2. **Admin Controls**: Events track `created_by`
3. **Facebook Data**: `fb_post` event type, image source tracking
4. **Galleries**: `images` array with source/priority
5. **Real Database**: DAL abstracts storage implementation
