from flask import Flask, request, session, redirect, url_for, render_template, flash
import psycopg2
import psycopg2.extras
import re
from werkzeug.security import generate_password_hash, check_password_hash
import datetime

date = datetime.date.today()

format_code = '%m-%d-%Y'

date_object = date.strftime(format_code)

now = datetime.datetime.now()

current_time = now.strftime("%I:%M %p")

app = Flask(__name__)

app.secret_key = '#' #Secret key for sessions

#Database info below:

DB_HOST = "#.#.us-east-1.rds.amazonaws.com"
DB_NAME = "VIG_LMS"
DB_USER = "postgres"
DB_PASS = "Carrotcake2021"

@app.route('/')
def home():
    # Check if user is logged in
    if 'loggedin' in session:

        conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        cursor.execute('SELECT COUNT (student_first_name) FROM classes WHERE class_creator = %s;', [session['email']])
        student_count = cursor.fetchone()

        cursor.execute('SELECT COUNT (assignment_name) FROM assignments WHERE assignment_creator = %s;', [session['email']])
        assignment_count = cursor.fetchone()

        cursor.execute('SELECT account_creation_date FROM users WHERE email = %s;', [session['email']])
        account_creation_date = cursor.fetchone()

        cursor.execute('SELECT COUNT (id) FROM logins WHERE user_login = %s;', [session['email']])
        login_count = cursor.fetchone()

        cursor.execute('SELECT * FROM logins WHERE user_login = %s AND id = (SELECT MAX(id) FROM logins);', [session['email']])
        login_info = cursor.fetchall()

        cursor.close()
        conn.close()

        # If user is logged in, they are directed to home page.
        return render_template('home.html', username=session['username'], class_name=session['class_name'], email=session['email'], name=session['name'],
                               student_count=student_count, assignment_count=assignment_count, account_creation_date=account_creation_date, login_count=login_count, login_info=login_info)
    # If user is not logged in, they are directed to the login page.
    return redirect(url_for('login'))

@app.route('/login/', methods=['GET', 'POST'])
def login():
    conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor) #Make connection to db via Psycopg2

    cursor.execute('SELECT COUNT (username) FROM users;')
    user_count = cursor.fetchone() #This shows the number of users using the application

    # Check if "username" and "password" POST requests exist (user submitted form)
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form and 'email' in request.form:
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']

        # Check if account exists
        cursor.execute('SELECT * FROM users WHERE username = %s;', (username,))
        account = cursor.fetchone()
        # Grab user information from classes table. The classes table contains information that the user submitted. This is student information and grades.
        cursor.execute('SELECT * FROM classes WHERE class_creator = %s;', (email,))
        account_2 = cursor.fetchone()

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
                session['name'] = account['fullname']
                session['email'] = account_2['class_creator']
                session['class_name'] = account_2['class_name']

                cursor.execute('SELECT username FROM users WHERE username = %s;', [session['username']])
                username_print = cursor.fetchone()

                cursor.execute("INSERT INTO logins (login_date, login_time, user_login) VALUES (%s, %s, %s);", (date_object, current_time, session['email']))

                conn.commit()

                for user in username_print:
                     flash(f'You have successfully logged in, {user}!')

                cursor.close()
                conn.close()

                # Redirect to home page
                return redirect(url_for('home'))
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

    return render_template('login.html', user_count=user_count, date_object=date_object, current_time=current_time)

@app.route('/delete_account', methods=['DELETE', 'GET', 'POST'])
def delete_account():

    conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    # Check if "username", "password" and "email" POST requests exist (user submitted form)
    if request.method == 'POST' and 'delete_username' in request.form and 'delete_password' in request.form and 'delete_email' in request.form:
        # Create variables to reference for below queries
        delete_username = request.form['delete_username']
        delete_password = request.form['delete_password']
        delete_email = request.form['delete_email']

        _hashed_password_delete = generate_password_hash(delete_password)

        cursor.execute('SELECT COUNT (username) FROM users;')
        user_count = cursor.fetchone()

        # Check if account exists:
        cursor.execute('SELECT * FROM users WHERE username = %s AND email = %s;', (delete_username, delete_email))
        delete_account = cursor.fetchone()
        # If account exists show error and validation checks
        if delete_account:
            delete_password_check = delete_account['password']
            if check_password_hash(delete_password_check, delete_password):
                cursor.execute('DELETE FROM users WHERE username = %s AND email = %s;', (delete_username, delete_email))
                cursor.execute('DELETE FROM logins WHERE user_login = %s;', (delete_email,))
                cursor.execute('DELETE FROM classes WHERE class_creator = %s;', (delete_email,))
                cursor.execute('DELETE FROM announcements WHERE announcement_creator = %s;', (delete_email,))
                cursor.execute('DELETE FROM classes WHERE class_creator = %s;', (delete_email,))
                cursor.execute('DELETE FROM assignments WHERE assignment_creator = %s;', (delete_email,))
                cursor.execute('DELETE FROM student_direct_message WHERE message_sender = %s;', (delete_email,))
                cursor.execute('DELETE FROM student_direct_message_teacher_copy WHERE message_sender = %s;', (delete_email,))
                cursor.execute('DELETE FROM teacher_direct_message WHERE message_recipient = %s;', (delete_email,))
                cursor.execute('DELETE FROM teacher_direct_message_student_copy WHERE message_recipient = %s;', (delete_email,))
                cursor.execute('DELETE FROM student_accounts WHERE teacher_email = %s;', (delete_email,))

                flash('Account successfully deleted.')
                conn.commit()
                cursor.close()
                conn.close()
                return redirect(url_for('login'))
            else:
                flash('Incorrect password.')
                cursor.close()
                conn.close()
        elif not delete_account:
            flash('No account found.')
            cursor.close()
            conn.close()
        else:
            flash('Invalid credentials.')
            cursor.close()
            conn.close()
    elif request.method == 'POST':
        # Form is empty
        flash('Please fill out the form!')
        cursor.close()
        conn.close()
    # Show registration form with message (if applicable)
    return render_template('login.html', user_count=user_count)

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
        cursor.execute('SELECT * FROM users WHERE username = %s;', (username,))
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
        if len(password) < 5:
            flash('Password must be longer than 5 characters.')
            cursor.close()
            conn.close()
        elif len(password) > 10:
            flash('Password must be shorter than 10 characters.')
            cursor.close()
            conn.close()
        elif not any(char.isdigit() for char in password):
            flash('Password should have at least one numeral.')
            cursor.close()
            conn.close()
        elif not any(char.isupper() for char in password):
            flash('Password should have at least one uppercase letter.')
            cursor.close()
            conn.close()
        elif not any(char.islower() for char in password):
            flash('Password should have at least one lowercase letter.')
            cursor.close()
            conn.close()
        elif not username or not password or not email:
            flash('Please fill out the form!')
            cursor.close()
            conn.close()
        else:
            # Account doesn't exist and the form data is valid, new account is created in the users table with the below queries:
            cursor.execute("INSERT INTO users (fullname, username, password, email, class, secret_question, account_creation_date) VALUES (%s,%s,%s,%s,%s,%s,%s);", (fullname, username, _hashed_password, email, class_name, secret_question, date_object))
            conn.commit()
            example = 'example'
            student = 'student'
            cursor.execute("INSERT INTO classes (student_first_name, student_last_name, class_name, teacher, class_creator) VALUES (%s,%s,%s,%s, (SELECT email from users WHERE fullname = %s))", (example, student, class_name, fullname, fullname))
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
   session.pop('name', None)
   session.pop('email', None)
   session.pop('class_name', None)
   session.pop('student_id', None)
   flash('You have been logged out.')
   # Redirect to login page
   return redirect(url_for('login'))

@app.route('/student_logout')
def student_logout():
    # Remove session data, this will log the user out
   session.pop('loggedin', None)
   session.pop('id', None)
   session.pop('student_first_name', None)
   session.pop('student_last_name', None)
   session.pop('class_creator', None)
   session.pop('student_email', None)
   session.pop('student_class_name', None)
   flash('You have been logged out.')
   # Redirect to login page
   return redirect(url_for('student_login'))

@app.route('/enroll_page', methods=['GET'])
def enroll_page(): #This function routes the logged in user to the page to enroll students

    conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    if 'loggedin' in session:
        cursor.execute('SELECT * FROM users WHERE id = %s;', [session['id']])
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
    student_email = request.form.get("student_email")

    cursor.execute('SELECT * FROM classes WHERE student_email = %s;', (student_email,))
    student_email_fetch = cursor.fetchone()

    if not first_name:
        flash('Please enter a first name.')
        cursor.close()
        conn.close()
        return redirect(url_for('enroll_page'))
    elif student_email_fetch:
        flash(f'Student email already exists for {student_email}!')
        cursor.close()
        conn.close()
        return redirect(url_for('enroll_page'))
    elif not last_name:
        cursor.close()
        conn.close()
        flash('Please enter a last name.')
        return redirect(url_for('enroll_page'))
    elif not graduation_year:
        cursor.close()
        conn.close()
        flash('Please enter a graduation year.')
        return redirect(url_for('enroll_page'))
    elif not grade:
        cursor.close()
        conn.close()
        flash('Please enter a student grade (0-100) to enroll.')
        return redirect(url_for('enroll_page'))
    elif graduation_year.isalpha():
        cursor.close()
        conn.close()
        flash('Please enter a graduation year that is a number.')
        return redirect(url_for('enroll_page'))
    elif grade.isalpha():
        cursor.close()
        conn.close()
        flash('Please enter a grade number between 0 - 100.')
        return redirect(url_for('enroll_page'))
    else:

        cursor.execute("INSERT INTO classes (class_name, teacher, student_first_name, student_last_name, student_graduation_year, student_grade, class_creator, student_email, enrollment_date) VALUES (%s,%s,%s,%s,%s,%s, (SELECT email from users WHERE email = %s), %s,%s)", (session['class_name'], session['username'], first_name, last_name, graduation_year, grade, session['email'], student_email, date_object))

        conn.commit()

        cursor.close()
        conn.close()
        flash(f'{first_name} {last_name} has been successfully enrolled.')

        return redirect(request.referrer)

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

@app.route('/edit_individual_student/<string:id>', methods=['GET'])
def edit_individual_student(id):

    if 'loggedin' in session: # Show user and student information from the db
         conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
         cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

         cursor.execute("""SELECT
         *
         FROM classes 
         WHERE id = {0}""".format(id))

         student_id_for_edit = cursor.fetchone()

         session['student_id'] = student_id_for_edit['id']

         cursor.execute("""SELECT
         student_first_name
         FROM classes 
         WHERE id = {0};""".format(id))

         student_first_name = cursor.fetchone()

         cursor.execute("""SELECT
         student_last_name
         FROM classes 
         WHERE id = {0} AND class_creator = %s;""".format(id), (session['email'],))

         student_last_name = cursor.fetchone()

         cursor.execute("""SELECT
         student_graduation_year
         FROM classes 
         WHERE id = {0};""".format(id))

         graduation_year = cursor.fetchone()

         cursor.execute("""SELECT
         enrollment_date
         FROM classes 
         WHERE id = {0};""".format(id))

         enrollment_date = cursor.fetchone()

         cursor.close()
         conn.close()

         return render_template('edit_individual_student.html', enrollment_date=enrollment_date, student_first_name=student_first_name, student_last_name=student_last_name, graduation_year=graduation_year,username=session['username'], class_name=session['class_name'], date_object=date_object)

    return redirect(url_for('login'))

@app.route('/edit_individual_student_first_name', methods=['POST'])
def edit_individual_student_first_name():

    if 'loggedin' in session: # Show user and student information from the db
         conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
         cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

         update_first_name = request.form.get('update_first_name')

         cursor.execute("""SELECT student_first_name FROM classes WHERE id = %s;""",
                        (session['student_id'],))

         student_first_name_original = cursor.fetchone()

         cursor.execute("""UPDATE classes 
            SET student_first_name = %s 
            WHERE id = %s;""", (update_first_name, session['student_id']))

         conn.commit()

         cursor.close()
         conn.close()

         for student in student_first_name_original:
             flash(f'First name updated from {student} to {update_first_name} successfully!')

         return redirect(url_for('query'))

    return redirect(url_for('login'))

@app.route('/edit_individual_student_last_name', methods=['POST'])
def edit_individual_student_last_name():

    if 'loggedin' in session: # Show user and student information from the db
         conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
         cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

         update_last_name = request.form.get('update_last_name')

         cursor.execute("""SELECT student_last_name FROM classes WHERE id = %s;""",
                        (session['student_id'],))

         student_last_name_original = cursor.fetchone()

         cursor.execute("""UPDATE classes 
            SET student_last_name = %s 
            WHERE id = %s;""", (update_last_name, session['student_id']))

         conn.commit()

         for student in student_last_name_original:
             flash(f'Last name updated from {student} to {update_last_name} successfully!')

         cursor.close()
         conn.close()

         return redirect(url_for('query'))

    return redirect(url_for('login'))

@app.route('/edit_individual_student_graduation_year', methods=['POST'])
def edit_individual_student_graduation_year():

    if 'loggedin' in session: # Show user and student information from the db
         conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
         cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

         update_graduation_year = request.form.get('update_graduation_year')

         cursor.execute("""SELECT student_graduation_year FROM classes WHERE id = %s;""",
                        (session['student_id'],))

         student_graduation_year_original = cursor.fetchone()

         cursor.execute("""SELECT student_first_name FROM classes WHERE id = %s;""",
                        (session['student_id'],))

         student_first_name = cursor.fetchone()

         cursor.execute("""SELECT student_last_name FROM classes WHERE id = %s;""",
                        (session['student_id'],))

         student_last_name = cursor.fetchone()

         cursor.execute("""UPDATE classes 
            SET student_graduation_year = %s 
            WHERE id = %s;""", (update_graduation_year, session['student_id']))

         conn.commit()

         for first_name, last_name, graduation_year in zip(student_first_name, student_last_name, student_graduation_year_original):
             flash(f'Graduation year updated from {graduation_year} to {update_graduation_year} successfully for {first_name} {last_name}!')

         conn.commit()

         cursor.close()
         conn.close()

         return redirect(url_for('query'))

    return redirect(url_for('login'))

@app.route('/update_attendance_record_query_individual_student/<string:id>', methods = ['POST', 'GET'])
def update_attendance_record_query_individual_student(id):

    if 'loggedin' in session: # This updates an attendance record from the db.

        conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        attendance = request.form.get('attendance')

        cursor.execute("""UPDATE attendance 
            SET attendance_status = %s 
            WHERE id = %s;""", (attendance, id))

        conn.commit()

        flash('Attendance updated successfully!')

        cursor.close()
        conn.close()

        return redirect(request.referrer)

    return redirect(url_for('login'))

@app.route('/delete_attendance_record_query_individual_student/<string:id>', methods = ['DELETE', 'GET'])
def delete_attendance_record_query_individual_student(id):

    if 'loggedin' in session: # This removes an attendance record from the db.

        conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        cursor.execute('DELETE FROM attendance WHERE id = {0};'.format(id))
        conn.commit()

        flash('Attendance record deleted successfully!')

        cursor.close()
        conn.close()

        return redirect(request.referrer)

    return redirect(url_for('login'))

@app.route('/update_individual_assignment_grade/<string:id>', methods=['POST'])
def update_individual_assignment_grade(id):

    if 'loggedin' in session: # Show user and student information from the db
         conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
         cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

         update_assignment_grade = request.form.get('update_assignment_grade')

         cursor.execute("""UPDATE assignment_results 
            SET score = %s 
            WHERE id = %s;""".format(id), (update_assignment_grade, id))

         cursor.execute("""UPDATE classes 
                        SET student_grade = (
                        SELECT ROUND(AVG(score))
                        FROM assignment_results WHERE student_id = %s)
                        WHERE id = %s;""", (session['student_id'], session['student_id']))

         conn.commit()

         flash('Assignment grade updated successfully.')

         cursor.close()
         conn.close()

         return redirect(request.referrer)

    return redirect(url_for('login'))

@app.route('/query_individual_student/<string:id>', methods=['GET'])
def query_individual_student(id):

    if 'loggedin' in session: # Show user and student information from the db
         conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
         cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

         cursor.execute("""SELECT
         *
         FROM classes 
         WHERE id = {0} AND class_creator = %s;""".format(id), (session['email'],))

         student_id_for_edit = cursor.fetchone()

         session['student_id'] = student_id_for_edit['id']

         cursor.execute('SELECT * FROM users WHERE id = %s', [session['id']])
         account = cursor.fetchone()
         cursor.execute("SELECT * FROM classes WHERE class_creator = %s;", [session['email']])
         records_2 = cursor.fetchall()

         cursor.execute("""SELECT
         ci.id AS score_id,
         s.student_first_name,
         s.student_last_name,
         cu.assignment_name,
         ci.score
         FROM classes s
         INNER JOIN assignment_results AS ci
         ON ci.student_id = s.id
         INNER JOIN assignments cu  
         ON cu.id = ci.assignment_id
         WHERE s.id = {0} 
         ORDER BY cu.assignment_name ASC;""".format(id))

         student_assignment_scores = cursor.fetchall()

         cursor.execute("""SELECT
         student_first_name
         FROM classes 
         WHERE id = {0};""".format(id))

         student_first_name = cursor.fetchone()

         cursor.execute("""SELECT
         student_last_name
         FROM classes 
         WHERE id = {0};""".format(id))

         student_last_name = cursor.fetchone()

         cursor.execute("""SELECT
         a.id,
         s.student_first_name,
         s.student_last_name,
         s.class_creator,
         a.date,
         a.attendance_status
         FROM classes s
         INNER JOIN attendance AS a
         ON a.student_id = s.id
         WHERE s.id = {0};""".format(id))

         search_attendance_query_student_login = cursor.fetchall()

         cursor.execute("SELECT COUNT (attendance_status) FROM attendance WHERE student_id = {0} AND attendance_status = 'Tardy';".format(id))
         student_tardy_count = cursor.fetchone()

         cursor.execute("SELECT COUNT (attendance_status) FROM attendance WHERE student_id = {0} AND attendance_status = 'Absent';".format(id))
         student_absent_count = cursor.fetchone()

         cursor.execute("SELECT COUNT (attendance_status) FROM attendance WHERE student_id = {0} AND attendance_status = 'Present';".format(id))
         student_present_count = cursor.fetchone()

         cursor.execute("""SELECT * FROM classes WHERE id = {0}""".format(id))

         class_fetch = cursor.fetchall()

         cursor.close()
         conn.close()

         return render_template('query_individual_student.html', student_tardy_count=student_tardy_count, student_absent_count=student_absent_count,student_present_count = student_present_count,
                                search_attendance_query_student_login=search_attendance_query_student_login, class_fetch=class_fetch,
                                student_assignment_scores=student_assignment_scores, student_first_name=student_first_name, student_last_name=student_last_name, records_2=records_2,
                                account=account, username=session['username'], class_name=session['class_name'])

    return redirect(url_for('login'))

@app.route('/delete_assignment_score_query_individual_student/<string:id>', methods = ['DELETE', 'GET'])
def delete_assignment_score_query_individual_student(id):

    if 'loggedin' in session:
        conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        cursor.execute('DELETE FROM assignment_results WHERE id = {0}'.format(id))

        conn.commit()

        cursor.execute("""UPDATE classes 
            SET student_grade = (
            SELECT ROUND(AVG(score))
            FROM assignment_results WHERE student_id = %s)
            WHERE id = %s;""", (session['student_id'], session['student_id']))

        conn.commit()

        flash('Assignment score successfully deleted!')

        cursor.close()
        conn.close()

        return redirect(request.referrer)

    return redirect(url_for('login'))

@app.route('/alphabetically', methods=['GET'])
def alphabetically():

    if 'loggedin' in session: # This orders the students alphabetically by first name

        conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        cursor.execute('SELECT * FROM users WHERE id = %s;', [session['id']])
        account = cursor.fetchone()

        cursor.execute("SELECT * FROM classes WHERE class_creator = %s ORDER BY student_first_name ASC;", [session['email']])
        records_2 = cursor.fetchall()

        cursor.close()
        conn.close()

        return render_template('query_page.html', records_2=records_2, account=account, username=session['username'], class_name=session['class_name'])

    return redirect(url_for('login'))

@app.route('/grade_ASC', methods=['GET'])
def grade_ASC():

    if 'loggedin' in session: # This orders the students by grade (lowest - highest)

        conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        cursor.execute('SELECT * FROM users WHERE id = %s;', [session['id']])
        account = cursor.fetchone()

        cursor.execute("SELECT * FROM classes WHERE class_creator = %s ORDER BY student_grade ASC;", [session['email']])
        records_2 = cursor.fetchall()

        cursor.close()
        conn.close()

        return render_template('query_page.html', records_2=records_2, account = account, username=session['username'], class_name = session['class_name'])

    return redirect(url_for('login'))

@app.route('/take_attendance_page', methods=['GET'])
def take_attendance_page():

    if 'loggedin' in session: # Show user and student information from the db
         conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)

         cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

         cursor.execute('SELECT * FROM users WHERE id = %s', [session['id']])
         account = cursor.fetchone()

         cursor.execute("SELECT * FROM classes WHERE class_creator = %s;", [session['email']])

         take_attendance_query = cursor.fetchall()

         cursor.close()
         conn.close()

         return render_template('take_attendance_page.html', take_attendance_query=take_attendance_query, date_object = date_object, account=account, username=session['username'], class_name=session['class_name'])

    return redirect(url_for('login'))

@app.route('/take_attendance/<string:id>', methods=['POST'])
def take_attendance(id):

    if 'loggedin' in session: # Show user and student information from the db
         conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)

         cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

         cursor.execute('SELECT * FROM users WHERE id = %s;', [session['id']])
         account = cursor.fetchone()

         attendance = request.form.get("attendance")

         cursor.execute('INSERT INTO attendance (date, attendance_status, student_id) VALUES (%s, %s, %s);'.format(id),
                        (date_object, attendance, id))

         conn.commit()

         flash('Attendance recorded!')

         cursor.execute("SELECT * FROM classes WHERE class_creator = %s;", [session['email']])

         take_attendance_query = cursor.fetchall()

         cursor.close()
         conn.close()

         return redirect(url_for('take_attendance_page', take_attendance_query=take_attendance_query, date_object = date_object, account=account, username=session['username'], class_name=session['class_name']))

    return redirect(url_for('login'))

@app.route('/view_attendance_for_today', methods=['GET'])
def view_attendance_for_today():

    if 'loggedin' in session: # Show user and student information from the db
         conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)

         cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

         cursor.execute('SELECT * FROM users WHERE id = %s;', [session['id']])
         account = cursor.fetchone()

         cursor.execute("""SELECT
            a.id,
            s.student_first_name,
            s.student_last_name,
            s.class_creator,
            a.date,
            a.attendance_status
            FROM classes s
            INNER JOIN attendance AS a
            ON a.student_id = s.id
            WHERE a.date = %s AND s.class_creator = %s;""", (date_object, session['email']))

         search_attendance_query = cursor.fetchall()

         cursor.close()
         conn.close()

         return render_template('view_attendance_for_today.html', search_attendance_query=search_attendance_query, date_object = date_object, account=account, username=session['username'], class_name=session['class_name'])

    return redirect(url_for('login'))

@app.route('/search_attendance_by_date', methods=['POST', 'GET'])
def search_attendance_by_date():

    if 'loggedin' in session: # Show user and student information from the db
         conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)

         cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

         cursor.execute('SELECT * FROM users WHERE id = %s;', [session['id']])
         account = cursor.fetchone()

         search_attendance_by_date = request.form['search_attendance_by_date']

         cursor.execute("""SELECT
            a.id,
            s.student_first_name,
            s.student_last_name,
            s.class_creator,
            a.date,
            a.attendance_status
            FROM classes s
            INNER JOIN attendance AS a
            ON a.student_id = s.id
            WHERE a.date = %s AND s.class_creator = %s;""", (search_attendance_by_date, session['email']))

         search_attendance_query = cursor.fetchall()

         if not search_attendance_by_date:
             flash('Please enter a date according to the format above to view attendance.')
             cursor.close()
             conn.close()
             return redirect(url_for('take_attendance_page'))

         cursor.close()
         conn.close()

         return render_template('search_attendance_by_date.html', search_attendance_query=search_attendance_query, date_object = date_object, account=account, username=session['username'], class_name=session['class_name'],
                                search_attendance_by_date=search_attendance_by_date)

    return redirect(url_for('login'))

@app.route('/search_attendance_by_student', methods=['POST', 'GET'])
def search_attendance_by_student():

    if 'loggedin' in session: # Show user and student information from the db
         conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)

         cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

         cursor.execute('SELECT * FROM users WHERE id = %s;', [session['id']])
         account = cursor.fetchone()

         search_attendance_by_student= request.form['search_attendance_by_student']

         cursor.execute("""SELECT
            a.id,
            s.student_first_name,
            s.student_last_name,
            s.class_creator,
            a.date,
            a.attendance_status
            FROM classes s
            INNER JOIN attendance AS a
            ON a.student_id = s.id
            WHERE s.id = %s AND class_creator = %s ORDER BY a.date;""", (search_attendance_by_student, session['email']))

         search_attendance_query_student = cursor.fetchall()

         cursor.execute("SELECT COUNT (attendance_status) FROM attendance WHERE student_id = %s AND attendance_status = 'Tardy';", (search_attendance_by_student,))
         student_tardy_count = cursor.fetchone()

         cursor.execute("SELECT COUNT (attendance_status) FROM attendance WHERE student_id = %s AND attendance_status = 'Absent';", (search_attendance_by_student,))
         student_absent_count = cursor.fetchone()

         cursor.execute("SELECT COUNT (attendance_status) FROM attendance WHERE student_id = %s AND attendance_status = 'Present';", (search_attendance_by_student,))
         student_present_count = cursor.fetchone()

         if not search_attendance_by_student:
             flash('Please enter a student id according to the format above to view attendance.')
             cursor.close()
             conn.close()
             return redirect(url_for('take_attendance_page'))

         cursor.close()
         conn.close()

         return render_template('search_attendance_by_student.html', search_attendance_query_student=search_attendance_query_student, date_object=date_object, account=account, username=session['username'], class_name=session['class_name'],
                                search_attendance_by_date=search_attendance_by_date, student_tardy_count=student_tardy_count, student_present_count=student_present_count, student_absent_count=student_absent_count)

    return redirect(url_for('login'))

@app.route('/delete_attendance_record/<string:id>', methods = ['DELETE', 'GET'])
def delete_attendance_record(id):

    if 'loggedin' in session: # This removes an attendance record from the db.

        conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        cursor.execute('DELETE FROM attendance WHERE id = {0};'.format(id))
        conn.commit()

        cursor.close()
        conn.close()

        return redirect(url_for('take_attendance_page'))

    return redirect(url_for('login'))

@app.route('/update_attendance_record/<string:id>', methods = ['POST', 'GET'])
def update_attendance_record(id):

    if 'loggedin' in session: # This updates an attendance record from the db.

        conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        attendance = request.form.get('attendance')

        cursor.execute("""UPDATE attendance 
            SET attendance_status = %s 
            WHERE id = %s;""", (attendance, id))

        conn.commit()

        cursor.close()
        conn.close()

        return redirect(url_for('take_attendance_page'))

    return redirect(url_for('login'))

@app.route('/grade_DESC', methods=['GET'])
def grade_DESC():

    if 'loggedin' in session: # This orders the students by grade (highest - lowest)

        conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        cursor.execute('SELECT * FROM users WHERE id = %s;', [session['id']])
        account = cursor.fetchone()

        cursor.execute("SELECT * FROM classes WHERE class_creator = %s ORDER BY student_grade DESC;", [session['email']])
        records_2 = cursor.fetchall()

        cursor.close()
        conn.close()

        return render_template('query_page.html', records_2=records_2, account=account, username=session['username'], class_name=session['class_name'])

    return redirect(url_for('login'))

@app.route('/delete_student', methods = ['DELETE', 'GET', 'POST'])
def delete_student():

    if 'loggedin' in session: #This removes a student from the class

        conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        cursor.execute('SELECT * FROM users WHERE id = %s;', [session['id']])
        account = cursor.fetchone()
        delete_first_name = request.form.get('delete_first_name')
        delete_last_name = request.form.get('delete_last_name')
        if not delete_first_name:
            flash('Please input student first name to delete.')
            return redirect(url_for('query'))
        elif not delete_last_name:
            flash('Please input student last name to delete.')
            return redirect(url_for('query'))
        elif not delete_first_name and delete_last_name:
            flash('Please input student names to delete.')
            return redirect(url_for('query'))

        cursor.execute('SELECT student_first_name FROM classes WHERE student_first_name = %s AND class_creator = %s;', (delete_first_name, session['email']))
        first_name = cursor.fetchall()

        cursor.execute('SELECT student_last_name FROM classes WHERE student_last_name = %s AND class_creator = %s;', (delete_last_name, session['email']))
        last_name = cursor.fetchall()

        cursor.execute('SELECT * FROM classes WHERE student_first_name = %s AND student_last_name = %s AND class_creator = %s;', (delete_first_name, delete_last_name, session['email']))
        full_name = cursor.fetchone()

        if not full_name:
                flash(f'{delete_first_name} {delete_last_name} is not enrolled in the class!')
                return redirect(url_for('query'))

        for first, last in zip(first_name, last_name):
            flash(f'{first} {last} has been removed from the class!')

        cursor.execute('DELETE FROM classes WHERE student_first_name = %s AND student_last_name = %s AND class_creator = %s;', (delete_first_name, delete_last_name, session['email']))
        conn.commit()

        cursor.execute("SELECT * FROM classes WHERE class_creator = %s;", [session['email']])
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

        cursor.execute('SELECT * FROM users WHERE id = %s;', [session['id']])
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
            WHERE id = %s;""", (updated_grade, id))

            flash("Grade updated successfully!")

            conn.commit()

            cursor.execute("SELECT * FROM classes WHERE class_creator = %s;", [session['email']])
            records_2 = cursor.fetchall()

            cursor.close()
            conn.close()
            return redirect(url_for('query', records_2=records_2, account=account, username=session['username'], class_name=session['class_name']))

    return redirect(url_for('login'))

@app.route('/student_direct_message_page/<string:id>', methods=['GET'])
def student_direct_message_page(id):

    if 'loggedin' in session: # This routes the user to the edit assignment grade page.

        conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        cursor.execute('SELECT * FROM users WHERE id = %s;', [session['id']])
        account = cursor.fetchone()

        cursor.execute('SELECT id FROM classes WHERE id = {0};'.format(id))

        student_direct_message_id = cursor.fetchone()

        cursor.execute('SELECT student_first_name FROM classes WHERE id = {0};'.format(id))

        student_direct_message_first_name = cursor.fetchone()

        cursor.execute('SELECT student_last_name FROM classes WHERE id = {0};'.format(id))

        student_direct_message_last_name = cursor.fetchone()

        cursor.execute("""SELECT
         *
         FROM classes 
         WHERE id = {0} AND class_creator = %s;""".format(id), (session['email'],))

        student_direct_message_info = cursor.fetchone()

        session['student_id'] = student_direct_message_info['id']

        session['student_first_name'] = student_direct_message_info['student_first_name']

        session['student_last_name'] = student_direct_message_info['student_last_name']

        cursor.execute("SELECT * FROM classes WHERE class_creator = %s", [session['email']])

        student_direct_message_class_info = cursor.fetchone()

        cursor.close()
        conn.close()

        return render_template('student_direct_message_page.html', account=account, student_direct_message_last_name = student_direct_message_last_name,student_direct_message_first_name=student_direct_message_first_name,student_direct_message_id = student_direct_message_id, student_direct_message_info=student_direct_message_info, student_direct_message_class_info = student_direct_message_class_info, username=session['username'], class_name=session['class_name']
                               )

    return redirect(url_for('login'))

@app.route('/delete_direct_message_to_student/<string:id>', methods = ['DELETE', 'GET'])
def delete_direct_message_to_student(id):

    if 'loggedin' in session: # This removes an attendance record from the db.

        conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        cursor.execute('DELETE FROM student_direct_message_teacher_copy WHERE id = {0};'.format(id))
        conn.commit()

        cursor.close()
        conn.close()

        flash('Message deleted!')

        return redirect(request.referrer)

    return redirect(url_for('login'))

@app.route('/delete_direct_message_from_student/<string:id>', methods = ['DELETE', 'GET'])
def delete_direct_message_from_student(id):

    if 'loggedin' in session: # This removes an attendance record from the db.

        conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        cursor.execute('DELETE FROM teacher_direct_message WHERE id = {0};'.format(id))
        conn.commit()

        cursor.close()
        conn.close()

        flash('Message deleted!')

        return redirect(request.referrer)

    return redirect(url_for('login'))

@app.route('/view_student_direct_message_page/<string:id>', methods=['GET'])
def view_student_direct_message_page(id):

    if 'loggedin' in session: # This routes the user to the edit assignment grade page.

        conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        cursor.execute('SELECT * FROM users WHERE id = %s;', [session['id']])
        account = cursor.fetchone()

        cursor.execute('SELECT id FROM classes WHERE id = {0};'.format(id))

        student_direct_message_id = cursor.fetchone()

        cursor.execute("""SELECT
         *
         FROM classes 
         WHERE id = {0} AND class_creator = %s;""".format(id), (session['email'],))

        cursor.execute('SELECT student_first_name FROM classes WHERE id = {0} AND class_creator = %s;'.format(id), (session['email'],))
        student_first_name_message = cursor.fetchone()

        cursor.execute('SELECT student_last_name FROM classes WHERE id = {0} AND class_creator = %s;'.format(id), (session['email'],))
        student_last_name_message = cursor.fetchone()

        cursor.execute('SELECT * FROM student_direct_message_teacher_copy WHERE student_id = {0} AND message_sender = %s;'.format(id), (session['email'],))
        view_student_direct_messages = cursor.fetchall()

        cursor.close()
        conn.close()

        return render_template('view_student_direct_message_page.html', student_first_name_message=student_first_name_message,student_last_name_message=student_last_name_message, account=account, student_direct_message_id = student_direct_message_id, view_student_direct_messages = view_student_direct_messages, username=session['username'], class_name=session['class_name']
                               )
    return redirect(url_for('login'))

@app.route('/view_teacher_direct_message_page/<string:id>', methods=['GET'])
def view_teacher_direct_message_page(id):

    if 'loggedin' in session: # This routes the user to the edit assignment grade page.

        conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        cursor.execute('SELECT * FROM users WHERE id = %s;', [session['id']])
        account = cursor.fetchone()

        cursor.execute('SELECT id FROM classes WHERE id = {0};'.format(id))

        student_direct_message_id = cursor.fetchone()

        cursor.execute('SELECT * FROM teacher_direct_message WHERE student_id = {0} AND message_recipient = %s;'.format(id), (session['email'],))
        view_teacher_direct_messages = cursor.fetchall()

        cursor.execute('SELECT student_first_name FROM classes WHERE id = {0} AND class_creator = %s;'.format(id), (session['email'],))
        student_first_name_message = cursor.fetchone()

        cursor.execute('SELECT student_first_name FROM classes WHERE id = {0} AND class_creator = %s;'.format(id), (session['email'],))
        student_last_name_message = cursor.fetchone()

        cursor.close()
        conn.close()

        return render_template('view_teacher_direct_message_page.html', account=account, student_first_name_message=student_first_name_message,student_last_name_message=student_last_name_message, student_direct_message_id = student_direct_message_id, view_teacher_direct_messages=view_teacher_direct_messages, username=session['username'], class_name=session['class_name']
                               )

    return redirect(url_for('login'))

@app.route('/student_direct_message_page_submit', methods=['POST'])
def student_direct_message_page_submit(): #This function routes the logged in user to the page to students

    conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    if 'loggedin' in session:
        message_subject = request.form.get("message_subject")
        student_direct_message_box = request.form.get("student_direct_message_box")

        cursor.execute('SELECT student_first_name FROM classes WHERE id = %s;', (session['student_id'],))

        student_direct_message_first_name = cursor.fetchone()

        cursor.execute('SELECT student_last_name FROM classes WHERE id = %s;', (session['student_id'],))

        student_direct_message_last_name = cursor.fetchone()

        cursor.execute('SELECT student_email FROM classes WHERE id = %s;', (session['student_id'],))

        student_email = cursor.fetchone()[0]

        cursor.execute("INSERT INTO student_direct_message(date, time, class, message_subject, message, student_first_name, student_last_name, student_id, message_sender, student_email) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s);", (date_object, current_time, session['class_name'], message_subject, student_direct_message_box, session['student_first_name'], session['student_last_name'], session['student_id'], session['email'], student_email))
        cursor.execute("INSERT INTO student_direct_message_teacher_copy(date, time, class, message_subject, message, student_first_name, student_last_name, student_id, message_sender,student_email) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s);", (date_object, current_time, session['class_name'], message_subject, student_direct_message_box, session['student_first_name'], session['student_last_name'], session['student_id'], session['email'], student_email))
        conn.commit()
        cursor.close()
        conn.close()

        for first_name, last_name in zip(student_direct_message_first_name, student_direct_message_last_name):
            flash(f'Message sent to {first_name} {last_name} successfully on {date_object} at {current_time}!. '
                  f'Your subject was: "{student_direct_message_box}" and the \n'
                  f' message was "{message_subject}".')

        return redirect(request.referrer)

    return redirect(url_for('login'))

@app.route('/assignment', methods=['GET', 'POST'])
def assignment():

    if 'loggedin' in session:# This selects the assignments that the user created

        conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        cursor.execute('SELECT * FROM users WHERE id = %s;', [session['id']])
        account = cursor.fetchone()

        cursor.execute("SELECT * FROM assignments WHERE assignment_creator = %s ORDER BY due_date DESC;", [session['email']])
        assignments = cursor.fetchall()

        cursor.close()
        conn.close()

        return render_template('assignment.html', account=account, assignments=assignments, username=session['username'], class_name=session['class_name'])

    return redirect(url_for('login'))

@app.route('/new_assignment', methods=['POST'])
def new_assignment():

    if 'loggedin' in session: # This creates a new assignment
        conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

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

            cursor.execute('SELECT * FROM users WHERE id = %s;', [session['id']])
            account = cursor.fetchone()

            cursor.execute("SELECT * FROM assignments WHERE assignment_creator = %s ORDER BY due_date DESC;", [session['email']])
            assignments = cursor.fetchall()

            cursor.close()
            conn.close()

            flash('New assignment created!')

        return render_template('assignment.html', account=account, assignments=assignments, username=session['username'], class_name=session['class_name'])

    return redirect(url_for('login'))

@app.route('/edit_assignment_grade/<string:id>', methods=['GET'])
def edit_assignment_grade(id):

    if 'loggedin' in session: # This routes the user to the edit assignment grade page.

        conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        cursor.execute('SELECT * FROM users WHERE id = %s', [session['id']])
        account = cursor.fetchone()

        cur = conn.cursor()

        cur.execute("SELECT assignment_name FROM assignments WHERE id = {0} AND assignment_creator = %s;".format(id), (session['email'],))
        records_2 = cur.fetchall()

        cur.execute('SELECT * FROM classes WHERE class_creator = %s;', [session['email']])
        records_3 = cur.fetchall()

        cur.execute("SELECT id FROM assignments WHERE id = {0} AND assignment_creator = %s;".format(id), (session['email'],))
        records_4 = cur.fetchone()

        cur.execute("SELECT due_date FROM assignments WHERE id = {0} AND assignment_creator = %s;".format(id), (session['email'],))
        due_date = cur.fetchall()

        cur.execute("SELECT category FROM assignments WHERE id = {0} AND assignment_creator = %s;".format(id), (session['email'],))
        category = cur.fetchall()

        cur.execute("SELECT * FROM assignments WHERE id = {0} AND assignment_creator = %s;".format(id), (session['email'],))
        records_5 = cur.fetchone()
        session['assignment_id'] = records_5[0]

        cursor.close()
        conn.close()

        return render_template('edit_assignment_grade.html', due_date=due_date, category=category, account=account, records_2=records_2, records_3=records_3, records_4=records_4, username=session['username'], class_name=session['class_name'])

    return redirect(url_for('login'))

@app.route('/update_assignment_name/<string:id>', methods=['POST','GET'])
def update_assignment_name(id):

    if 'loggedin' in session: # This routes the user to the edit assignment grade page.

        conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        cur = conn.cursor()

        update_assignment_name = request.form.get("update_assignment_name")

        cur.execute("""UPDATE assignments 
            SET assignment_name = %s 
            WHERE id = %s;""", (update_assignment_name, id))

        conn.commit()

        cursor.close()
        conn.close()

        return redirect(request.referrer)

    return redirect(url_for('login'))

@app.route('/update_assignment_due_date/<string:id>', methods=['POST','GET'])
def update_assignment_due_date(id):

    if 'loggedin' in session: # This routes the user to the edit assignment grade page.

        conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        cur = conn.cursor()

        update_assignment_due_date = request.form.get("update_assignment_due_date")

        cur.execute("""UPDATE assignments 
            SET due_date = %s 
            WHERE id = %s;""", (update_assignment_due_date, id))

        conn.commit()

        cursor.close()
        conn.close()

        return redirect(request.referrer)

    return redirect(url_for('login'))

@app.route('/edit_assignment_grade_2', methods=['POST', 'GET'])
def edit_assignment_grade_2():

    if 'loggedin' in session:

        conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        grade_assignment = request.form.get("grade_assignment")
        student_id = request.form.get("student_id")

        cur = conn.cursor()

        conn.commit()

        if not grade_assignment:
            flash('Please input the updated grade here.')
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
        elif student_id.isalpha():
            flash('Please enter a grade number between 0 - 100.')
            cursor.close()
            conn.close()
            return redirect(url_for('assignment'))
        else:
            cur.execute("""INSERT INTO assignment_results
            (score, student_id, assignment_id) VALUES (%s, %s, %s) 
            """, (grade_assignment, student_id, session['assignment_id']))

            conn.commit()

            cur.execute("""UPDATE classes 
                        SET student_grade = (
                        SELECT ROUND(AVG(score))
                        FROM assignment_results WHERE student_id = %s)
                        WHERE id = %s;""", (student_id, student_id))

            conn.commit()

            flash('Assignment grade successfully updated!')

            cursor.close()
            conn.close()

            return redirect(request.referrer)

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

        return render_template('view_assignment_scores.html', account=account, assignment_scores=assignment_scores, username=session['username'], class_name=session['class_name'])

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

@app.route('/announcements_page', methods=['GET'])
def announcements_page():

    conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    if 'loggedin' in session:
        cursor.execute('SELECT * FROM users WHERE id = %s', [session['id']])
        account = cursor.fetchone()
        cursor.close()
        conn.close()
        return render_template('announcements_page.html', account=account, username=session['username'], class_name=session['class_name'])

    return redirect(url_for('login'))

@app.route('/announcements_page_submit', methods=['POST', 'GET'])
def announcements_page_submit():

    conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    if 'loggedin' in session:
        announcement_box = request.form.get("announcement_box")
        cursor.execute("INSERT INTO announcements(announcement_date, announcement_time, class, announcement, announcement_creator) VALUES (%s,%s,%s,%s,%s);", (date_object, current_time, session['class_name'], announcement_box, session['email']))
        conn.commit()
        cursor.close()
        conn.close()
        flash(f'Announcement recorded for {date_object} at {current_time}. Your announcement was "{announcement_box}"')
        return redirect(request.referrer)

@app.route('/view_announcements_by_date', methods=['POST', 'GET'])
def view_announcements_by_date():

    if 'loggedin' in session: # Show user and student information from the db
         conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)

         cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

         cursor.execute('SELECT * FROM users WHERE id = %s', [session['id']])
         account = cursor.fetchone()

         search_announcements_by_date = request.form.get("search_announcements_by_date")

         cursor.execute("""SELECT
            * FROM announcements WHERE announcement_date = %s AND announcement_creator = %s;""", (search_announcements_by_date, session['email']))

         search_announcements_query = cursor.fetchall()

         if not search_announcements_by_date:
             flash('Please enter a date according to the format above to view announcements.')
             cursor.close()
             conn.close()
             return redirect(url_for('announcements_page'))

         cursor.close()
         conn.close()

         return render_template('view_announcements_by_date.html', search_announcements_query=search_announcements_query, search_announcements_by_date=search_announcements_by_date, date_object = date_object, account=account, username=session['username'], class_name=session['class_name']
                                )

    return redirect(url_for('login'))

@app.route('/delete_announcement/<string:id>', methods = ['DELETE', 'GET'])
def delete_announcement(id):

    if 'loggedin' in session: # This removes an attendance record from the db.

        conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        cursor.execute('DELETE FROM announcements WHERE id = {0};'.format(id))
        conn.commit()

        cursor.close()
        conn.close()

        return redirect(request.referrer)

    return redirect(url_for('login'))

@app.route('/delete_assignment', methods = ['DELETE', 'POST', 'GET'])
def delete_assignment():

    if 'loggedin' in session:

        conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        cursor.execute('SELECT * FROM users WHERE id = %s;', [session['id']])
        account = cursor.fetchone()

        delete_assignment_name = request.form.get('delete_assignment_name')

        cursor.execute('DELETE FROM assignments WHERE assignment_name = %s AND assignment_creator = %s;', (delete_assignment_name, session['email']))

        conn.commit()

        flash('Assignment removed successfully.')

        cursor.execute("SELECT * FROM assignments WHERE assignment_creator = %s;", [session['email']])

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

        cursor.execute('SELECT * FROM users WHERE id = %s;', [session['id']])
        account = cursor.fetchone()

        cursor.execute('DELETE FROM assignment_results WHERE id = {0};'.format(id))

        conn.commit()

        cursor.execute("""UPDATE classes 
                        SET student_grade = (
                        SELECT ROUND(AVG(score))
                        FROM assignment_results WHERE student_id = %s)
                        WHERE id = %s;""", (session['student_id'], session['student_id']))

        conn.commit()

        cursor.execute("SELECT * FROM assignments WHERE assignment_creator = %s;", [session['email']])

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
        cursor.execute('SELECT * FROM users WHERE email = %s AND secret_question = %s;', (email_2, secret_question_2))

        account_password_reset = cursor.fetchone()

        _hashed_password_reset = generate_password_hash(new_password)

        if account_password_reset:

            cursor.execute("""UPDATE users 
            SET password = %s 
            WHERE email = %s;""", (_hashed_password_reset, email_2))

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
        student_email = request.form['student_email']
        student_password = request.form['student_password']
        student_class_name = request.form['student_class_name']
        teacher_email = request.form['teacher_email']
        student_secret_question = request.form['student_secret_question']

        _hashed_password_student = generate_password_hash(student_password)

        cursor.execute('SELECT * FROM student_accounts WHERE student_first_name = %s AND student_last_name = %s AND class = %s AND teacher_email = %s;', (student_firstname, student_lastname, student_class_name, teacher_email))
        student_account = cursor.fetchone()

        cursor.execute('SELECT * FROM classes WHERE student_first_name = %s AND student_last_name = %s AND class_name = %s AND class_creator = %s;', (student_firstname, student_lastname, student_class_name, teacher_email))
        student_verify = cursor.fetchone()

        if student_account:
            flash('Student account already exists!')
        elif not student_verify:
            flash('Student not enrolled in class!')
        if len(student_password) < 5:
            flash('Password must be longer than 5 characters.')
            cursor.close()
            conn.close()
        elif len(student_password) > 10:
            flash('Password must be shorter than 10 characters.')
            cursor.close()
            conn.close()
        elif not any(char.isdigit() for char in student_password):
            flash('Password should have at least one numeral.')
            cursor.close()
            conn.close()
        elif not any(char.isupper() for char in student_password):
            flash('Password should have at least one uppercase letter.')
            cursor.close()
            conn.close()
        elif not any(char.islower() for char in student_password):
            flash('Password should have at least one lowercase letter.')
            cursor.close()
            conn.close()
        elif not student_firstname or not student_lastname or not student_password:
            flash('Please fill out the form!')
        else:
            # Account doesn't exist and the form data is valid, now insert new account into users table
            cursor.execute("INSERT INTO student_accounts (student_first_name, student_last_name, student_email, password, class, teacher_email, secret_question, account_creation_date) VALUES (%s,%s,%s,%s,%s,%s,%s,%s);", (student_firstname, student_lastname, student_email, _hashed_password_student, student_class_name, teacher_email, student_secret_question, date_object))
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

@app.route('/student_home', methods=['GET'])
def student_home():

    if 'loggedin' in session: # Show user and student information from the db
        conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cursor.execute('SELECT * FROM classes WHERE student_email = %s;', [session['student_email']])
        student_class_info = cursor.fetchall()

        cursor.execute('SELECT account_creation_date FROM student_accounts WHERE student_email = %s;', [session['student_email']])
        account_creation_date = cursor.fetchone()

        cursor.execute('SELECT COUNT (id) FROM student_logins WHERE student_login = %s;', [session['student_email']])
        student_login_count = cursor.fetchone()

        cursor.execute('SELECT * FROM student_logins WHERE student_login = %s AND id = (SELECT MAX(id) FROM student_logins);', [session['student_email']])
        student_login_info = cursor.fetchall()

        cursor.execute('SELECT student_first_name FROM student_accounts WHERE student_email = %s;', [session['student_email']])
        first_name = cursor.fetchone()

        cursor.execute('SELECT student_last_name FROM student_accounts WHERE student_email = %s;', [session['student_email']])
        last_name = cursor.fetchone()

        cursor.execute('SELECT student_email FROM student_accounts WHERE student_email = %s;', [session['student_email']])
        email = cursor.fetchone()

        cursor.execute('SELECT class FROM student_accounts WHERE student_email = %s;', [session['student_email']])
        class_name = cursor.fetchone()

        cursor.execute("""SELECT
        enrollment_date
        FROM classes 
        WHERE student_email = %s;""", [session['student_email']])

        enrollment_date = cursor.fetchone()

        return render_template('student_home.html', first_name=first_name,last_name=last_name,email=email,class_name=class_name, student_class_info=student_class_info,student_login_count=student_login_count,
                               student_login_info=student_login_info, account_creation_date=account_creation_date, enrollment_date=enrollment_date)

    return redirect(url_for('login'))

@app.route('/student_login/', methods=['GET', 'POST'])
def student_login():
    conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    cursor.execute('SELECT COUNT (student_first_name) FROM student_accounts;')
    student_count = cursor.fetchone()

    # Check if "username" and "password" POST requests exist (user submitted form)
    if request.method == 'POST' and 'student_email_2' in request.form and 'student_password_2' in request.form:
        student_email_2 = request.form['student_email_2']
        student_password_2 = request.form['student_password_2']

        cursor.execute('SELECT * FROM student_accounts WHERE student_email = %s;', (student_email_2,))
        student_account = cursor.fetchone()
        if not student_account:
            flash('Account does not exist!')
            return render_template('student_login.html', student_count=student_count, date_object=date_object)

        if student_account:
            password_student = student_account['password']
            # If account exists in users table in out database
            if check_password_hash(password_student, student_password_2):
                # Create session data, we can access this data in other routes
                session['loggedin'] = True
                session['id'] = student_account['id']
                session['student_first_name'] = student_account['student_first_name']
                session['student_last_name'] = student_account['student_last_name']
                session['class_creator'] = student_account['teacher_email']
                session['student_email'] = student_account['student_email']
                session['student_class_name'] = student_account['class']

                cursor.execute("INSERT INTO student_logins (login_date, login_time, student_login) VALUES (%s, %s, %s);", (date_object, current_time, session['student_email']))

                conn.commit()

                # Redirect to home page
                return redirect(url_for('student_home'))
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

    return render_template('student_login.html', student_count=student_count, date_object=date_object, current_time=current_time)

@app.route('/student_assignments', methods=['GET'])
def student_assignments():

    if 'loggedin' in session: # Show user and student information from the db
        conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
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
                WHERE s.student_email = %s
                ORDER BY cu.assignment_name ASC;""", [session['student_email']])
        student_assignments = cursor.fetchall()

        return render_template('student_assignments.html', student_assignments=student_assignments)

    return redirect(url_for('login'))

@app.route('/student_attendance', methods=['GET'])
def student_attendance():

    if 'loggedin' in session: # Show user and student information from the db
        conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cursor.execute("""SELECT
                a.id,
                s.student_first_name,
                s.student_last_name,
                s.class_creator,
                a.date,
                a.attendance_status
                FROM classes s
                INNER JOIN attendance AS a
                ON a.student_id = s.id
                WHERE s.student_email = %s;""", [session['student_email']])
        student_attendance = cursor.fetchall()

        return render_template('student_attendance.html', student_attendance=student_attendance)

    return redirect(url_for('login'))

@app.route('/student_announcements', methods=['GET'])
def student_announcements():

    if 'loggedin' in session: # Show user and student information from the db
        conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cursor.execute("""SELECT * FROM announcements WHERE announcement_creator = %s;""", [session['class_creator']])

        announcements_student_fetch = cursor.fetchall()

        return render_template('student_announcements.html', announcements_student_fetch=announcements_student_fetch,student_attendance=student_attendance)

    return redirect(url_for('login'))

@app.route('/teacher_direct_message_page_submit', methods=['POST', 'GET'])
def teacher_direct_message_page_submit(): #This function routes the logged in user to the page to students

    conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    if 'loggedin' in session:
        message_subject = request.form.get("message_subject")
        cursor.execute('SELECT * FROM student_accounts WHERE student_first_name = %s AND student_last_name = %s;', [session['student_first_name'], session['student_last_name']])
        student_account = cursor.fetchone()
        session['student_class_name'] = student_account['class']
        cursor.execute("""SELECT * FROM classes WHERE student_first_name = %s AND student_last_name = %s;""", [session['student_first_name'], session['student_last_name']])

        class_fetch = cursor.fetchone()

        session['class_creator'] = class_fetch['class_creator']

        session['id'] = class_fetch['id']
        teacher_direct_message_box = request.form.get("teacher_direct_message_box")
        cursor.execute("INSERT INTO teacher_direct_message(date, class, message_subject, message, student_first_name, student_last_name, student_id, message_recipient) VALUES (%s,%s,%s,%s,%s,%s,%s,%s);", (date_object, session['student_class_name'], message_subject, teacher_direct_message_box, session['student_first_name'], session['student_last_name'], session['id'], session['class_creator']))
        cursor.execute("INSERT INTO teacher_direct_message_student_copy(date, class, message_subject, message, student_first_name, student_last_name, student_id, message_recipient) VALUES (%s,%s,%s,%s,%s,%s,%s,%s);", (date_object, session['student_class_name'], message_subject, teacher_direct_message_box, session['student_first_name'], session['student_last_name'], session['id'], session['class_creator']))

        conn.commit()
        flash('Message sent!')

        cursor.close()
        conn.close()

        # Redirect to home page
        return redirect(url_for('student_messages'))

    return redirect(url_for('login'))

@app.route('/student_messages', methods=['GET'])
def student_messages():

    if 'loggedin' in session: # Show user and student information from the db
        conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cursor.execute('SELECT * FROM student_direct_message WHERE student_first_name = %s AND student_last_name = %s AND message_sender = %s;',
                               [session['student_first_name'], session['student_last_name'], session['class_creator']])

        view_student_direct_messages = cursor.fetchall()

        cursor.execute('SELECT * FROM teacher_direct_message_student_copy WHERE student_first_name = %s AND student_last_name = %s AND message_recipient = %s;',
                       [session['student_first_name'], session['student_last_name'], session['class_creator']])

        view_teacher_direct_messages = cursor.fetchall()

        cursor.close()
        conn.close()

        return render_template('student_messages.html', view_student_direct_messages=view_student_direct_messages,view_teacher_direct_messages=view_teacher_direct_messages)

    return redirect(url_for('login'))

@app.route('/delete_direct_message_to_teacher/<string:id>', methods = ['DELETE', 'GET'])
def delete_direct_message_to_teacher(id):

    if 'loggedin' in session: # This removes an attendance record from the db.

        conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        cursor.execute('DELETE FROM teacher_direct_message_student_copy WHERE id = {0};'.format(id))
        conn.commit()

        flash('Message deleted!')

        cursor.close()
        conn.close()

        # Redirect to home page
        return redirect(url_for('student_messages'))

    return redirect(url_for('login'))

@app.route('/delete_direct_message_from_teacher/<string:id>', methods = ['DELETE', 'GET'])
def delete_direct_message_from_teacher(id):

    if 'loggedin' in session: #This removes an attendance record from the db.

        conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        cursor.execute('DELETE FROM student_direct_message WHERE id = {0};'.format(id))
        conn.commit()

        cursor.close()
        conn.close()

        # Redirect to home page
        return redirect(url_for('student_messages'))

    return redirect(url_for('login'))

@app.route('/student_reset_password', methods=['GET', 'POST'])
def student_reset_password():

    conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    # Check if "username" and "password" POST requests exist (user submitted form)
    if request.method == 'POST' and 'student_email_reset_password' in request.form and 'student_secret_question_2' in request.form and 'student_new_password' in request.form:
        student_email_reset_password = request.form['student_email_reset_password']
        student_secret_question_2 = request.form['student_secret_question_2']
        student_new_password = request.form['student_new_password']

        # Check if account exists
        cursor.execute('SELECT * FROM student_accounts WHERE student_email = %s AND secret_question = %s;', (student_email_reset_password, student_secret_question_2))

        student_account_password_reset = cursor.fetchone()

        _hashed_password_reset_student = generate_password_hash(student_new_password)

        if student_account_password_reset:

            cursor.execute("""UPDATE student_accounts 
            SET password = %s 
            WHERE student_email = %s;""", (_hashed_password_reset_student, student_email_reset_password))

            conn.commit()

            # Redirect to home page
            flash(f'Password updated for {student_email_reset_password}')

            cursor.close()
            conn.close()
            return redirect(url_for('student_reset_password'))
        else:
            # Account doesn't exist or username/password incorrect
            flash('Incorrect credentials')
            cursor.close()
            conn.close()

    return render_template('student_reset_password.html')

@app.route('/delete_student_account', methods=['DELETE', 'GET', 'POST'])
def delete_student_account():

    conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    # Check if "username", "password" and "email" POST requests exist (user submitted form)
    if request.method == 'POST' and 'delete_student_email' in request.form and 'delete_student_password' in request.form:
        # Create variables to reference for below queries
        delete_student_email = request.form['delete_student_email']
        delete_student_password = request.form['delete_student_password']

        _hashed_password_delete_student = generate_password_hash(delete_student_password)

        cursor.execute('SELECT COUNT (student_first_name) FROM student_accounts;')
        student_count_2 = cursor.fetchone()

        # Check if account exists:
        cursor.execute('SELECT * FROM student_accounts WHERE student_email = %s;', (delete_student_email,))
        delete_student_account_query = cursor.fetchone()
        # If account exists show error and validation checks
        if delete_student_account_query:
            delete_student_password_check = delete_student_account_query['password']
            if check_password_hash(delete_student_password_check, delete_student_password):
                cursor.execute('DELETE FROM student_accounts WHERE student_email = %s;', (delete_student_email,))
                flash('Account successfully deleted.')
                conn.commit()
                cursor.close()
                conn.close()
            else:
                flash('Incorrect password.')
                cursor.close()
                conn.close()
        elif not delete_student_account_query:
            flash('No account found.')
            cursor.close()
            conn.close()
        else:
            flash('Invalid credentials.')
            cursor.close()
            conn.close()
    elif request.method == 'POST':
        # Form is empty
        flash('Please fill out the form!')
        cursor.close()
        conn.close()
    # Show registration form with message (if applicable)
    return render_template('student_login.html', student_count_2=student_count_2)

if __name__ == "__main__":
    app.run(debug=True)
