from flask import request, session, redirect, url_for, render_template, flash, Blueprint
import psycopg2
import psycopg2.extras
import os
from dotenv import load_dotenv, find_dotenv
import boto3
import datetime
import csv
import io

load_dotenv(find_dotenv())

#Database info below:

DB_HOST = os.getenv('DB_HOST')
DB_NAME = os.getenv('DB_NAME')
DB_USER = os.getenv('DB_USER')
DB_PASS = os.getenv('DB_PASS')

s3 = boto3.client('s3',
                    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
                     )

BUCKET_NAME = os.getenv('BUCKET_NAME_VAR')

student_info_for_teachers = Blueprint("student_info_for_teachers", __name__)

@student_info_for_teachers.route('/enroll_page', methods=['GET'])
def enroll_page(): #This function routes the logged in user to the page to enroll students

    conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    if 'loggedin' in session:
        cursor.execute('SELECT * FROM users WHERE id = %s;', [session['id']])
        account = cursor.fetchone()
        cursor.close()
        conn.close()
        return render_template('enroll_student.html', account=account, username=session['username'], class_name=session['class_name'])

    return redirect(url_for('login')) #User is redirected to the log in page if there is no session data

@student_info_for_teachers.route('/enroll_page_submit', methods=['POST'])
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

    date = datetime.date.today()

    format_code = '%m-%d-%Y'

    date_object = date.strftime(format_code)

    if student_email_fetch:
        flash(f'Student email already exists for {student_email}!')
        cursor.close()
        conn.close()
        return redirect(url_for('student_info_for_teachers.enroll_page'))
    else:

        cursor.execute("INSERT INTO classes (class_name, teacher, student_first_name, student_last_name, student_graduation_year, student_grade, class_creator, student_email, enrollment_date) VALUES (%s,%s,%s,%s,%s,%s, (SELECT email from users WHERE email = %s), %s,%s)", (session['class_name'], session['username'], first_name, last_name, graduation_year, grade, session['email'], student_email, date_object))

        conn.commit()

        cursor.close()
        conn.close()
        flash(f'{first_name} {last_name} has been successfully enrolled.')

        return redirect(request.referrer)

@student_info_for_teachers.route('/delete_student', methods = ['DELETE', 'GET', 'POST'])
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
            return redirect(url_for('student_info_for_teachers.query'))
        elif not delete_last_name:
            flash('Please input student last name to delete.')
            return redirect(url_for('student_info_for_teachers.query'))
        elif not delete_first_name and delete_last_name:
            flash('Please input student names to delete.')
            return redirect(url_for('student_info_for_teachers.query'))

        cursor.execute('SELECT student_first_name FROM classes WHERE student_first_name = %s AND class_creator = %s;', (delete_first_name, session['email']))
        first_name = cursor.fetchone()

        cursor.execute('SELECT student_last_name FROM classes WHERE student_last_name = %s AND class_creator = %s;', (delete_last_name, session['email']))
        last_name = cursor.fetchone()

        cursor.execute('SELECT * FROM classes WHERE student_first_name = %s AND student_last_name = %s AND class_creator = %s;', (delete_first_name, delete_last_name, session['email']))
        full_name = cursor.fetchone()

        if not full_name:
                flash(f'{delete_first_name} {delete_last_name} is not enrolled in the class!')
                return redirect(url_for('student_info_for_teachers.query'))

        for first, last in zip(first_name, last_name):
            flash(f'{first} {last} has been removed from the class!')

        cursor.execute('DELETE FROM classes WHERE student_first_name = %s AND student_last_name = %s AND class_creator = %s;', (delete_first_name, delete_last_name, session['email']))
        conn.commit()

        cursor.execute("SELECT * FROM classes WHERE class_creator = %s;", [session['email']])
        records_2 = cursor.fetchall()

        cursor.close()
        conn.close()

        return redirect(url_for('student_info_for_teachers.query', records_2=records_2, account=account))

    return redirect(url_for('login'))

@student_info_for_teachers.route('/query', methods=['GET'])
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

         return render_template('class_roster.html', records_2=records_2, account=account, username=session['username'], class_name=session['class_name'])

    return redirect(url_for('login'))

@student_info_for_teachers.route('/query_individual_student/<string:id>', methods=['GET'])
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

         session['student_first_name'] = student_id_for_edit['student_first_name']

         session['student_last_name'] = student_id_for_edit['student_last_name']

         cursor.execute("""SELECT
         student_email
         FROM classes 
         WHERE id = {0} AND class_creator = %s;""".format(id), (session['email'],))

         student_email = cursor.fetchone()[0]

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

         cursor.execute('SELECT * FROM assignment_files_student_s3 WHERE student_email = %s ORDER BY upload_date ASC;', (student_email,))
         student_uploads = cursor.fetchall()

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

         return render_template('individual_student.html', student_uploads=student_uploads, student_tardy_count=student_tardy_count, student_absent_count=student_absent_count, student_present_count = student_present_count,
                                search_attendance_query_student_login=search_attendance_query_student_login, class_fetch=class_fetch,
                                student_assignment_scores=student_assignment_scores, student_first_name=student_first_name, student_last_name=student_last_name, records_2=records_2,
                                account=account, username=session['username'], class_name=session['class_name'])

    return redirect(url_for('login'))

@student_info_for_teachers.route('/request_csv_student_grades', methods=['GET'])
def request_csv_student_grades():

    if 'loggedin' in session: # Show user and student information from the db
         conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
         cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

         email = session['email']

         cursor.execute("""SELECT
         *
         FROM classes 
         WHERE id = %s AND class_creator = %s;""", (session['student_id'], session['email'],))

         student_overall_grade = cursor.fetchone()

         cursor.execute("""SELECT
         student_first_name
         FROM classes 
         WHERE id = %s;""", [session['student_id']])

         student_first_name = cursor.fetchone()

         cursor.execute("""SELECT
         student_last_name
         FROM classes 
         WHERE id = %s;""", [session['student_id']])

         student_last_name = cursor.fetchone()

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
         WHERE s.id = %s
         ORDER BY cu.assignment_name ASC;""", [session['student_id']])

         student_assignment_scores = cursor.fetchall()

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
         WHERE s.id = %s;""", [session['student_id']])

         search_attendance_query_student_login = cursor.fetchall()

         headers = ['Score Id', 'First name', 'Last name', 'Assignment name', 'Score']
         csvio = io.StringIO()
         writer = csv.writer(csvio)
         writer.writerow(header for header in headers)
         for row in student_assignment_scores:
             writer.writerow(row)

         s3.put_object(Body=csvio.getvalue(), ContentType='application/vnd.ms-excel', Bucket=BUCKET_NAME, Key=f'{email}-student_grades_for_{student_first_name}{student_last_name}.csv')

         csvio.close()

         csv_url = s3.generate_presigned_url(
                     'get_object',
                     Params={
                         'Bucket': BUCKET_NAME,
                         'Key': f'{email}-student_grades_for_{student_first_name}{student_last_name}.csv'
                     },
                     ExpiresIn=3600
                 )

         csv_message = "Click link to download a csv copy of your gradebook"

         cursor.execute("""SELECT
         student_email
         FROM classes 
         WHERE id = %s AND class_creator = %s;""", (session['student_id'], session['email'],))

         student_email = cursor.fetchone()[0]

         cursor.execute('SELECT * FROM assignment_files_student_s3 WHERE student_email = %s ORDER BY upload_date ASC;', (student_email,))
         student_uploads = cursor.fetchall()

         cursor.execute("SELECT COUNT (attendance_status) FROM attendance WHERE student_id = %s AND attendance_status = 'Tardy';", (session['student_id'],))
         student_tardy_count = cursor.fetchone()

         cursor.execute("SELECT COUNT (attendance_status) FROM attendance WHERE student_id = %s AND attendance_status = 'Absent';", (session['student_id'],))
         student_absent_count = cursor.fetchone()

         cursor.execute("SELECT COUNT (attendance_status) FROM attendance WHERE student_id = %s AND attendance_status = 'Present';", (session['student_id'],))
         student_present_count = cursor.fetchone()

         cursor.close()
         conn.close()

         return render_template('individual_student.html', student_overall_grade=student_overall_grade, student_uploads=student_uploads, student_tardy_count=student_tardy_count, student_absent_count=student_absent_count, student_present_count=student_present_count,
                                student_assignment_scores=student_assignment_scores, student_first_name=student_first_name, student_last_name=student_last_name, search_attendance_query_student_login=search_attendance_query_student_login,
                                username=session['username'], class_name=session['class_name'], csv_url=csv_url, csv_message=csv_message)

    return redirect(url_for('login'))

@student_info_for_teachers.route('/edit_individual_student/<string:id>', methods=['GET'])
def edit_individual_student(id):

    if 'loggedin' in session: # Show user and student information from the db
         conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
         cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

         date = datetime.date.today()

         format_code = '%m-%d-%Y'

         date_object = date.strftime(format_code)

         cursor.execute("""SELECT
         *
         FROM classes 
         WHERE id = {0};""".format(id))

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

         return render_template('edit_student.html', enrollment_date=enrollment_date, student_first_name=student_first_name, student_last_name=student_last_name, graduation_year=graduation_year, username=session['username'], class_name=session['class_name'], date_object=date_object)

    return redirect(url_for('login'))

@student_info_for_teachers.route('/edit_individual_student_first_name', methods=['POST'])
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

         return redirect(url_for('student_info_for_teachers.query'))

    return redirect(url_for('login'))

@student_info_for_teachers.route('/edit_individual_student_last_name', methods=['POST'])
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

         return redirect(url_for('student_info_for_teachers.query'))

    return redirect(url_for('login'))

@student_info_for_teachers.route('/edit_individual_student_graduation_year', methods=['POST'])
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

         return redirect(url_for('student_info_for_teachers.query'))

    return redirect(url_for('login'))

@student_info_for_teachers.route('/edit_individual_student_email', methods=['POST'])
def edit_individual_student_email():

    if 'loggedin' in session: # Show user and student information from the db
         conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
         cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

         update_student_email = request.form.get('update_student_email')

         cursor.execute("""SELECT student_email FROM classes WHERE id = %s;""",
                        (session['student_id'],))

         student_email_original = cursor.fetchone()

         cursor.execute("""SELECT student_first_name FROM classes WHERE id = %s;""",
                        (session['student_id'],))

         student_first_name = cursor.fetchone()

         cursor.execute("""SELECT student_last_name FROM classes WHERE id = %s;""",
                        (session['student_id'],))

         student_last_name = cursor.fetchone()

         cursor.execute("""UPDATE classes 
            SET student_email = %s 
            WHERE id = %s;""", (update_student_email, session['student_id']))

         conn.commit()

         for first_name, last_name, graduation_year in zip(student_first_name, student_last_name, student_email_original):
             flash(f'Student email updated from {student_email_original} to {update_student_email} successfully for {first_name} {last_name}!')

         conn.commit()

         cursor.close()
         conn.close()

         return redirect(url_for('student_info_for_teachers.query'))

    return redirect(url_for('login'))
