STUDENT PORTAL - WORKING LOCAL VERSION

1. Install Python 3.11+.
2. Open Command Prompt in this folder.
3. Run: pip install -r requirements.txt
4. Run: python app.py
5. Open: http://127.0.0.1:5000

Demo login:
Student ID: STU2026001
Password: 12345

The app creates student_portal.db automatically.
Assignment uploads are saved in the uploads folder.

This is a development/demo system. Before real college deployment, add proper password hashing,
CSRF protection, admin roles, HTTPS, validation, backups, and production database hosting.


ADMIN PANEL
Open: http://127.0.0.1:5000/admin
Username: admin
Password: admin123

Admin can:
- Add students and their login credentials
- Delete students
- Publish notices
- Add results
- Add attendance records
- Add fee records
- Review/approve/reject correction requests
- View student feedback
