# Changelog

### Added
- **Instructor Management:** Added a new `professors.html` admin panel with full CRUD capabilities (Create, Read, Update, Delete) for managing faculty members.
- **Extended User Profiles:** Added `national_id`, `phone_number`, `address`, and `date_of_birth` fields to the database for Students, Professors, and Admins.
- **Course Scheduling & Deadlines:** Added `selection_deadline`, `start_date`, `end_date`, `exam_day`, `is_active`, and `is_hidden` fields to the Course model and Admin course management UI.
- **Automated Deadline Enforcement:** The `/student/enroll` backend endpoint now checks the current real-world date against the course `selection_deadline` and blocks late enrollments.
- **Forgot Password Flow:** Added a "Forgot Password" modal to `index.html` that sends a reset request to the Admin portal.
- **Database Reset Script:** Added `reset_db.py` to seamlessly drop old schemas, rebuild updated tables, and inject a securely hashed default Admin account.

### Changed
- **Signup Flow Restructured:** `signup.html` no longer asks students to set a password. Upon Admin approval, the student's `national_id` is automatically securely hashed and set as their temporary password.
- **Admin Password Reset:** Approving a password reset request now automatically changes the user's password to their `national_id`.
- **Profile UI Overhaul:** Updated the Profile pages for both Admins and Professors to fetch and display the newly added personal information fields dynamically.
- **Admin Navigation:** Unified the sidebar navigation across all admin panels to include the new "Instructors" dashboard.
- **Course Edit Modal:** The Admin `courses.html` modal now supports toggling course visibility (hidden) and enrollment status (active).

### Fixed
- **Authentication Hashing Bug:** Fixed an issue where legacy plain-text passwords caused the login and change-password endpoints to crash. Implemented a fallback mechanism to verify and upgrade unhashed passwords to secure `bcrypt` hashes upon next login.
- **Schema Drift Issues:** Resolved `sqlite3.OperationalError` crashes caused by missing columns (e.g., `national_id`, `selection_deadline`) by migrating to a cleanly built database schema.
