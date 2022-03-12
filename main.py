#app.py
from flask import Flask, request, session, redirect, url_for, render_template, flash
import psycopg2
import psycopg2.extras
import re
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'ryanv203'

DB_HOST = "localhost"
DB_NAME = "Vig_LMS"
DB_USER = "postgres"
DB_PASS = ""
DB_PORT_ID = 5432

conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)

@app.route('/')
def home():
    # Check if user is loggedin
    if 'loggedin' in session:

        # User is loggedin show them the home page
        return render_template('home.html', username=session['username'], class_name = session['class_name'])
    # User is not loggedin redirect to login page
    return redirect(url_for('login'))

@app.route('/login/', methods=['GET', 'POST'])
def login():
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    # Check if "username" and "password" POST requests exist (user submitted form)
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form and 'email' in request.form:
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']

        print(password)

        # Check if account exists using MySQL
        cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
        # Fetch one record and return result
        account = cursor.fetchone()
        cursor.execute('SELECT * FROM classes WHERE class_creator = %s', (email,))
        account_2 = cursor.fetchone()
        cursor.execute('SELECT class_name FROM classes WHERE class_creator = %s', (email,))
        class_name_print = cursor.fetchone()

        if account and account_2:
            password_rs = account['password']
            print(password_rs)
            # If account exists in users table in out database
            if check_password_hash(password_rs, password):
                # Create session data, we can access this data in other routes
                session['loggedin'] = True
                session['id'] = account['id']
                session['username'] = account['username']
                session['email'] = account_2['class_creator']
                session['class_name'] = account_2['class_name']

                # Redirect to home page
                return redirect(url_for('home', class_name_print = class_name_print))
            else:
                # Account doesnt exist or username/password incorrect
                flash('Incorrect username/password')
        else:
            # Account doesnt exist or username/password incorrect
            flash('Incorrect username/password')

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    # Check if "username", "password" and "email" POST requests exist (user submitted form)
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form and 'email' in request.form:
        # Create variables for easy access
        fullname = request.form['fullname']
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        class_name = request.form['class_name']

        _hashed_password = generate_password_hash(password)

        #Check if account exists using MySQL
        cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
        account = cursor.fetchone()
        print(account)
        # If account exists show error and validation checks
        if account:
            flash('Account already exists!')
        elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            flash('Invalid email address!')
        elif not re.match(r'[A-Za-z0-9]+', username):
            flash('Username must contain only characters and numbers!')
        elif not username or not password or not email:
            flash('Please fill out the form!')
        else:
            # Account doesn't exist and the form data is valid, now insert new account into users table
            cursor.execute("INSERT INTO users (fullname, username, password, email, class) VALUES (%s,%s,%s,%s,%s)", (fullname, username, _hashed_password, email, class_name))
            conn.commit()
            cursor.execute("INSERT INTO classes (class_name, teacher, class_creator) VALUES (%s,%s, (SELECT email from users WHERE fullname = %s))", (class_name, fullname, fullname))
            conn.commit()
            flash('You have successfully registered!')
    elif request.method == 'POST':
        # Form is empty... (no POST data)
        flash('Please fill out the form!')
    # Show registration form with message (if any)
    return render_template('register.html')

@app.route('/logout')
def logout():
    # Remove session data, this will log the user out
   session.pop('loggedin', None)
   session.pop('id', None)
   session.pop('username', None)
   # Redirect to login page
   return redirect(url_for('login'))

@app.route('/profile')
def profile():
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    # Check if user is loggedin
    if 'loggedin' in session:
        cursor.execute('SELECT * FROM users WHERE id = %s', [session['id']])
        account = cursor.fetchone()
        # Show the profile page with account info
        return render_template('profile.html', account=account)
    # User is not loggedin redirect to login page
    return redirect(url_for('login'))

@app.route('/enroll_page', methods=['GET'])
def enroll_page():
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    if 'loggedin' in session:
        cursor.execute('SELECT * FROM users WHERE id = %s', [session['id']])
        account = cursor.fetchone()
        return render_template('enroll_page.html', account = account, username=session['username'], class_name = session['class_name'])

    return redirect(url_for('login'))

@app.route('/enroll_page_submit', methods=['POST'])
def enroll_page_submit():
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    class_name = request.form.get("class_name")
    teacher = request.form.get("teacher")
    first_name = request.form.get("first name")
    last_name = request.form.get("last name")
    graduation_year = request.form.get("graduation year")
    grade = request.form.get("grade")

    cursor.execute("INSERT INTO classes (class_name, teacher, student_first_name, student_last_name, student_graduation_year, student_grade, class_creator) VALUES (%s,%s,%s,%s,%s,%s, (SELECT email from users WHERE email = %s))", (class_name, teacher, first_name, last_name, graduation_year, grade, session['email']))

    conn.commit()

    return render_template('enroll_page.html')

#period_1_spanish_1 show class roster #READ
@app.route('/query', methods=['GET'])
def query():
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    if 'loggedin' in session:
         cursor.execute('SELECT * FROM users WHERE id = %s', [session['id']])
         account = cursor.fetchone()
         cursor.execute("SELECT * FROM classes WHERE class_creator = %s", [session['email']])
         records_2 = cursor.fetchall()

         return render_template('query_page.html', records_2=records_2, account = account, username=session['username'], class_name = session['class_name'])

    return redirect(url_for('login'))

@app.route('/alphabetically', methods=['GET'])
def alphabetically():
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    if 'loggedin' in session:

        cursor.execute('SELECT * FROM users WHERE id = %s', [session['id']])
        account = cursor.fetchone()

        cursor.execute("SELECT * FROM classes WHERE class_creator = %s ORDER BY student_first_name ASC", [session['email']])
        records_2 = cursor.fetchall()

        return render_template('query_page.html', records_2=records_2, account = account, username=session['username'], class_name = session['class_name'])

    return redirect(url_for('login'))

#period_1_sort_grade_ascending
@app.route('/grade_ASC', methods=['GET'])
def grade_ASC():
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    if 'loggedin' in session:

        cursor.execute('SELECT * FROM users WHERE id = %s', [session['id']])
        account = cursor.fetchone()

        cursor.execute("SELECT * FROM classes WHERE class_creator = %s ORDER BY student_grade ASC", [session['email']])
        records_2 = cursor.fetchall()

        return render_template('query_page.html', records_2=records_2, account = account, username=session['username'], class_name = session['class_name'])

    return redirect(url_for('login'))

#period_1_sort_grade_descending
@app.route('/grade_DESC', methods=['GET'])
def grade_DESC():
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    if 'loggedin' in session:

        cursor.execute('SELECT * FROM users WHERE id = %s', [session['id']])
        account = cursor.fetchone()

        cursor.execute("SELECT * FROM classes WHERE class_creator = %s ORDER BY student_grade DESC", [session['email']])
        records_2 = cursor.fetchall()

        return render_template('query_page.html', records_2=records_2, account = account, username=session['username'], class_name = session['class_name'])

    return redirect(url_for('login'))

@app.route('/delete/<string:id>', methods = ['DELETE', 'GET'])
def delete_student(id):
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    if 'loggedin' in session:

        cursor.execute('SELECT * FROM users WHERE id = %s', [session['id']])
        account = cursor.fetchone()
        cursor.execute('DELETE FROM classes WHERE id = {0}'.format(id))
        conn.commit()
        cursor.execute("SELECT * FROM classes WHERE class_creator = %s", [session['email']])
        records_2 = cursor.fetchall()
        return redirect(url_for('query', records_2=records_2, account = account))

    return redirect(url_for('login'))

@app.route('/update_grade/<id>', methods = ['PATCH', 'GET', 'POST'])
def update_grade(id):
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    if 'loggedin' in session:

        cursor.execute('SELECT * FROM users WHERE id = %s', [session['id']])
        account = cursor.fetchone()

        updated_grade = request.form.get("update grade")

        cur = conn.cursor()

        cur.execute("""UPDATE classes 
        SET student_grade = %s 
        WHERE id = %s""", (updated_grade, id))

        conn.commit()

        cursor.execute("SELECT * FROM classes WHERE class_creator = %s", [session['email']])
        records_2 = cursor.fetchall()
        return redirect(url_for('query', records_2=records_2, account = account, username=session['username'], class_name = session['class_name']))

    return redirect(url_for('login'))

@app.route('/assignment', methods=['GET', 'POST'])
def assignment():
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    if 'loggedin' in session:
        cursor.execute('SELECT * FROM users WHERE id = %s', [session['id']])
        account = cursor.fetchone()

        cursor.execute("SELECT * FROM assignments WHERE assignment_creator = %s", [session['email']])
        assignments = cursor.fetchall()
        return render_template('assignment.html', account = account, assignments = assignments, username=session['username'], class_name = session['class_name'])

    return redirect(url_for('login'))

@app.route('/new_assignment', methods=['POST'])
def new_assignment():
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    if 'loggedin' in session:
        cursor.execute('SELECT * FROM users WHERE id = %s', [session['id']])
        account = cursor.fetchone()

        assignment_name = request.form.get("assignment name")
        category = request.form.get("category")
        due_date = request.form.get("due date")
        overall_points = request.form.get("max points")

        cursor.execute("INSERT INTO assignments (assignment_name, category, due_date, overall_points, assignment_creator) VALUES (%s, %s, %s, %s, (SELECT email from users WHERE email = %s))", (assignment_name, category, due_date, overall_points, session['email']))

        conn.commit()

        return render_template('assignment.html', account = account, username=session['username'], class_name = session['class_name'])

    return redirect(url_for('login'))

@app.route('/edit_assignment_grade/<string:id>', methods=['GET'])
def edit_assignment_grade(id):
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    if 'loggedin' in session:
        cursor.execute('SELECT * FROM users WHERE id = %s', [session['id']])
        account = cursor.fetchone()

        cur = conn.cursor()

        cur.execute("SELECT assignment_name FROM assignments WHERE id = {0}".format(id))
        records_2 = cur.fetchall()

        cur.execute('SELECT * FROM classes WHERE class_creator = %s', [session['email']])
        records_3 = cur.fetchall()

        cur.execute("SELECT id FROM assignments WHERE id = {0}".format(id))
        records_4 = cur.fetchone()

        return render_template('edit_assignment_grade.html', account = account, records_2 = records_2, records_3 = records_3, records_4 = records_4, username=session['username'], class_name = session['class_name'])

    return redirect(url_for('login'))

@app.route('/edit_assignment_grade_2', methods=['POST','GET'])
def edit_assignment_grade_2():

    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    if 'loggedin' in session:
        cursor.execute('SELECT * FROM users WHERE id = %s', [session['id']])
        account = cursor.fetchone()

        grade_assignment = request.form.get("grade_assignment")
        input_id = request.form.get("input_id")
        student_id = request.form.get("student_id")

        cur = conn.cursor()

        conn.commit()

        cur.execute("""INSERT INTO assignment_results
        (score, student_id, assignment_id) VALUES (%s, %s, %s) 
        """, (grade_assignment, student_id, input_id))

        conn.commit()

        cur.execute("""UPDATE classes 
                    SET student_grade = (
                    SELECT ROUND(AVG(score))
                    FROM assignment_results)
                    WHERE id = %s""", (student_id,))

        conn.commit()

        return render_template('edit_assignment_grade.html', account = account, grade_assignment = grade_assignment, student_id = student_id, username=session['username'], class_name = session['class_name'])

    return redirect(url_for('login'))

@app.route('/view_assignment_scores', methods=['GET'])
def view_assignment_scores():
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    if 'loggedin' in session:
        cursor.execute('SELECT * FROM users WHERE id = %s', [session['id']])
        account = cursor.fetchone()

        cursor.execute("""SELECT
        ci.id AS score_id,
        s.student_first_name,
        s.student_last_name,
        ci.score,
        cu.assignment_name
        FROM classes s
        INNER JOIN assignment_results AS ci
        ON ci.student_id = s.id
        INNER JOIN assignments cu  
        ON cu.id = ci.assignment_id
        WHERE class_creator = %s
        ORDER BY cu.assignment_name ASC;""", [session['email']])

        assignment_scores = cursor.fetchall()

        return render_template('view_assignment_scores.html', account = account, assignment_scores = assignment_scores, username=session['username'], class_name = session['class_name'])

    return redirect(url_for('login'))

@app.route('/delete_assignment/<string:id>', methods = ['DELETE','GET'])
def delete_assignment(id):
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    if 'loggedin' in session:
        cursor.execute('SELECT * FROM users WHERE id = %s', [session['id']])
        account = cursor.fetchone()

        cursor.execute('DELETE FROM assignments WHERE id = {0}'.format(id))

        conn.commit()

        cursor.execute("SELECT * FROM assignments WHERE assignment_creator = %s", [session['email']])

        assignments = cursor.fetchall()

        return redirect(url_for('assignment', account = account, assignments = assignments))

    return redirect(url_for('login'))

@app.route('/delete_assignment_score/<string:id>', methods = ['DELETE','GET'])
def delete_assignment_score(id):
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    if 'loggedin' in session:
        cursor.execute('SELECT * FROM users WHERE id = %s', [session['id']])
        account = cursor.fetchone()

        cursor.execute('DELETE FROM assignment_results WHERE id = {0}'.format(id))

        conn.commit()

        cursor.execute("SELECT * FROM assignments WHERE assignment_creator = %s", [session['email']])

        assignments = cursor.fetchall()

        return redirect(url_for('view_assignment_scores', account = account, assignments = assignments, username=session['username'], class_name = session['class_name']))

    return redirect(url_for('login'))

if __name__ == "__main__":
    app.run(debug=True)
