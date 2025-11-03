# Task Manager - HabitCoach AI

A Django-based web application.  
The project enables users to perform **daily check-ins** with mood tracking, notes and tags, while providing an **admin dashboard** for viewing and managing user activity.

---

## Progress (Week 4)

- Repository and virtual environment setup  
- Base Django project initialized (`config/`)  
- `.env` configuration for environment variables  
- `checkins` app created and registered  
- Database schema for user check-ins completed  
- Admin panel integration and working migrations  
- Tests implemented with `pytest`  

---

## Progress (Week 5)

- Extended `CheckIn` model with new fields: `mood`, `note`, `tags` and optional `hrv_rmssd` for HRV-based readiness tracking  
- Created user-facing templates (`dashboard.html`, `list.html`, `form.html`) with accessible structure and navigation  
- Implemented form validation for mood (1–5) and positive HRV values  
- Added `dashboard` view displaying user streak, 7-day trend and a 3-day smoothed mood average  
- Integrated **Tiny Habit suggestions** (Ref-A) and **HRV context tips** (Ref-B) into the dashboard  
- Added **risk-day analytics** summarizing days with low mood or warning/block status (Ref-C)  
- Implemented seed data command (`python manage.py seed_checkins`) for demo/testing with auto-generated check-ins  
- Expanded test coverage for streak calculation, check-in updates and dashboard analytics rendering  

---

## Current Progress (Week 6)

- Added **anchor-based prompts** and **celebration micro-UX** aligned with *Tiny Habits* principles (Ref-A)  
- Extended `Habit` model with new fields: `anchor_text`, `prompt_type`, `celebration_note` and randomized `prompt_variant` for A/B testing  
- Created **Anchor Builder** partial (`_anchor_builder.html`) with live preview using the “After I … I will …” recipe pattern  
- Updated `HabitForm` and `habit_create` view to automatically assign prompt variants and encourage ability-first design  
- Introduced `BiometricsDaily` model for HRV-based readiness tracking (`rmssd`, `sdnn`, `resting_hr`)  
- Implemented `import_hrv` management command for CSV data ingestion and idempotent updates  
- Expanded `seed_checkins` command with demo anchor habits, prompt variants, check-ins and HRV trends  
- Built `services/prompts.py` for scheduling logic and random variant assignment  
- Added lightweight analytics utilities (`analytics/utils.py`) providing `permutation_test()` and `quick_vif()` for behavioral analysis  
- Developed unit tests (`test_week6.py`) verifying new models, services and importer functionality  
- Verified migrations, fixtures and dashboard compatibility with prior Week 5 implementation  

---

**References**

- (Ref-A) Fogg, B.J. – *Tiny Habits* (Behavior Design, Stanford)  
- (Ref-B) Storniolo et al., 2025 – *Frontiers in Sports & Active Living*, HRV in exercise and recovery  
- (Ref-C) James et al., 2021 – *An Introduction to Statistical Learning (2e)*, data smoothing and interpretability  