from flask import Flask, flash, render_template, request, redirect, url_for, session
import sqlite3

app = Flask(__name__)
app.secret_key = "your_secret_key"

# Initialize the database
def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    # Create users table (Already created)
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    name TEXT,
                    password TEXT)''')

    # Create collector data table (Already created)
    c.execute('''CREATE TABLE IF NOT EXISTS collector_data (
                    day INTEGER,
                    household_id TEXT,
                    food_waste REAL,
                    plastic_waste REAL,
                    paper_waste REAL,
                    food_segregation INTEGER,
                    plastic_segregation INTEGER,
                    paper_segregation INTEGER,
                    streak INTEGER,
                    collector_id TEXT,
                    colony TEXT,  
                    PRIMARY KEY (day, household_id))''')

    # Create customer table (Already created)
    c.execute('''CREATE TABLE IF NOT EXISTS customers (
                    community_name TEXT PRIMARY KEY,
                    name TEXT,
                    phone TEXT,
                    password TEXT)''')

    # Create collectors table to store approved collectors
    c.execute('''CREATE TABLE IF NOT EXISTS collectors (
                    user_id TEXT PRIMARY KEY,
                    FOREIGN KEY (user_id) REFERENCES users (user_id))''')

    conn.commit()
    conn.close()

@app.route('/approve_collector/<user_id>', methods=['POST'])
def approve_collector(user_id):
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))

    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    # Approve the collector by inserting into the 'collectors' table
    c.execute("INSERT INTO collectors (user_id) VALUES (?)", (user_id,))
    conn.commit()
    conn.close()

    # Remove from the pending collectors
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("DELETE FROM pending_collectors WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

    return redirect(url_for('verification'))  # Redirect to the verification page

@app.route('/reject_collector/<user_id>', methods=['POST'])
def reject_collector(user_id):
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))

    print(f"Rejecting collector with user_id: {user_id}")  # Debug print

    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    # Reject the collector by removing from the pending collectors table
    c.execute("DELETE FROM pending_collectors WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

    return redirect(url_for('verification'))  # Redirect back to the verification page

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user_id = request.form['user_id']
        password = request.form['password']

        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE user_id = ? AND password = ?", (user_id, password))
        user = c.fetchone()

        if user:
            # Check if user is approved as a collector
            c.execute("SELECT * FROM collectors WHERE user_id = ?", (user_id,))
            collector = c.fetchone()

            if collector:  # If user is approved as a collector
                session['user_id'] = user[0]
                session['name'] = user[1]
                return redirect(url_for('data_entry'))
            else:
                return "You need to be approved as a collector to access this page."

        else:
            return "Invalid login credentials. Please try again."

    return render_template('login.html')

@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Check if admin credentials are correct
        if username == "admin" and password == "admin123":
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))  # Redirect to admin dashboard
        
        flash("Invalid admin credentials!", "danger")  # Flash an error message
    
    return render_template('admin_login.html')  # Render admin login page

@app.route('/admin_dashboard')
def admin_dashboard():
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))

    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    # Get list of pending collectors
    c.execute("SELECT * FROM users WHERE user_id NOT IN (SELECT user_id FROM collectors)")
    pending_collectors = c.fetchall()

    conn.close()
    return render_template('admin_dashboard.html', pending_collectors=pending_collectors)

@app.route('/verification', methods=['GET', 'POST'])
def verification():
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))

    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    # Get users who are pending approval (those who are not in the 'users' table as collectors)
    c.execute("SELECT u.user_id, u.name FROM users u WHERE u.user_id NOT IN (SELECT c.user_id FROM collectors c)")
    pending_collectors = c.fetchall()
    conn.close()

    return render_template('verification.html', pending_collectors=pending_collectors)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        user_id = request.form['user_id']
        name = request.form['name']
        password = request.form['password']

        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        existing_user = c.fetchone()

        if existing_user:
            conn.close()
            return "User ID already exists. Please choose a different one."

        c.execute("INSERT INTO users (user_id, name, password) VALUES (?, ?, ?)", (user_id, name, password))
        conn.commit()
        conn.close()

        return redirect(url_for('login'))

    return render_template('signup.html')

@app.route('/customer_login', methods=['GET', 'POST'])
def customer_login():
    if request.method == 'POST':
        user_id = request.form['user_id']
        password = request.form['password']

        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("SELECT * FROM customers WHERE user_id = ? AND password = ?", (user_id, password))
        customer = c.fetchone()
        conn.close()

        if customer:
            # Store customer details in session
            session['customer_name'] = customer[3]  # Full Name
            session['household_id'] = customer[1]  # Household ID
            return redirect(url_for('customer_home'))  # Redirect to the home page
        else:
            return "Invalid User ID or Password. Please try again."

    return render_template('customer_login.html')

def generate_household_id():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    
    c.execute("SELECT MAX(SUBSTR(household_id, 2)) FROM customers")
    result = c.fetchone()
    max_id = int(result[0]) if result[0] else 0
    new_household_id = f"h{str(max_id + 1).zfill(3)}"  # Generates h001, h002, etc.

    conn.close()
    return new_household_id

@app.route('/customer_signup', methods=['GET', 'POST'])
def customer_signup():
    if request.method == 'POST':
        community_name = request.form['community_name']
        name = request.form['name']
        user_id = request.form['user_id']  # Include User ID field
        phone = request.form['phone']
        password = request.form['password']

        household_id = generate_household_id()  # Generate unique household ID

        conn = sqlite3.connect('database.db')
        c = conn.cursor()

        # Check if user_id already exists
        c.execute("SELECT * FROM customers WHERE user_id = ?", (user_id,))
        existing_user = c.fetchone()
        if existing_user:
            conn.close()
            return "User ID already exists. Please choose a different one."

        # Insert new customer with generated household_id
        c.execute("INSERT INTO customers (community_name, name, user_id, phone, password, household_id) VALUES (?, ?, ?, ?, ?, ?)",
                  (community_name, name, user_id, phone, password, household_id))
        conn.commit()
        conn.close()

        return redirect(url_for('customer_login'))  # Redirect to login page

    return render_template('customer_signup.html')

@app.route('/customer_home')
def customer_home():
    if 'customer_name' not in session:
        return redirect(url_for('customer_login'))

    return render_template('customer_home.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('welcome'))

@app.route('/history', methods=['GET'])
def history():
    search_date = request.args.get('search_date')
    collector_id = session['user_id']
    
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # If search_date is provided, filter by that date
    if search_date:
        cursor.execute("""
            SELECT cd.entry_date, cd.day, cd.household_id, cd.food_waste, cd.plastic_waste, cd.paper_waste, 
                   cd.food_segregation, cd.plastic_segregation, cd.paper_segregation, 
                   cd.streak, u.name AS collector_name
            FROM collector_data cd
            JOIN users u ON cd.collector_id = u.user_id
            WHERE cd.collector_id = ? AND cd.entry_date = ?
        """, (collector_id, search_date))
    else:
        cursor.execute("""
            SELECT cd.entry_date, cd.day, cd.household_id, cd.food_waste, cd.plastic_waste, cd.paper_waste, 
                   cd.food_segregation, cd.plastic_segregation, cd.paper_segregation, 
                   cd.streak, u.name AS collector_name
            FROM collector_data cd
            JOIN users u ON cd.collector_id = u.user_id
            WHERE cd.collector_id = ?
        """, (collector_id,))
    
    history_data = cursor.fetchall()
    conn.close()

    # Format entry_date in mm/dd/yyyy if it's not None
    for i, row in enumerate(history_data):
        entry_date = row[0]
        if entry_date:
            # Fix the formatting to mm/dd/yyyy
            formatted_date = f"{entry_date[5:7]}/{entry_date[8:10]}/{entry_date[:4]}"  # Converting to mm/dd/yyyy
            history_data[i] = row[:0] + (formatted_date,) + row[1:]
        else:
            history_data[i] = row[:0] + ("N/A",) + row[1:]  # If entry_date is None, show "N/A"

    return render_template('history.html', history_data=history_data)

@app.route('/data_entry', methods=['GET', 'POST'])
def data_entry():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        day = int(request.form['day'])  # Collectors enter 1-7 (Monday-Sunday)
        household_id = request.form['household_id']
        food_waste = float(request.form['food_waste'])
        plastic_waste = float(request.form['plastic_waste'])
        paper_waste = float(request.form['paper_waste'])
        food_segregation = int(request.form['food_segregation'])
        plastic_segregation = int(request.form['plastic_segregation'])
        paper_segregation = int(request.form['paper_segregation'])
        colony = request.form['colony']
        entry_date = request.form['entry_date']  # Date from the form (yyyy-mm-dd format)

        collector_id = session['user_id']

        conn = sqlite3.connect('database.db')
        c = conn.cursor()

        # Fetch last recorded day and streak for this household
        c.execute("SELECT day, streak FROM collector_data WHERE household_id = ? ORDER BY day DESC LIMIT 1", (household_id,))
        result = c.fetchone()
        last_day = result[0] if result else None
        last_streak = result[1] if result else 0

        # Determine new streak
        if last_day is not None:
            if day == 1 and last_day == 7:  # New week starts (Sunday → Monday)
                streak = 1
            elif day == last_day + 1:  # Consecutive day (e.g., Monday -> Tuesday)
                if food_segregation == 0 or plastic_segregation == 0 or paper_segregation == 0:
                    streak = last_streak - 1  # Reduce streak for improper segregation
                else:
                    streak = last_streak + 1  # Increase streak for proper segregation
            else:  # Non-consecutive or incorrect day order → reset streak
                streak = 1
        else:
            streak = 1  # First-time entry

        # Ensure streak reflects negative values correctly
        if food_segregation == 0 or plastic_segregation == 0 or paper_segregation == 0:
            streak = last_streak - 1  # Deduct consistently for continuous improper segregation

        # Insert data into the database
        c.execute('''INSERT INTO collector_data (entry_date, day, household_id, food_waste, plastic_waste, paper_waste,
                                                 food_segregation, plastic_segregation, paper_segregation, streak, collector_id, colony)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  (entry_date, day, household_id, food_waste, plastic_waste, paper_waste, food_segregation, plastic_segregation,
                   paper_segregation, streak, collector_id, colony))
        conn.commit()
        conn.close()

        return redirect(url_for('data_entry'))

    # Fetch data sorted by household_id
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("""
    SELECT * FROM collector_data 
    ORDER BY DATE(entry_date) ASC, 
             day ASC, 
             CAST(SUBSTR(household_id, 2) AS INTEGER) ASC;
    """)

    data = c.fetchall()
    conn.close()

    print("Sorted Data Sent to HTML:", data)  # Debugging step ✅
    
    return render_template('data_entry.html', data=data)  # Make sure the correct data is sent

@app.route('/')
def welcome():
    return render_template('welcome.html')

if __name__ == "__main__":
    init_db()
    app.run(debug=True)




