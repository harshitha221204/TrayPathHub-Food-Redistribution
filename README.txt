Feedgood - Flask project
------------------------

How to run:
1. Extract the feedgood project folder.
2. Open terminal / PowerShell in the project folder.
3. (Optional) Create virtual environment:
   python -m venv venv
   .\venv\Scripts\Activate.ps1   # PowerShell
4. Install dependencies:
   pip install flask werkzeug
5. Run the app:
   python app.py
6. Open browser at http://127.0.0.1:5000

Default admin credentials:
  email: admin@feedgood.local
  password: admin123

Notes:
- The SQLite database (feedgood.db) is auto-created on first run.
- Place any background images in static/images/ if you want to change them.
