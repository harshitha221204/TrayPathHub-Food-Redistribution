from flask import Flask, render_template, request, redirect, url_for, session, g, flash, jsonify
import sqlite3, os
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__, static_folder='static', template_folder='templates')
app.secret_key = "change_me_please"
DATABASE = "feedgood.db"

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        conn = sqlite3.connect(DATABASE)
        conn.row_factory = sqlite3.Row
        g._database = conn
    return g._database

@app.teardown_appcontext
def close_connection(exc):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    db = get_db()
    cur = db.cursor()
    cur.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT UNIQUE,
        password TEXT,
        phone TEXT,
        role TEXT,
        latitude REAL,
        longitude REAL,
        created_at TEXT
    );
    CREATE TABLE IF NOT EXISTS listings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        restaurant_id INTEGER,
        title TEXT,
        description TEXT,
        quantity INTEGER,
        expiry TEXT,
        pickup_address TEXT,
        status TEXT DEFAULT 'available',
        created_at TEXT
    );
    CREATE TABLE IF NOT EXISTS claims (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        listing_id INTEGER,
        ngo_id INTEGER,
        qty INTEGER,
        status TEXT DEFAULT 'claimed',
        claimed_at TEXT
    );
    """)
    db.commit()
    cur.execute("SELECT id FROM users WHERE email = ?", ('admin@feedgood.local',))
    if not cur.fetchone():
        cur.execute("INSERT INTO users (name,email,password,phone,role,created_at) VALUES (?,?,?,?,?,?)",
                    ("Admin","admin@feedgood.local", generate_password_hash("admin123"), "0000000000", "admin", datetime.utcnow().isoformat()))
        db.commit()

with app.app_context():
    init_db()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/login', methods=['GET','POST'])
def login():
    error = None
    if request.method == 'POST':
        role = request.form.get('role')
        email = request.form.get('email')
        password = request.form.get('password')
        db = get_db()
        cur = db.execute("SELECT * FROM users WHERE email = ? AND role = ?", (email, role))
        user = cur.fetchone()
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['user_role'] = user['role']
            session['user_name'] = user['name']
            flash('Logged in successfully','success')
            if user['role'] == 'restaurant':
                return redirect(url_for('restaurant_dashboard'))
            elif user['role'] == 'ngo':
                return redirect(url_for('ngo_dashboard'))
            elif user['role'] == 'admin':
                return redirect(url_for('admin_panel'))
        else:
            error = 'Invalid credentials or role'
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/register')
def register_select():
    return render_template('register_select.html')

@app.route('/register/restaurant', methods=['GET','POST'])
def register_restaurant():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        pwd = generate_password_hash(request.form.get('password'))
        phone = request.form.get('phone')
        lat = request.form.get('latitude') or None
        lon = request.form.get('longitude') or None
        db = get_db()
        try:
            db.execute("INSERT INTO users (name,email,password,phone,role,latitude,longitude,created_at) VALUES (?,?,?,?,?,?,?,?)",
                       (name,email,pwd,phone,'restaurant',lat,lon, datetime.utcnow().isoformat()))
            db.commit()
            flash('Restaurant registered. Please login.','success')
            return redirect(url_for('login'))
        except Exception as e:
            flash('Registration failed: '+str(e),'error')
    return render_template('register_restaurant.html')

@app.route('/register/ngo', methods=['GET','POST'])
def register_ngo():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        pwd = generate_password_hash(request.form.get('password'))
        phone = request.form.get('phone')
        lat = request.form.get('latitude') or None
        lon = request.form.get('longitude') or None
        db = get_db()
        try:
            db.execute("INSERT INTO users (name,email,password,phone,role,latitude,longitude,created_at) VALUES (?,?,?,?,?,?,?,?)",
                       (name,email,pwd,phone,'ngo',lat,lon, datetime.utcnow().isoformat()))
            db.commit()
            flash('NGO registered. Please login.','success')
            return redirect(url_for('login'))
        except Exception as e:
            flash('Registration failed: '+str(e),'error')
    return render_template('register_ngo.html')

@app.route('/restaurant/dashboard', methods=['GET','POST'])
def restaurant_dashboard():
    if 'user_role' not in session or session.get('user_role') != 'restaurant':
        flash('Please login as restaurant','error')
        return redirect(url_for('login'))
    db = get_db()
    uid = session['user_id']
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        quantity = int(request.form.get('quantity') or 0)
        expiry = request.form.get('expiry')
        pickup_address = request.form.get('pickup_address')
        db.execute("INSERT INTO listings (restaurant_id,title,description,quantity,expiry,pickup_address,created_at) VALUES (?,?,?,?,?,?,?)",
                   (uid,title,description,quantity,expiry,pickup_address, datetime.utcnow().isoformat()))
        db.commit()
        flash('Listing published','success')
        return redirect(url_for('restaurant_dashboard'))
    cur = db.execute("SELECT * FROM listings WHERE restaurant_id = ? ORDER BY created_at DESC", (uid,))
    listings = cur.fetchall()
    return render_template('restaurant_dashboard.html', listings=listings)

@app.route('/ngo/dashboard', methods=['GET','POST'])
def ngo_dashboard():
    if 'user_role' not in session or session.get('user_role') != 'ngo':
        flash('Please login as NGO','error')
        return redirect(url_for('login'))
    db = get_db()
    cur = db.execute("""SELECT l.*, u.name as restaurant_name, u.phone as restaurant_phone, u.latitude as lat, u.longitude as lon
                      FROM listings l JOIN users u ON l.restaurant_id = u.id WHERE l.status = 'available' ORDER BY l.created_at DESC""")
    listings = cur.fetchall()
    cur2 = db.execute("""SELECT c.*, l.title as food_title FROM claims c JOIN listings l ON c.listing_id = l.id WHERE c.ngo_id = ?""", (session['user_id'],))
    claims = cur2.fetchall()
    return render_template('ngo_dashboard.html', listings=listings, claims=claims)

@app.route('/claim/<int:listing_id>', methods=['POST'])
def claim(listing_id):
    if 'user_role' not in session or session.get('user_role') != 'ngo':
        flash('Login as NGO to claim','error')
        return redirect(url_for('login'))
    qty = int(request.form.get('qty') or 1)
    db = get_db()
    db.execute("INSERT INTO claims (listing_id, ngo_id, qty, status, claimed_at) VALUES (?,?,?,?,?)",
               (listing_id, session['user_id'], qty, 'claimed', datetime.utcnow().isoformat()))
    db.execute("UPDATE listings SET quantity = quantity - ? WHERE id = ?", (qty, listing_id))
    cur = db.execute("SELECT quantity FROM listings WHERE id = ?", (listing_id,))
    row = cur.fetchone()
    if row and row['quantity'] <= 0:
        db.execute("UPDATE listings SET status = 'finished' WHERE id = ?", (listing_id,))
    db.commit()
    flash('Claim submitted','success')
    return redirect(url_for('ngo_dashboard'))

@app.route('/admin')
def admin_panel():
    if 'user_role' not in session or session.get('user_role') != 'admin':
        flash('Admin access only','error')
        return redirect(url_for('login'))
    db = get_db()
    cur = db.execute("SELECT * FROM listings ORDER BY created_at DESC")
    listings = cur.fetchall()
    return render_template('admin.html', listings=listings)

@app.route('/api/listings')
def api_listings():
    db = get_db()
    cur = db.execute("SELECT l.*, u.name as restaurant_name, u.latitude as lat, u.longitude as lon, u.phone as phone FROM listings l JOIN users u ON l.restaurant_id = u.id WHERE l.status = 'available'")
    rows = [dict(r) for r in cur.fetchall()]
    return jsonify(rows)

if __name__ == '__main__':
    app.run(debug=True)
