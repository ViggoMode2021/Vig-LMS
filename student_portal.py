from flask import request, session, redirect, url_for, render_template, flash, Blueprint
import psycopg2
import psycopg2.extras
from werkzeug.security import generate_password_hash, check_password_hash
import datetime
import pytz #US/Eastern
import boto3
from botocore.exceptions import ClientError
import os
from dotenv import load_dotenv, find_dotenv
from werkzeug.utils import secure_filename

load_dotenv(find_dotenv())

CLIENT_ID = os.getenv('CLIENT_ID')

#Database info below:

DB_HOST = os.getenv('DB_HOST')
DB_NAME = os.getenv('DB_NAME')
DB_USER = os.getenv('DB_USER')
DB_PASS = os.getenv('DB_PASS')

student_portal = Blueprint("student_portal", __name__)

s3 = boto3.client('s3',
                    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
                     )

BUCKET_NAME = os.getenv('BUCKET_NAME_VAR')

USER_POOL_ID = os.getenv('USER_POOL_ID')

@student_portal.route('/student_register', methods=['GET', 'POST'])
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

        _hashed_password_student = generate_password_hash(student_password)

        cursor.execute('SELECT * FROM student_accounts WHERE student_first_name = %s AND student_last_name = %s AND class = %s AND teacher_email = %s;', (student_firstname, student_lastname, student_class_name, teacher_email))
        student_account = cursor.fetchone()

        cursor.execute('SELECT * FROM classes WHERE student_first_name = %s AND student_last_name = %s AND class_name = %s AND class_creator = %s;', (student_firstname, student_lastname, student_class_name, teacher_email))
        student_verify = cursor.fetchone()

        date = datetime.date.today()

        format_code = '%m-%d-%Y'

        date_object = date.strftime(format_code)

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
            cursor.execute("INSERT INTO student_accounts (student_first_name, student_last_name, student_email, password, class, teacher_email, account_creation_date) VALUES (%s,%s,%s,%s,%s,%s,%s);", (student_firstname, student_lastname, student_email, _hashed_password_student, student_class_name, teacher_email, date_object))
            conn.commit()
            flash(f'You have successfully registered with the email "{student_email}". Your other credentials are: First Name: "{student_firstname}" Last Name:  "{student_lastname}" Class Name:  "{student_class_name}".!')
            cursor.close()
            conn.close()
            client = boto3.client("cognito-idp", region_name="us-east-1")

            # The below code, will do the sign-up
            client.sign_up(
                ClientId=CLIENT_ID,
                Username=student_email,
                Password=student_password,
                UserAttributes=[{"Name": "email", "Value": student_email}],
            )

            session['loggedin'] = True

            session['username'] = student_email

            return redirect(url_for('student_portal.student_authenticate_page'))

    elif request.method == 'POST':
        # Form is empty... (no POST data)
        flash('Please fill out the form!')
        cursor.close()
        conn.close()
    # Show registration form with message (if any)
    return render_template('student_register.html')

@student_portal.route('/student_authenticate_page', methods=['GET'])
def student_authenticate_page():
    if 'loggedin' in session:
        return render_template('student_authenticate.html')

    return redirect(url_for('student_portal.student_login'))

@student_portal.route('/student_authenticate', methods=['POST'])
def student_authenticate():
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

            cursor.execute("UPDATE student_accounts SET authenticated_account = %s WHERE student_email = %s", ('Authenticated', session['username']))

            conn.commit()

            cursor.close()
            conn.close()

            session.pop('username')

            return redirect(url_for('student_portal.student_login'))

    except ClientError as e:
        flash("Incorrect authentication code")
        return redirect(url_for('student_portal.student_authenticate_page'))

    return redirect(url_for('login'))

@student_portal.route('/student_home', methods=['GET'])
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

        cursor.execute('SELECT enrollment_date FROM classes WHERE student_email = %s;', [session['student_email']])
        enrollment_date = cursor.fetchone()

        cursor.execute('SELECT COUNT (id) FROM assignment_files_teacher_s3 WHERE assignment_creator = %s;', [session['class_creator']])
        teacher_document_count = cursor.fetchone()

        cursor.execute('SELECT COUNT (id) FROM assignment_files_student_s3 WHERE student_email = %s;', [session['student_email']])
        student_document_count = cursor.fetchone()

        for first, last in zip(first_name, last_name):
            flash(f'You have successfully logged in {first} {last}!')

        cursor.execute("""SELECT
        enrollment_date
        FROM classes 
        WHERE student_email = %s;""", [session['student_email']])

        return render_template('student_home_page.html', first_name=first_name, last_name=last_name, email=email, class_name=class_name, student_class_info=student_class_info,student_login_count=student_login_count,
                               student_login_info=student_login_info, account_creation_date=account_creation_date, enrollment_date=enrollment_date, teacher_document_count=teacher_document_count, student_document_count=student_document_count
                               )

    return redirect(url_for('login'))

@student_portal.route('/student_login/', methods=['GET', 'POST'])
def student_login():
    conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    cursor.execute('SELECT COUNT (student_first_name) FROM student_accounts;')
    student_count = cursor.fetchone()

    date = datetime.date.today()

    format_code = '%m-%d-%Y'

    date_object = date.strftime(format_code)

    timezone = pytz.timezone('US/Eastern')
    now = datetime.datetime.now(tz=timezone)
    current_time = now.strftime("%I:%M %p")

    # Check if "username" and "password" POST requests exist (user submitted form)
    if request.method == 'POST' and 'student_email_2' in request.form and 'student_password_2' in request.form:
        student_email_2 = request.form['student_email_2']
        student_password_2 = request.form['student_password_2']

        cursor.execute('SELECT * FROM student_accounts WHERE student_email = %s AND authenticated_account = %s;', (student_email_2, 'Authenticated'))
        student_account = cursor.fetchone()
        if not student_account:
            flash(f'Account does not exist for {student_email_2}!')
            return render_template('student_login.html', student_count=student_count, date_object=date_object, current_time=current_time)

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
                return redirect(url_for('student_portal.student_home'))
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

@student_portal.route('/student_assignments', methods=['GET'])
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
                WHERE s.student_email = %s AND ci.score IS NULL
                ORDER BY cu.assignment_name ASC;""", [session['student_email']])

        student_assignments_null = cursor.fetchall()

        cursor.execute('SELECT * FROM assignment_files_teacher_s3 WHERE assignment_creator = %s ORDER BY upload_date DESC;', [session['class_creator']])
        student_assignments_originals = cursor.fetchall()

        cursor.execute('SELECT * FROM assignment_files_student_s3 WHERE student_email = %s ORDER BY upload_date DESC;', [session['student_email']])
        student_assignments_student_s3 = cursor.fetchall()

        first_name = session['student_first_name']

        last_name = session['student_last_name']

        class_name = session['student_class_name']

        cursor.close()
        conn.close()

        return render_template('student_portal_assignments.html', first_name=first_name, last_name=last_name, class_name=class_name, student_assignments=student_assignments, student_assignments_student_s3=student_assignments_student_s3, student_assignments_originals=student_assignments_originals,
                               student_assignments_null=student_assignments_null)

    return redirect(url_for('student_portal.student_login'))

@student_portal.route('/student_assignment_originals_download/<string:id>', methods=['GET'])
def student_assignment_originals_download(id):
    if 'loggedin' in session: # Show user and student information from the db
        conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        cursor.execute('SELECT assignment_name FROM assignment_files_teacher_s3 WHERE id = {0} AND assignment_creator = %s;'.format(id), [session['class_creator']])
        assignment_download_name = cursor.fetchone()[0]
        cursor.execute('SELECT * FROM assignment_files_teacher_s3 WHERE assignment_creator = %s ORDER BY upload_date DESC;', [session['class_creator']])
        assignment_files = cursor.fetchall()
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

        cursor.execute('SELECT * FROM assignment_files_teacher_s3 WHERE assignment_creator = %s ORDER BY upload_date DESC;', [session['class_creator']])
        student_assignments_originals = cursor.fetchall()

        cursor.execute('SELECT * FROM assignment_files_student_s3 WHERE student_email = %s ORDER BY upload_date DESC;', [session['student_email']])
        student_assignments_student_s3 = cursor.fetchall()

        cursor.close()
        conn.close()
        msg_3 = f"Click link to download {assignment_download_name}"
        response_2 = s3.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': BUCKET_NAME,
                'Key': str(assignment_download_name)
            },
            ExpiresIn=3600
        )
        return render_template("student_portal_assignments.html", student_assignments_student_s3=student_assignments_student_s3, student_assignments=student_assignments, student_assignments_originals=student_assignments_originals, assignment_files=assignment_files, msg_3=msg_3, response_2=response_2)

    return redirect(url_for('student_portal.student_login'))

@student_portal.route('/download_uploads_student_account/<string:id>', methods=['GET'])
def download_uploads_student_account(id):
    if 'loggedin' in session: # Show user and student information from the db
        conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cursor.execute('SELECT file_name FROM assignment_files_student_s3 WHERE id = {0} AND student_email = %s;'.format(id), [session['student_email']])
        download_uploads_student_account_name = cursor.fetchone()[0]
        cursor.execute('SELECT * FROM assignment_files_teacher_s3 WHERE assignment_creator = %s;', [session['class_creator']])
        assignment_files = cursor.fetchall()
        cursor.execute("""SELECT
                    ci.id AS score_id,
                    s.student_first_name,
                    s.student_last_name,
                    ci.score,
                    cu.assignment_name,
                    cu.description
                    FROM classes s
                    INNER JOIN assignment_results AS ci
                    ON ci.student_id = s.id
                    INNER JOIN assignments cu  
                    ON cu.id = ci.assignment_id
                    WHERE s.student_email = %s
                    ORDER BY cu.assignment_name ASC;""", [session['student_email']])

        student_assignments = cursor.fetchall()

        cursor.execute('SELECT * FROM assignment_files_teacher_s3 WHERE assignment_creator = %s;', [session['class_creator']])
        student_assignments_originals = cursor.fetchall()

        cursor.execute('SELECT * FROM assignment_files_student_s3 WHERE student_email = %s;', [session['student_email']])
        student_assignments_student_s3 = cursor.fetchall()

        cursor.close()
        conn.close()
        msg_4 = f"Click link to download {download_uploads_student_account_name}"
        response_3 = s3.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': BUCKET_NAME,
                'Key': str(download_uploads_student_account_name)
            },
            ExpiresIn=3600
        )
        return render_template("student_portal_assignments.html", student_assignments_student_s3=student_assignments_student_s3, msg_4=msg_4, response_3=response_3, student_assignments=student_assignments, student_assignments_originals=student_assignments_originals, assignment_files=assignment_files)

    return redirect(url_for('student_portal.student_login'))

@student_portal.route('/delete_student_upload/<string:id>', methods=['GET', 'POST'])
def delete_student_upload(id):
    if 'loggedin' in session: # Show user and student information from the db
        conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cursor.execute('SELECT file_name FROM assignment_files_student_s3 WHERE id = {0} AND student_email = %s ORDER BY upload_date DESC;'.format(id), [session['student_email']])
        assignment_delete_name = cursor.fetchone()
        for name in assignment_delete_name:
            flash(f'{name} deleted!')
        s3.delete_objects(
        Bucket=BUCKET_NAME,
        Delete={
            'Objects': [
                {
                    'Key': str(assignment_delete_name)
                }
            ]
        }
        )
        cursor.execute('DELETE FROM assignment_files_student_s3 WHERE id = {0} AND student_email = %s;'.format(id), [session['student_email']])
        conn.commit()

        cursor.close()
        conn.close()
        return redirect(url_for('student_portal.student_assignments'))

    return redirect(url_for('student_portal.student_login'))

@student_portal.route('/student_documents_to_teacher', methods=['POST'])
def student_documents_to_teacher():

    if 'loggedin' in session: # Show user and student information from the db

        if request.method == 'POST':
            img_2 = request.files['file_2']
            if img_2:
                    date = datetime.date.today()

                    format_code = '%m-%d-%Y'

                    date_object = date.strftime(format_code)

                    timezone = pytz.timezone('US/Eastern')
                    now = datetime.datetime.now(tz=timezone)
                    current_time = now.strftime("%I:%M %p")
                    email = [session['student_email']]
                    filename = secure_filename(img_2.filename + "  email  " + str(email))
                    img_2.save(filename)
                    conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
                    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
                    cursor.execute("INSERT INTO assignment_files_student_s3 (file_name, student_email, upload_date, upload_time) VALUES (%s, %s, %s, %s);", (filename, session['student_email'], date_object, current_time))
                    conn.commit()
                    s3.upload_file(
                        Bucket=BUCKET_NAME,
                        Filename=filename,
                        Key=filename
                    )
                    flash(f'{filename} has been uploaded to teacher and student portal for your class.')

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

                    cursor.execute('SELECT * FROM assignment_files_teacher_s3 WHERE assignment_creator = %s;', [session['class_creator']])
                    student_assignments_originals = cursor.fetchall()

                    cursor.execute('SELECT * FROM assignment_files_student_s3 WHERE student_email = %s;', [session['student_email']])
                    student_assignments_student_s3 = cursor.fetchall()

                    class_name = session['student_class_name']

                    cursor.close()
                    conn.close()

            else:
                flash('No file has been selected to upload. Please click "Choose File button".')
                return redirect(url_for("student_portal.student_assignments"))
            return render_template("student_assignments.html", student_assignments_student_s3=student_assignments_student_s3, student_assignments=student_assignments,
                                   student_assignments_originals=student_assignments_originals, class_name=class_name)

    return redirect(url_for('student_portal.student_login'))

@student_portal.route('/student_attendance', methods=['GET'])
def student_attendance():

    if 'loggedin' in session: # Show user and student information from the db
        conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        cursor.execute("""SELECT id FROM classes WHERE student_email = %s""", [session['student_email']])
        student_id_for_attendance = cursor.fetchone()[0]

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

        cursor.execute("SELECT COUNT (attendance_status) FROM attendance WHERE student_id = %s AND attendance_status = 'Tardy';", (student_id_for_attendance,))
        student_tardy_count = cursor.fetchone()

        cursor.execute("SELECT COUNT (attendance_status) FROM attendance WHERE student_id = %s AND attendance_status = 'Absent';", (student_id_for_attendance,))
        student_absent_count = cursor.fetchone()

        cursor.execute("SELECT COUNT (attendance_status) FROM attendance WHERE student_id = %s AND attendance_status = 'Present';", (student_id_for_attendance,))
        student_present_count = cursor.fetchone()

        first_name = session['student_first_name']
        last_name = session['student_last_name']

        class_name = session['student_class_name']

        return render_template('student_portal_attendance.html', student_attendance=student_attendance, student_tardy_count=student_tardy_count,
                               student_absent_count=student_absent_count, first_name=first_name, last_name=last_name, class_name=class_name, student_present_count=student_present_count )

    return redirect(url_for('login'))

@student_portal.route('/student_announcements', methods=['GET'])
def student_announcements():

    if 'loggedin' in session: # Show user and student information from the db
        conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cursor.execute("""SELECT * FROM announcements WHERE announcement_creator = %s;""", [session['class_creator']])

        announcements_student_fetch = cursor.fetchall()

        class_name = session['student_class_name']

        first_name = session['student_first_name']

        last_name = session['student_last_name']

        return render_template('student_portal_announcements.html', class_name=class_name, announcements_student_fetch=announcements_student_fetch,student_attendance=student_attendance,
                               first_name=first_name, last_name=last_name)

    return redirect(url_for('login'))

@student_portal.route('/teacher_direct_message_page_submit', methods=['POST', 'GET'])
def teacher_direct_message_page_submit():

    conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    if 'loggedin' in session:
        message_subject = request.form.get("message_subject")
        cursor.execute('SELECT * FROM student_accounts WHERE student_first_name = %s AND student_last_name = %s;', [session['student_first_name'], session['student_last_name']])
        student_account = cursor.fetchone()
        session['student_class_name'] = student_account['class']

        cursor.execute('SELECT id FROM classes WHERE student_email = %s;', [session['student_email']])
        student_id = cursor.fetchone()[0]

        date = datetime.date.today()

        format_code = '%m-%d-%Y'

        date_object = date.strftime(format_code)

        timezone = pytz.timezone('US/Eastern')
        now = datetime.datetime.now(tz=timezone)
        current_time = now.strftime("%I:%M %p")

        teacher_direct_message_box = request.form.get("teacher_direct_message_box")
        cursor.execute("INSERT INTO teacher_direct_message(date, time, class, message_subject, message, student_first_name, student_last_name, student_id, message_recipient) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s);", (date_object, current_time, session['student_class_name'], message_subject, teacher_direct_message_box, session['student_first_name'], session['student_last_name'], student_id, session['class_creator']))
        cursor.execute("INSERT INTO teacher_direct_message_student_copy(date, time, class, message_subject, message, student_first_name, student_last_name, student_id, message_recipient) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s);", (date_object, current_time, session['student_class_name'], message_subject, teacher_direct_message_box, session['student_first_name'], session['student_last_name'], student_id, session['class_creator']))

        conn.commit()

        flash(f'Message sent successfully on {date_object} at {current_time}!. '
                f'Your subject was: "{message_subject}" and the \n'
                f' message was "{teacher_direct_message_box}".')

        cursor.close()
        conn.close()

        # Redirect to home page
        return redirect(url_for('student_portal.student_messages'))

    return redirect(url_for('login'))

@student_portal.route('/student_messages', methods=['GET'])
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

        first_name = session['student_first_name']
        last_name = session['student_last_name']

        cursor.close()
        conn.close()

        return render_template('student_portal_messages.html', view_student_direct_messages=view_student_direct_messages, view_teacher_direct_messages=view_teacher_direct_messages,
                               first_name=first_name, last_name=last_name)

    return redirect(url_for('login'))

@student_portal.route('/delete_direct_message_to_teacher/<string:id>', methods = ['DELETE', 'GET'])
def delete_direct_message_to_teacher(id):

    if 'loggedin' in session: # This removes an attendance record from the db.

        conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        cursor.execute('SELECT message_subject FROM teacher_direct_message_student_copy WHERE id = {0};'.format(id))

        message_subject = cursor.fetchone()

        cursor.execute('SELECT message FROM teacher_direct_message_student_copy WHERE id = {0};'.format(id))

        message = cursor.fetchone()

        cursor.execute('SELECT date FROM teacher_direct_message_student_copy WHERE id = {0};'.format(id))

        message_date = cursor.fetchone()

        cursor.execute('SELECT time FROM teacher_direct_message_student_copy WHERE id = {0};'.format(id))

        message_time = cursor.fetchone()

        cursor.execute('DELETE FROM teacher_direct_message_student_copy WHERE id = {0};'.format(id))
        conn.commit()

        for subject, body, mes_date, time in zip(message_subject, message, message_date, message_time):
            flash(f'Message deleted! The message subject was "{subject}" and the message was "{body}". The message'
                  f' was sent at {time} on {mes_date}.')

        cursor.close()
        conn.close()

        # Redirect to home page
        return redirect(url_for('student_portal.student_messages'))

    return redirect(url_for('login'))

@student_portal.route('/delete_direct_message_from_teacher/<string:id>', methods = ['DELETE', 'GET'])
def delete_direct_message_from_teacher(id):

    if 'loggedin' in session: #This removes an attendance record from the db.

        conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        cursor.execute('SELECT message_subject FROM student_direct_message WHERE id = {0};'.format(id))

        message_subject = cursor.fetchone()

        cursor.execute('SELECT message FROM student_direct_message WHERE id = {0};'.format(id))

        message = cursor.fetchone()

        cursor.execute('SELECT date FROM student_direct_message WHERE id = {0};'.format(id))

        message_date = cursor.fetchone()

        cursor.execute('SELECT time FROM student_direct_message WHERE id = {0};'.format(id))

        message_time = cursor.fetchone()

        cursor.execute('DELETE FROM student_direct_message WHERE id = {0};'.format(id))
        conn.commit()

        for subject, body, mes_date, time in zip(message_subject, message, message_date, message_time):
            flash(f'Message deleted! The message subject was "{subject}" and the message was "{body}". The message'
                  f' was sent at {time} on {mes_date}.')

        cursor.close()
        conn.close()

        # Redirect to home page
        return redirect(url_for('student_portal.student_messages'))

    return redirect(url_for('login'))

@student_portal.route('/student_forgot_password_page', methods=['GET'])
def student_forgot_password_page():
    return render_template('student_forgot_password_page.html')

@student_portal.route('/request_password_reset', methods=['POST', 'GET'])
def request_password_reset():

    email_forgot_password = request.form.get('email_forgot_password')

    conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    cursor.execute('SELECT student_email FROM student_accounts WHERE student_email = %s;', (email_forgot_password,))

    email_confirmation = cursor.fetchone()

    conn.close()
    cursor.close()

    if email_confirmation:

        client = boto3.client("cognito-idp", region_name="us-east-1")
        # Initiating the Authentication,
        client.forgot_password(
            ClientId=CLIENT_ID,
            Username=email_forgot_password
        )

        session['username'] = email_forgot_password
        return render_template('authenticate_new_student_password.html')

    else:

        flash('User is not in system!')
        return render_template('student_forgot_password_page.html')

@student_portal.route('/confirm_forgot_password', methods=['POST', 'GET'])
def confirm_forgot_password():
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

            cursor.execute("""UPDATE student_accounts 
            SET password = %s 
            WHERE student_email = %s;""", (_hashed_password_reset, email_new_password))

            conn.commit()

            flash(f'Password reset successfully for {email_new_password}.')
            return redirect(url_for('student_portal.student_login'))

        except:
            flash('One or more fields are incorrect. Please try again.')
            return render_template('authenticate_new_student_password.html')

@student_portal.route('/delete_student_account_page', methods=['GET'])
def delete_student_account_page():
    return render_template("delete_student_account.html")

@student_portal.route('/delete_student_account', methods=['DELETE', 'GET', 'POST'])
def delete_student_account():

    conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    # Check if "username", "password" and "email" POST requests exist (user submitted form)
    if request.method == 'POST' and 'delete_student_email' in request.form and 'delete_student_password' in request.form:
        # Create variables to reference for below queries
        delete_student_email = request.form.get('delete_student_email')

        delete_student_password = request.form.get('delete_student_password')

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

                client = boto3.client('cognito-idp', region_name="us-east-1")

                client.admin_delete_user(
                UserPoolId=USER_POOL_ID,
                Username=delete_student_email
                )

                flash(f'Account successfully deleted for {delete_student_email}.')
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

@student_portal.route('/student_logout')
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
   return redirect(url_for('student_portal.student_login'))
