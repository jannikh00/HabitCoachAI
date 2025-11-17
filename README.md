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

## Progress (Week 6)

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

## Progress (Week 7)

- Added new HRVReading model implementing rmssd_ms, sdnn_ms, and resting_hr based on physiological readiness metrics from Frontiers in Sports & Active Living (Ref-B)
- Introduced HabitAnchor model aligned with B.J. Fogg’s Tiny Habits framework, enabling creation of “After I … I will …” prompt–behavior–celebration recipes (Ref-A)
- Created user-facing templates (hrv_form.html, hrv_list.html, habit_anchor_form.html, habit_anchor_list.html) for HRV submission and habit anchor management
- Implemented HRVReadingForm and HabitAnchorForm with structured placeholders and validation supporting ability-first habit design
- Added authenticated views for HRV creation/listing and Habit Anchor creation/listing with full URL routing through the checkins namespace
- Developed ISL-inspired prediction service (services/scoring.py) using a logistic-style estimator combining recent CheckIn trends with latest HRV data (Ref-C)
- Updated dashboard view to display a “Today’s adherence forecast” probability derived from behavioral streaks and physiological readiness signals
- Implemented custom UserLoginView and UserLogoutView with dedicated routing (users/urls.py) and integrated them into the project navigation
- Refactored navigation bar with authentication-aware links and consistent namespaced URL usage (checkins: / users:)
- Created a new superuser and validated Django admin access for all Week 7 data models (HRVReading, HabitAnchor, CheckIn)

---

## Current Progress (Week 8)

- Unified the dashboard view to merge streak analytics, 7-day trend data, mood smoothing, risk-day detection, HRV readiness and adherence forecasting into one coherent backend pipeline
- Added _classify_readiness() helper using rmssd_ms and resting_hr to generate “High / Moderate / Low readiness” categories based on HRV recovery indicators from Frontiers in Sports & Active Living (Ref-B)
- Integrated Tiny Habits principles directly into dashboard microcopy, guiding users to shrink behaviors and celebrate wins on low-readiness days (Ref-A)
- Updated dashboard.html with a new “Today’s Readiness” section showing readiness label, description and scaled habit-design guidance
- Extended dashboard context with completion_prob, powered by predict_habit_completion_probability() — a logistic-style estimator inspired by An Introduction to Statistical Learning (Ref-C)
- Implemented mood smoothing (_smooth(k=3)) for clearer short-term trends, following ISL’s emphasis on interpretable statistics (Ref-C)
- Improved risk-day analytics by detecting warn/block statuses and low-mood days (≤2), exposing both risk_count and risk_days for template rendering
- Added comprehensive Week 8 tests (test_week8_dashboard.py) validating streak output, trend population, readiness structure, HRV integration and forecast percentage bounds
- Enforced authentication on the dashboard using @login_required to prevent anonymous-user errors in streak/HRV queries
- Completed integration of the new navigation and styling across templates
- Resolved logout routing and template discovery issues (users/logout.html) and fixed static file loading to ensure consistent UI across all screens

---

**References**

- (Ref-A) Fogg, B.J. – *Tiny Habits* (Behavior Design, Stanford)  
- (Ref-B) Storniolo et al., 2025 – *Frontiers in Sports & Active Living*, HRV in exercise and recovery  
- (Ref-C) James et al., 2021 – *An Introduction to Statistical Learning (2e)*, data smoothing and interpretability  