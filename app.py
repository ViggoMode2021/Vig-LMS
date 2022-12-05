from flask import Flask, request, session, redirect, url_for, render_template, flash
import psycopg2
import psycopg2.extras
import re
from werkzeug.security import generate_password_hash, check_password_hash
import datetime
import pytz #US/Eastern
import boto3
from botocore.exceptions import ClientError
import os
from dotenv import load_dotenv, find_dotenv

# Module imports
from files import files
from grades import grades
from assignments import assignments
from messaging_and_announcements import messaging_and_announcements
from student_info_for_teachers import student_info_for_teachers
from attendance import attendance
from student_portal import student_portal

load_dotenv(find_dotenv())

dotenv_path = os.path.join(os.path.dirname(__file__), ".env_vig_lms")
load_dotenv(dotenv_path)

app = Flask(__name__)

app.secret_key = os.getenv("SECRET_KEY")

app.register_blueprint(files)
app.register_blueprint(grades)
app.register_blueprint(messaging_and_announcements)
app.register_blueprint(student_portal)
app.register_blueprint(student_info_for_teachers)
app.register_blueprint(assignments)
app.register_blueprint(attendance)

# VigLMS uses boto3 for users to upload and download files across accounts.

s3 = boto3.client('s3',
                    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
                     )

BUCKET_NAME = os.getenv('BUCKET_NAME_VAR') # Set as environment variable

CLIENT_ID = os.getenv('CLIENT_ID')

USER_POOL_ID = os.getenv('USER_POOL_ID')

#Database info below:

DB_HOST = os.getenv('DB_HOST')
DB_NAME = os.getenv('DB_NAME')
DB_USER = os.getenv('DB_USER')
DB_PASS = os.getenv('DB_PASS')

@app.route('/register', methods=['GET', 'POST'])
def register():

    conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    # Check if "username", "password" and "email" POST requests exist (user submitted form)
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form and 'email' in request.form:

        # Create variables to reference for below queries
        fullname = request.form['fullname']
        email = request.form['email']
        username = request.form['username']
        password = request.form['password']
        class_name = request.form['class_name']

        _hashed_password = generate_password_hash(password)

        # Check if account exists:
        cursor.execute('SELECT username FROM users WHERE username = %s;', (username,))
        account = cursor.fetchone()

        cursor.execute('SELECT email FROM users WHERE email = %s;', (email,))
        email_confirm = cursor.fetchone()

        date = datetime.date.today()

        format_code = '%m-%d-%Y'

        date_object = date.strftime(format_code)

        timezone = pytz.timezone('US/Eastern')

        # If account exists show error and validation checks
        if account:
            for a in account:
                flash(f'Account already exists for {a}!')
                cursor.close()
                conn.close()
        elif email_confirm:
            for e in email_confirm:
                flash(f'Account already exists for {e}!')
                cursor.close()
                conn.close()
        elif not re.match(r'[A-Za-z0-9]+', username):
            flash('Username must contain only characters and numbers!')
            cursor.close()
            conn.close()
        elif len(password) < 5:
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
        else:
            # Account doesn't exist and the form data is valid, new account is created in the users table with the below queries:
            cursor.execute("INSERT INTO users (fullname, username, password, email, class, account_creation_date) VALUES (%s,%s,%s,%s,%s,%s);", (fullname, username, _hashed_password, email, class_name, date_object))
            conn.commit()
            example = 'example'
            student = 'student'
            cursor.execute("INSERT INTO classes (student_first_name, student_last_name, class_name, teacher, class_creator) VALUES (%s,%s,%s,%s, (SELECT email from users WHERE fullname = %s))", (example, student, class_name, fullname, fullname))
            conn.commit()
            flash(f'You have successfully registered as "{username}"! Your email is "{email}", your username is "{username}" and your class name is'
                  f'" {class_name}".')

            client = boto3.client("cognito-idp", region_name="us-east-1")

            # The below code, will do the sign-up
            client.sign_up(
                ClientId=CLIENT_ID,
                Username=email,
                Password=password,
                UserAttributes=[{"Name": "email", "Value": email}],
            )

            cursor.close()
            conn.close()

            session['loggedin'] = True

            session['username'] = email

            return redirect(url_for('authenticate_page'))
        # Show registration form with message (if applicable)
    return render_template('register.html')

@app.route('/authenticate_page', methods=['GET'])
def authenticate_page():
    if 'loggedin' in session:
        return render_template('authenticate.html')

    return redirect(url_for('login'))

@app.route('/authenticate', methods=['POST'])
def authenticate():
    try:
        if 'loggedin' in session:
            authentication_code = request.form.get('authentication_code')
            client = boto3.client("cognito-idp", region_name="us-east-1")

            conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
            cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

            client.confirm_sign_up(
                ClientId=CLIENT_ID,
                Username=session['username'],
                ConfirmationCode=authentication_code,
                ForceAliasCreation=False
            )

            flash('You have authenticated!')

            cursor.execute("UPDATE users SET authenticated_account = %s WHERE email = %s", ('Authenticated', session['username']))

            conn.commit()

            cursor.close()
            conn.close()

            session.pop('username')

            return redirect(url_for('login'))

    except ClientError as e:
        flash("Incorrect authentication code")
        return redirect(url_for('authenticate_page'))

    return redirect(url_for('login'))

@app.route('/login/', methods=['GET', 'POST'])
def login():
    conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor) #Make connection to db via Psycopg2

    cursor.execute('SELECT COUNT (username) FROM users;')
    user_count = cursor.fetchone() #This shows the number of users using the application

    date = datetime.date.today()

    format_code = '%m-%d-%Y'

    date_object = date.strftime(format_code)

    timezone = pytz.timezone('US/Eastern')
    now = datetime.datetime.now(tz=timezone)
    current_time = now.strftime("%I:%M %p")

    # Check if "username" and "password" POST requests exist (user submitted form)
    if request.method == 'POST' and 'password' in request.form and 'email' in request.form:
        password = request.form['password']
        email = request.form['email']

        # Check if account exists
        cursor.execute('SELECT * FROM users WHERE email = %s AND authenticated_account = %s;', (email, 'Authenticated'))
        account = cursor.fetchone()
        # Grab user information from classes table. The classes table contains information that the user submitted. This is student information and grades.
        cursor.execute('SELECT * FROM classes WHERE class_creator = %s;', (email,))
        account_2 = cursor.fetchone()

        # If above information is adequate:
        if account and account_2:
            password_rs = account['password']
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

        cursor.execute('SELECT COUNT (id) FROM assignment_files_teacher_s3 WHERE assignment_creator = %s;', [session['email']])
        teacher_document_count = cursor.fetchone()

        cursor.execute('SELECT * FROM logins WHERE user_login = %s AND id = (SELECT MAX(id) FROM logins);', [session['email']])
        login_info = cursor.fetchall()

        cursor.close()
        conn.close()

        # If user is logged in, they are directed to home page.
        return render_template('home_page.html', username=session['username'], class_name=session['class_name'], email=session['email'], name=session['name'],
                               student_count=student_count, assignment_count=assignment_count, account_creation_date=account_creation_date, login_count=login_count, teacher_document_count=teacher_document_count, login_info=login_info)
    # If user is not logged in, they are directed to the login page.
    return redirect(url_for('login'))

@app.route('/faq_page', methods=['GET'])
def faq_page():
    return render_template("faq_page.html")

@app.route('/forgot_password_page', methods=['GET'])
def forgot_password_page():
    return render_template('forgot_password_page.html')

@app.route('/teacher_request_password_reset', methods=['POST', 'GET'])
def teacher_request_password_reset():

    teacher_email_forgot_password = request.form.get('teacher_email_forgot_password')

    conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    cursor.execute('SELECT email FROM users WHERE email = %s;', (teacher_email_forgot_password,))

    email_confirmation = cursor.fetchone()

    conn.close()
    cursor.close()

    if email_confirmation:

        client = boto3.client("cognito-idp", region_name="us-east-1")
        # Initiating the Authentication,
        client.forgot_password(
            ClientId=CLIENT_ID,
            Username=teacher_email_forgot_password
        )

        session['username'] = teacher_email_forgot_password
        return render_template('authenticate_new_password.html')

    else:

        flash('User is not in system!')
        return render_template('forgot_password_page.html')

@app.route('/teacher_confirm_forgot_password', methods=['POST', 'GET'])
def teacher_confirm_forgot_password():
        try:
            email_new_password = request.form.get('username_new_password')
            authentication_code_new_password = request.form.get('authentication_code_new_password')
            new_password = request.form.get('new_password')

            conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
            cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

            client = boto3.client("cognito-idp", region_name="us-east-1")

            client.confirm_forgot_password(
                ClientId=CLIENT_ID,
                Username=email_new_password,
                ConfirmationCode=authentication_code_new_password,
                Password=new_password
            )

            _hashed_password_reset = generate_password_hash(new_password)

            cursor.execute("""UPDATE users 
            SET password = %s 
            WHERE email = %s;""", (_hashed_password_reset, email_new_password))

            conn.commit()

            flash(f'Password reset successfully for {email_new_password}.')
            return redirect(url_for('login'))

        except:
            flash('One or more fields are incorrect. Please try again.')
            return render_template('authenticate_new_password.html')

@app.route('/delete_teacher_account_page', methods=['GET'])
def delete_teacher_account_page():
    return render_template("delete_teacher_account.html")

@app.route('/delete_account', methods=['DELETE', 'GET', 'POST'])
def delete_account():

    conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    # Check if "username", "password" and "email" POST requests exist (user submitted form)
    if request.method == 'POST' and 'delete_username' in request.form and 'delete_password' in request.form and 'delete_email' in request.form:
        # Create variables to reference for below queries
        delete_username = request.form.get('delete_username')
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
                cursor.execute('DELETE FROM assignment_files_teacher_s3 WHERE assignment_creator = %s', (delete_email,))

                conn.commit()
                cursor.close()
                conn.close()

                client = boto3.client('cognito-idp', region_name="us-east-1")

                client.admin_delete_user(
                UserPoolId=USER_POOL_ID,
                Username=delete_email
                )

                flash(f'Account successfully deleted for Username: {delete_username} with email: {delete_email}.')
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

if __name__ == "__main__":
    app.run(debug=True)

