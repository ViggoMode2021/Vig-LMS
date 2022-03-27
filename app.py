from flask import Flask, request, session, redirect, url_for, render_template, flash
import psycopg2
import psycopg2.extras
import re
from werkzeug.security import generate_password_hash, check_password_hash
import datetime

date_object = datetime.date.today()

app = Flask(__name__)

app.secret_key = '#TOPSECRET' #Secret key for sessions

#Database info below:

DB_HOST = "viglmsdatabase.cg5kocdwgcwg.us-east-1.rds.amazonaws.com"
DB_NAME = "VIG_LMS"
DB_USER = "postgres"
DB_PASS = "#TOPSecret"

@app.route('/')
def home():
    # Check if user is logged in
    if 'loggedin' in session:

        # If user is logged in, they are directed to home page.
        return render_template('home.html', username=session['username'], class_name = session['class_name'])
    # If user is not logged in, they are directed to the login page.
    return redirect(url_for('login'))

@app.route('/login/', methods=['GET', 'POST'])
def login():
    conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor) #Make connection to db via Psycopg2

    cursor.execute('SELECT COUNT (username) FROM users;')
    user_count = cursor.fetchall() #This shows the number of users using the application

    # Check if "username" and "password" POST requests exist (user submitted form)
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form and 'email' in request.form:
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']

        # Check if account exists
        cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
        account = cursor.fetchone()
        # Grab user information from classes table. The classes table contains information that the user submitted. This is student information and grades.
        cursor.execute('SELECT * FROM classes WHERE class_creator = %s', (email,))
        account_2 = cursor.fetchone()
        # Grab class name to be stored in session data
        cursor.execute('SELECT class_name FROM classes WHERE class_creator = %s', (email,))
        class_name_print = cursor.fetchone()

        # If above information is adequate:
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

                cursor.close()
                conn.close()

                # Redirect to home page
                return redirect(url_for('home', class_name_print=class_name_print))
            else:
                # Account doesn't exist or username/password incorrect
                flash('Incorrect username/password')
                cursor.close()
                conn.close()
        else:
            # Account doesn't exist or username/password incorrect
            flash('Incorrect username/password')
            cursor.close()
            conn.close()

    return render_template('login.html', user_count=user_count, date_object=date_object)

@app.route('/register', methods=['GET', 'POST'])
def register():

    conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    # Check if "username", "password" and "email" POST requests exist (user submitted form)
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form and 'email' in request.form:
        # Create variables to reference for below queries
        fullname = request.form['fullname']
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        class_name = request.form['class_name']
        secret_question = request.form['secret_question']

        _hashed_password = generate_password_hash(password)

        # Check if account exists:
        cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
        account = cursor.fetchone()
        # If account exists show error and validation checks
        if account:
            flash('Account already exists!')
            cursor.close()
            conn.close()
        elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            flash('Invalid email address!')
            cursor.close()
            conn.close()
        elif not re.match(r'[A-Za-z0-9]+', username):
            flash('Username must contain only characters and numbers!')
            cursor.close()
            conn.close()
        elif not username or not password or not email:
            flash('Please fill out the form!')
            cursor.close()
            conn.close()
        else:
            # Account doesn't exist and the form data is valid, new account is created in the users table with the below queries:
            cursor.execute("INSERT INTO users (fullname, username, password, email, class, secret_question) VALUES (%s,%s,%s,%s,%s,%s)", (fullname, username, _hashed_password, email, class_name, secret_question))
            conn.commit()
            cursor.execute("INSERT INTO classes (class_name, teacher, class_creator) VALUES (%s,%s, (SELECT email from users WHERE fullname = %s))", (class_name, fullname, fullname))
            conn.commit()
            flash('You have successfully registered!')
            cursor.close()
            conn.close()
    elif request.method == 'POST':
        # Form is empty
        flash('Please fill out the form!')
        cursor.close()
        conn.close()
    # Show registration form with message (if applicable)
    return render_template('register.html')

@app.route('/logout')
def logout():
    # Remove session data, this will log the user out
   session.pop('loggedin', None)
   session.pop('id', None)
   session.pop('username', None)
   # Redirect to login page
   return redirect(url_for('login'))

@app.route('/enroll_page', methods=['GET'])
def enroll_page(): #This function routes the logged in user to the page to enroll students

    conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    if 'loggedin' in session:
        cursor.execute('SELECT * FROM users WHERE id = %s', [session['id']])
        account = cursor.fetchone()
        cursor.close()
        conn.close()
        return render_template('enroll_page.html', account=account, username=session['username'], class_name=session['class_name'])

    return redirect(url_for('login')) #User is redirected to the log in page if there is no session data

@app.route('/enroll_page_submit', methods=['POST'])
def enroll_page_submit():

    conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    # Get information from forms to enroll students
    first_name = request.form.get("first name")
    last_name = request.form.get("last name")
    graduation_year = request.form.get("graduation year")
    grade = request.form.get("grade")

    if not first_name:
        flash('Please enter a first name.')
        cursor.close()
        conn.close()
        return render_template('enroll_page.html')
    elif not last_name:
        cursor.close()
        conn.close()
        flash('Please enter a last name.')
        return render_template('enroll_page.html')
    elif not graduation_year:
        cursor.close()
        conn.close()
        flash('Please enter a graduation year.')
        return render_template('enroll_page.html')
    elif not grade:
        cursor.close()
        conn.close()
        flash('Please enter a student grade (0-100) to enroll.')
        return render_template('enroll_page.html')
    elif graduation_year.isalpha():
        cursor.close()
        conn.close()
        flash('Please enter a graduation year that is a number.')
        return render_template('enroll_page.html')
    elif grade.isalpha():
        cursor.close()
        conn.close()
        flash('Please enter a grade number between 0 - 100.')
        return render_template('enroll_page.html')
    else:

        cursor.execute("INSERT INTO classes (class_name, teacher, student_first_name, student_last_name, student_graduation_year, student_grade, class_creator) VALUES (%s,%s,%s,%s,%s,%s, (SELECT email from users WHERE email = %s))", (session['class_name'], session['username'], first_name, last_name, graduation_year, grade, session['email']))

        conn.commit()

        cursor.close()
        conn.close()
        flash(f'{first_name} {last_name} has been successfully enrolled.')

    return render_template('enroll_page.html')

#period_1_spanish_1 show class roster #READ
@app.route('/query', methods=['GET'])
def query():

    if 'loggedin' in session: # Show user and student information from the db
         conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
         cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
         cursor.execute('SELECT * FROM users WHERE id = %s', [session['id']])
         account = cursor.fetchone()
         cursor.execute("SELECT * FROM classes WHERE class_creator = %s", [session['email']])
         records_2 = cursor.fetchall()

         cursor.close()
         conn.close()

         return render_template('query_page.html', records_2=records_2, account=account, username=session['username'], class_name=session['class_name'])

    return redirect(url_for('login'))

@app.route('/alphabetically', methods=['GET'])
def alphabetically():

    if 'loggedin' in session: # This orders the students alphabetically by first name

        conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        cursor.execute('SELECT * FROM users WHERE id = %s', [session['id']])
        account = cursor.fetchone()

        cursor.execute("SELECT * FROM classes WHERE class_creator = %s ORDER BY student_first_name ASC", [session['email']])
        records_2 = cursor.fetchall()

        cursor.close()
        conn.close()

        return render_template('query_page.html', records_2=records_2, account=account, username=session['username'], class_name=session['class_name'])

    return redirect(url_for('login'))

#period_1_sort_grade_ascending
@app.route('/grade_ASC', methods=['GET'])
def grade_ASC():

    if 'loggedin' in session: # This orders the students by grade (lowest - highest)

        conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        cursor.execute('SELECT * FROM users WHERE id = %s', [session['id']])
        account = cursor.fetchone()

        cursor.execute("SELECT * FROM classes WHERE class_creator = %s ORDER BY student_grade ASC", [session['email']])
        records_2 = cursor.fetchall()

        cursor.close()
        conn.close()

        return render_template('query_page.html', records_2=records_2, account = account, username=session['username'], class_name = session['class_name'])

    return redirect(url_for('login'))

#period_1_sort_grade_descending
@app.route('/grade_DESC', methods=['GET'])
def grade_DESC():

    if 'loggedin' in session: # This orders the students by grade (highest - lowest)

        conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        cursor.execute('SELECT * FROM users WHERE id = %s', [session['id']])
        account = cursor.fetchone()

        cursor.execute("SELECT * FROM classes WHERE class_creator = %s ORDER BY student_grade DESC", [session['email']])
        records_2 = cursor.fetchall()

        cursor.close()
        conn.close()

        return render_template('query_page.html', records_2=records_2, account=account, username=session['username'], class_name=session['class_name'])

    return redirect(url_for('login'))

@app.route('/delete/<string:id>', methods = ['DELETE', 'GET'])
def delete_student(id):

    if 'loggedin' in session: # This removes a student from the class

        conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        cursor.execute('SELECT * FROM users WHERE id = %s', [session['id']])
        account = cursor.fetchone()
        cursor.execute('DELETE FROM classes WHERE id = {0}'.format(id))
        conn.commit()
        cursor.execute("SELECT * FROM classes WHERE class_creator = %s", [session['email']])
        records_2 = cursor.fetchall()

        cursor.close()
        conn.close()

        return redirect(url_for('query', records_2=records_2, account=account))

    return redirect(url_for('login'))

@app.route('/update_grade/<id>', methods = ['PATCH', 'GET', 'POST'])
def update_grade(id):

    if 'loggedin' in session: # This updates the student grade via user input.

        conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        cursor.execute('SELECT * FROM users WHERE id = %s', [session['id']])
        account = cursor.fetchone()

        updated_grade = request.form.get("update grade")

        cur = conn.cursor()

        if not updated_grade:
            flash("Please enter a new grade if you wish to update the student's grade.")
            cursor.close()
            conn.close()
            return redirect(url_for('query'))
        if updated_grade.isalpha():
            flash("Please enter a new grade number if you wish to update the student's grade.")
            cursor.close()
            conn.close()
            return redirect(url_for('query'))
        else:
            cur.execute("""UPDATE classes 
            SET student_grade = %s 
            WHERE id = %s""", (updated_grade, id))

            conn.commit()

            cursor.execute("SELECT * FROM classes WHERE class_creator = %s", [session['email']])
            records_2 = cursor.fetchall()

            cursor.close()
            conn.close()
            return redirect(url_for('query', records_2=records_2, account=account, username=session['username'], class_name=session['class_name']))

    return redirect(url_for('login'))

@app.route('/assignment', methods=['GET', 'POST'])
def assignment():

    if 'loggedin' in session:# This selects the assignments that the user created

        conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        cursor.execute('SELECT * FROM users WHERE id = %s', [session['id']])
        account = cursor.fetchone()

        cursor.execute("SELECT * FROM assignments WHERE assignment_creator = %s", [session['email']])
        assignments = cursor.fetchall()

        cursor.close()
        conn.close()

        return render_template('assignment.html', account=account, assignments =assignments, username=session['username'], class_name=session['class_name'])

    return redirect(url_for('login'))

@app.route('/new_assignment', methods=['POST'])
def new_assignment():

    if 'loggedin' in session: # This creates a new assignment
        conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        cursor.execute('SELECT * FROM users WHERE id = %s', [session['id']])
        account = cursor.fetchone()

        assignment_name = request.form.get("assignment name")
        category = request.form.get("category")
        due_date = request.form.get("due date")
        overall_points = request.form.get("max points")

        if not assignment_name:
            flash('Please enter an assignment name.')
            cursor.close()
            conn.close()
        elif not category:
            flash('Please enter a category.')
            cursor.close()
            conn.close()
            return render_template('assignment.html')
        if not due_date:
            flash('Please enter an due date.')
            cursor.close()
            conn.close()
            return render_template('assignment.html')
        if not overall_points:
            flash('Please enter an overall point amount.')
            cursor.close()
            conn.close()
            return render_template('assignment.html')
        else:
            cursor.execute("INSERT INTO assignments (assignment_name, category, due_date, overall_points, assignment_creator) VALUES (%s, %s, %s, %s, (SELECT email from users WHERE email = %s))", (assignment_name, category, due_date, overall_points, session['email']))
            conn.commit()

            cursor.close()
            conn.close()

        return render_template('assignment.html', account = account, username=session['username'], class_name = session['class_name'])

    return redirect(url_for('login'))

@app.route('/edit_assignment_grade/<string:id>', methods=['GET'])
def edit_assignment_grade(id):

    if 'loggedin' in session: # This routes the user to the edit assignment grade page.

        conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        cursor.execute('SELECT * FROM users WHERE id = %s', [session['id']])
        account = cursor.fetchone()

        cur = conn.cursor()

        cur.execute("SELECT assignment_name FROM assignments WHERE id = {0}".format(id))
        records_2 = cur.fetchall()

        cur.execute('SELECT * FROM classes WHERE class_creator = %s', [session['email']])
        records_3 = cur.fetchall()

        cur.execute("SELECT id FROM assignments WHERE id = {0}".format(id))
        records_4 = cur.fetchone()

        cursor.close()
        conn.close()

        return render_template('edit_assignment_grade.html', account=account, records_2=records_2, records_3=records_3, records_4=records_4, username=session['username'], class_name=session['class_name'])

    return redirect(url_for('login'))

@app.route('/edit_assignment_grade_2', methods=['POST', 'GET'])
def edit_assignment_grade_2():

    if 'loggedin' in session:

        conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        cursor.execute('SELECT * FROM users WHERE id = %s', [session['id']])
        account = cursor.fetchone()

        grade_assignment = request.form.get("grade_assignment")
        input_id = request.form.get("input_id")
        student_id = request.form.get("student_id")

        cur = conn.cursor()

        conn.commit()

        if not grade_assignment:
            flash('Please input the updated grade here.')
            cursor.close()
            conn.close()
            return redirect(url_for('assignment'))
        elif not input_id:
            flash('Please confirm the assignment ID here (located at the top left corner of page).')
            cursor.close()
            conn.close()
            return redirect(url_for('assignment'))
        elif not student_id:
            flash('Please confirm the student ID here (located in this row on the left).')
            cursor.close()
            conn.close()
            return redirect(url_for('assignment'))
        elif grade_assignment.isalpha():
            flash('Please enter an assignment grade (0-100).')
            cursor.close()
            conn.close()
            return redirect(url_for('assignment'))
        elif input_id.isalpha():
            flash('Please enter a graduation year that is a number.')
            cursor.close()
            conn.close()
            return redirect(url_for('assignment'))
        elif student_id.isalpha():
            flash('Please enter a grade number between 0 - 100.')
            cursor.close()
            conn.close()
            return redirect(url_for('assignment'))
        else:
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

            cursor.close()
            conn.close()

            return render_template('assignment.html', account=account, grade_assignment=grade_assignment, student_id=student_id, username=session['username'], class_name = session['class_name'])

    return redirect(url_for('login'))

@app.route('/view_assignment_scores', methods=['GET'])
def view_assignment_scores():

    if 'loggedin' in session:

        conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

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

        cursor.close()
        conn.close()

        return render_template('view_assignment_scores.html', account=account, assignment_scores=assignment_scores, username=session['username'], class_name = session['class_name'])

    return redirect(url_for('login'))

@app.route('/view_assignment_scores_by_student', methods=['POST', 'GET'])
def view_assignment_scores_by_student():

    if 'loggedin' in session:
        conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        cursor.execute('SELECT * FROM users WHERE id = %s', [session['id']])
        account = cursor.fetchone()

        session['student_name'] = request.form['student_name']

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
        WHERE class_creator = %s AND s.student_last_name = %s
        ORDER BY cu.assignment_name ASC;""", [session['email'], session['student_name']])

        assignment_scores_by_student = cursor.fetchall()

        cursor.close()
        conn.close()

        if not assignment_scores_by_student:
            flash('Student not enrolled in class.')
            cursor.close()
            conn.close()

            return redirect(url_for('assignment'))

        return render_template('view_assignment_scores_by_student.html', account=account, assignment_scores_by_student=assignment_scores_by_student, username=session['username'], class_name=session['class_name'], student_name=session['student_name'])

    return redirect(url_for('login'))

@app.route('/delete_assignment/<string:id>', methods = ['DELETE', 'GET'])
def delete_assignment(id):

    if 'loggedin' in session:

        conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        cursor.execute('SELECT * FROM users WHERE id = %s', [session['id']])
        account = cursor.fetchone()

        cursor.execute('DELETE FROM assignments WHERE id = {0}'.format(id))

        conn.commit()

        cursor.execute("SELECT * FROM assignments WHERE assignment_creator = %s", [session['email']])

        assignments = cursor.fetchall()

        cursor.close()
        conn.close()

        return redirect(url_for('assignment', account=account, assignments=assignments))

    return redirect(url_for('login'))

@app.route('/delete_assignment_score/<string:id>', methods = ['DELETE', 'GET'])
def delete_assignment_score(id):

    if 'loggedin' in session:
        conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        cursor.execute('SELECT * FROM users WHERE id = %s', [session['id']])
        account = cursor.fetchone()

        cursor.execute('DELETE FROM assignment_results WHERE id = {0}'.format(id))

        conn.commit()

        cursor.execute("SELECT * FROM assignments WHERE assignment_creator = %s", [session['email']])

        assignments = cursor.fetchall()

        cursor.close()
        conn.close()

        return redirect(url_for('view_assignment_scores', account=account, assignments=assignments, username=session['username'], class_name=session['class_name']))

    return redirect(url_for('login'))

@app.route('/reset_password', methods=['GET', 'POST'])
def reset_password():

    conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    # Check if "username" and "password" POST requests exist (user submitted form)
    if request.method == 'POST' and 'email_2' in request.form and 'secret_question_2' in request.form and 'new_password' in request.form:
        email_2 = request.form['email_2']
        secret_question_2 = request.form['secret_question_2']
        new_password = request.form['new_password']

        # Check if account exists
        cursor.execute('SELECT * FROM users WHERE email = %s AND secret_question = %s', (email_2, secret_question_2))

        account_password_reset = cursor.fetchone()

        _hashed_password_reset = generate_password_hash(new_password)

        if account_password_reset:

            cursor.execute("""UPDATE users 
            SET password = %s 
            WHERE email = %s""", (_hashed_password_reset, email_2))

            conn.commit()

            # Redirect to home page
            flash(f'Password updated for {email_2}')

            cursor.close()
            conn.close()
            return redirect(url_for('reset_password'))
        else:
            # Account doesn't exist or username/password incorrect
            flash('Incorrect credentials')
            cursor.close()
            conn.close()

    return render_template('reset_password.html')

################## STUDENT ACCOUNT PORTION ###################################

@app.route('/student_register', methods=['GET', 'POST'])
def student_register():

    conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    # Check if "username", "password" and "email" POST requests exist (user submitted form)
    if request.method == 'POST' and 'student_firstname' in request.form and 'student_lastname' in request.form and 'student_password' in request.form:
        # Create variables for easy access
        student_firstname = request.form['student_firstname']
        student_lastname = request.form['student_lastname']
        student_password = request.form['student_password']
        student_class_name = request.form['student_class_name']
        student_secret_question = request.form['student_secret_question']

        _hashed_password_student = generate_password_hash(student_password)

        cursor.execute('SELECT * FROM student_accounts WHERE student_first_name = %s AND student_last_name = %s', (student_firstname, student_lastname))
        student_account = cursor.fetchone()

        cursor.execute('SELECT * FROM classes WHERE student_first_name = %s AND student_last_name = %s AND class_name = %s', (student_firstname, student_lastname, student_class_name))
        student_verify = cursor.fetchone()

        if student_account:
            flash('Student account already exists!')
        elif not student_verify:
            flash('Student not enrolled in class!')
        elif not student_firstname or not student_lastname or not student_password:
            flash('Please fill out the form!')
        else:
            # Account doesn't exist and the form data is valid, now insert new account into users table
            cursor.execute("INSERT INTO student_accounts (student_first_name, student_last_name, password, class, secret_question) VALUES (%s,%s,%s,%s,%s)", (student_firstname, student_lastname, _hashed_password_student, student_class_name, student_secret_question))
            conn.commit()
            flash('You have successfully registered!')
            cursor.close()
            conn.close()
    elif request.method == 'POST':
        # Form is empty... (no POST data)
        flash('Please fill out the form!')
        cursor.close()
        conn.close()
    # Show registration form with message (if any)
    return render_template('student_register.html')

@app.route('/student_login/', methods=['GET', 'POST'])
def student_login():
    conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    cursor.execute('SELECT COUNT (student_first_name) FROM student_accounts;')
    student_count = cursor.fetchall()

    # Check if "username" and "password" POST requests exist (user submitted form)
    if request.method == 'POST' and 'student_first_name_2' in request.form and 'student_last_name_2' in request.form and 'student_password_2' in request.form:
        student_first_name_2 = request.form['student_first_name_2']
        student_last_name_2 = request.form['student_last_name_2']
        student_password_2 = request.form['student_password_2']

        cursor.execute('SELECT * FROM student_accounts WHERE student_first_name = %s AND student_last_name = %s', (student_first_name_2, student_last_name_2))
        student_account = cursor.fetchone()
        session['student_class_name'] = student_account['class']
        cursor.execute('SELECT * FROM classes WHERE student_first_name = %s AND student_last_name = %s AND class_name = %s', (student_first_name_2, student_last_name_2, session['student_class_name']))
        student_class_info = cursor.fetchall()

        if student_account:
            password_student = student_account['password']
            # If account exists in users table in out database
            if check_password_hash(password_student, student_password_2):
                # Create session data, we can access this data in other routes
                session['loggedin'] = True
                session['id'] = student_account['id']
                session['student_first_name'] = student_account['student_first_name']
                session['student_last_name'] = student_account['student_last_name']

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
                WHERE s.student_last_name = %s AND s.class_name = %s
                ORDER BY cu.assignment_name ASC;""", [session['student_last_name'], session['student_class_name']])

                student_assignments = cursor.fetchall()

                cursor.close()
                conn.close()

                # Redirect to home page
                return render_template('student_home.html', student_class_info=student_class_info, student_assignments=student_assignments)
            else:
                # Account doesn't exist or username/password incorrect
                flash('Incorrect credentials or account does not exist. Please check your spelling.')
                cursor.close()
                conn.close()
        else:
            # Account doesn't exist or username/password incorrect
            flash('Incorrect credentials or account does not exist. Please check your spelling.')
            cursor.close()
            conn.close()

    return render_template('student_login.html', student_count=student_count, date_object=date_object)

@app.route('/student_home', methods=['GET'])
def student_home():
    conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    if 'loggedin' in session: # Show user and student information from the db
         cursor.execute('SELECT * FROM student_accounts WHERE id = %s', [session['id']])
         student_account_2 = cursor.fetchone()
         cursor.execute("SELECT * FROM classes WHERE student_first_name = %s", [session['student_first_name']])
         student_class_info = cursor.fetchall()
         cursor.close()
         conn.close()

         return render_template('student_home.html', student_class_info = student_class_info, student_account_2 = student_account_2)

    return redirect(url_for('login'))

@app.route('/student_reset_password', methods=['GET', 'POST'])
def student_reset_password():

    conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    # Check if "username" and "password" POST requests exist (user submitted form)
    if request.method == 'POST' and 'student_last_name_2' in request.form and 'student_secret_question_2' in request.form and 'student_new_password' in request.form:
        student_last_name_2 = request.form['student_last_name_2']
        student_secret_question_2 = request.form['student_secret_question_2']
        student_new_password = request.form['student_new_password']

        # Check if account exists
        cursor.execute('SELECT * FROM student_accounts WHERE student_last_name = %s AND secret_question = %s', (student_last_name_2, student_secret_question_2))

        student_account_password_reset = cursor.fetchone()

        _hashed_password_reset_student = generate_password_hash(student_new_password)

        if student_account_password_reset:

            cursor.execute("""UPDATE student_accounts 
            SET password = %s 
            WHERE student_last_name = %s""", (_hashed_password_reset_student, student_last_name_2))

            conn.commit()

            # Redirect to home page
            flash(f'Password updated for {student_last_name_2}')

            cursor.close()
            conn.close()
            return redirect(url_for('student_reset_password'))
        else:
            # Account doesn't exist or username/password incorrect
            flash('Incorrect credentials')
            cursor.close()
            conn.close()

    return render_template('student_reset_password.html')

if __name__ == "__main__":
    app.run(debug=True)
