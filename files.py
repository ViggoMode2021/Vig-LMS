from flask import Flask, request, session, redirect, url_for, render_template, flash, Blueprint
import psycopg2
import psycopg2.extras
import os
import boto3
import datetime
import pytz
from dotenv import load_dotenv, find_dotenv
from werkzeug.utils import secure_filename

# Start environment variables #

load_dotenv(find_dotenv())

s3 = boto3.client('s3',
                    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
                     )

BUCKET_NAME = os.getenv('BUCKET_NAME_VAR') # Set as environment variable

files = Blueprint("files", __name__)

#Database info below:

DB_HOST = os.getenv('DB_HOST')
DB_NAME = os.getenv('DB_NAME')
DB_USER = os.getenv('DB_USER')
DB_PASS = os.getenv('DB_PASS')

@files.route('/upload_file_page', methods=['GET'])
def upload_file_page():
    conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute('SELECT * FROM assignment_files_teacher_s3 WHERE assignment_creator = %s ORDER BY upload_date DESC;', [session['email']])
    assignment_files = cursor.fetchall()
    cursor.execute('SELECT * FROM users WHERE id = %s;', [session['id']])
    account = cursor.fetchone()
    cursor.close()
    conn.close()

    return render_template("file_page.html", assignment_files=assignment_files, account=account, username=session['username'], class_name=session['class_name'])

@files.route('/upload', methods=['POST'])
def upload():# Upload file to S3 bucket from teacher account. Files are accessible from the teacher's account and corresponding student accounts.
    if request.method == 'POST':
        img = request.files['file']
        if img:
                date = datetime.date.today()

                format_code = '%m-%d-%Y'

                date_object = date.strftime(format_code)

                timezone = pytz.timezone('US/Eastern')
                now = datetime.datetime.now(tz=timezone)
                current_time = now.strftime("%I:%M %p")
                email = [session['email']]
                email_save = str(email)
                filename = secure_filename(email_save + "-" + img.filename)
                img.save(filename)
                conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
                cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
                cursor.execute('SELECT * FROM users WHERE id = %s;', [session['id']])
                account = cursor.fetchone()
                cursor.execute("INSERT INTO assignment_files_teacher_s3 (assignment_name, assignment_creator, upload_date, upload_time) VALUES (%s, %s, %s, %s);", (filename, session['email'], date_object, current_time))
                conn.commit()
                cursor.close()
                conn.close()
                class_name = session['class_name']
                s3.upload_file(
                    Bucket=BUCKET_NAME,
                    Filename=filename,
                    Key=filename
                )
                os.remove(filename)
        else:
            flash('No file has been selected to upload. Please click "Choose File button".')
            return redirect(url_for("files.upload_file_page", username=session['username'], class_name=session['class_name']))
        flash(f'{filename} has been uploaded to teacher and student portal for {class_name}.')
        return redirect(url_for("files.upload_file_page", account=account, username=session['username'], class_name=session['class_name']))

@files.route('/upload_assignment', methods=['POST'])
def upload_assignment(): # Upload file to S3 bucket from teacher account. Files are accessible from the teacher's account and corresponding student accounts.
    if request.method == 'POST':
        img_3 = request.files['file_3']
        if img_3:
                date = datetime.date.today()

                format_code = '%m-%d-%Y'

                date_object = date.strftime(format_code)

                timezone = pytz.timezone('US/Eastern')
                now = datetime.datetime.now(tz=timezone)
                current_time = now.strftime("%I:%M %p")
                conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
                cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
                email = [session['email']]
                cursor.execute("""SELECT assignment_name FROM assignments WHERE id = %s;""", (session['assignment_id'],))
                assignment_name = cursor.fetchone()
                for name in assignment_name:
                    filename_3 = secure_filename(name + str(email))
                img_3.save(filename_3)
                cursor.execute("INSERT INTO assignment_files_teacher_s3 (assignment_name, assignment_creator, upload_date, upload_time) VALUES (%s, %s, %s, %s);", (filename_3, session['email'], date_object, current_time))
                conn.commit()
                cursor.close()
                conn.close()
                class_name=session['class_name']
                s3.upload_file(
                    Bucket=BUCKET_NAME,
                    Filename=filename_3,
                    Key=filename_3
                )
                os.remove(filename_3)
        else:
            flash('No file has been selected to upload. Please click "Choose File button".')
            return request.referrer()

        flash(f'{filename_3} has been uploaded to teacher and student portal for {class_name}.')
        return redirect(url_for("assignments.assignment", username=session['username'], class_name=session['class_name']))

@files.route('/download_assignment', methods=['GET'])
def download_assignment(): # Download file from S3 bucket from teacher account. Files are accessible from the teacher's account and corresponding student accounts.
    conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute('SELECT assignment_name FROM assignment_files_teacher_s3 WHERE assignment_name = %s;', [session['assignment_name']])
    assignment_download_name = cursor.fetchone()
    s3.download_file(
        BUCKET_NAME,
        Filename=str(assignment_download_name),
        Key=str(assignment_download_name)
    )
    cursor.close()
    conn.close()

    return redirect(request.referrer)

@files.route('/delete_file/<string:id>', methods=['GET', 'POST'])
def delete_file(id): # Delete file from S3 bucket from teacher account.
    conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute('SELECT assignment_name FROM assignment_files_teacher_s3 WHERE id = {0} AND assignment_creator = %s ORDER BY upload_date ASC;'.format(id), [session['email']])
    assignment_download_name = cursor.fetchone()
    cursor.execute('SELECT * FROM users WHERE id = %s;', [session['id']])
    account = cursor.fetchone()
    for name in assignment_download_name:
        flash(f'{name} deleted!')
    response = s3.delete_objects(
    Bucket=BUCKET_NAME,
    Delete={
        'Objects': [
            {
                'Key': str(assignment_download_name)
            }
        ]
    }
    )
    cursor.execute('DELETE FROM assignment_files_teacher_s3 WHERE id = {0} AND assignment_creator = %s;'.format(id), [session['email']])
    conn.commit()
    cursor.execute('SELECT * FROM assignment_files_teacher_s3 WHERE assignment_creator = %s ORDER BY upload_date DESC;', [session['email']])
    assignment_files = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("file_page.html", response=response, assignment_files=assignment_files, account=account, username=session['username'], class_name=session['class_name'])

@files.route('/download/<string:id>', methods=['GET'])
def download(id): # Download file from S3 bucket from teacher account. Files are accessible from the teacher's account and corresponding student accounts.
    conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute('SELECT assignment_name FROM assignment_files_teacher_s3 WHERE id = {0} AND assignment_creator = %s ORDER BY upload_date DESC;'.format(id), [session['email']])
    assignment_download_name = cursor.fetchone()[0]
    cursor.execute('SELECT * FROM assignment_files_teacher_s3 WHERE assignment_creator = %s;', [session['email']])
    assignment_files = cursor.fetchall()
    cursor.execute('SELECT * FROM users WHERE id = %s;', [session['id']])
    account = cursor.fetchone()
    cursor.close()
    conn.close()
    msg_2 = f"Click link to download {assignment_download_name}"
    response = s3.generate_presigned_url(
        'get_object',
        Params={
            'Bucket': BUCKET_NAME,
            'Key': str(assignment_download_name)
        },
        ExpiresIn=3600
    )
    flash(f"Please check your browser's download folder for the file name {assignment_download_name} after clicking link below.")
    return render_template("file_page.html", assignment_files=assignment_files, msg_2=msg_2, response=response, account=account, username=session['username'], class_name=session['class_name'])

@files.route('/download_uploads_query_individual_student/<string:id>', methods=['GET'])
def download_uploads_query_individual_student(id):
    if 'loggedin' in session:
        conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cursor.execute("""SELECT
             student_email
             FROM classes 
             WHERE id = %s AND class_creator = %s;""", (session['student_id'], session['email']))

        student_email = cursor.fetchone()[0]

        cursor.execute('SELECT file_name FROM assignment_files_student_s3 WHERE id = {0} AND student_email = %s;'.format(id), (student_email,))
        download_uploads_query_ind_student = cursor.fetchone()[0]
        cursor.execute('SELECT * FROM assignment_files_teacher_s3 WHERE assignment_creator = %s;', [session['email']])
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
                    ORDER BY cu.assignment_name ASC;""", (student_email,))

        student_assignments = cursor.fetchall()

        cursor.execute('SELECT * FROM assignment_files_teacher_s3 WHERE assignment_creator = %s ORDER BY upload_date ASC;;', [session['email']])
        student_assignments_originals = cursor.fetchall()

        cursor.execute('SELECT * FROM assignment_files_student_s3 WHERE student_email = %s ORDER BY upload_date ASC;;', (student_email,))
        student_assignments_student_s3 = cursor.fetchall()

        msg_5 = f"Click link to download {download_uploads_query_ind_student}"
        response_4 = s3.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': BUCKET_NAME,
                'Key': str(download_uploads_query_ind_student)
            },
            ExpiresIn=3600
        )
        cursor.execute("""SELECT
         *
         FROM classes 
         WHERE id = %s AND class_creator = %s;""", [session['student_id'], session['email']])

        cursor.execute("""SELECT
        student_email
        FROM classes 
        WHERE id = %s AND class_creator = %s;""", [session['student_id'], session['email']])

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
        WHERE s.id = %s 
        ORDER BY cu.assignment_name ASC;""", [session['student_id']])

        student_assignment_scores = cursor.fetchall()

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

        cursor.execute('SELECT * FROM assignment_files_student_s3 WHERE student_email = %s;', (student_email,))
        student_uploads = cursor.fetchall()

        cursor.execute("SELECT COUNT (attendance_status) FROM attendance WHERE student_id = %s AND attendance_status = 'Tardy';", [session['student_id']])
        student_tardy_count = cursor.fetchone()

        cursor.execute("SELECT COUNT (attendance_status) FROM attendance WHERE student_id = %s AND attendance_status = 'Absent';", [session['student_id']])
        student_absent_count = cursor.fetchone()

        cursor.execute("SELECT COUNT (attendance_status) FROM attendance WHERE student_id = %s AND attendance_status = 'Present';", [session['student_id']])
        student_present_count = cursor.fetchone()

        cursor.execute("SELECT * FROM classes WHERE id = %s;", [session['student_id']])

        class_fetch = cursor.fetchall()

        cursor.close()
        conn.close()

        return render_template('individual_student.html', account=account, username=session['username'], class_name=session['class_name'], class_fetch=class_fetch, msg_5=msg_5, student_present_count=student_present_count,
                               student_tardy_count=student_tardy_count, student_absent_count=student_absent_count, student_uploads=student_uploads,
                               search_attendance_query_student_login=search_attendance_query_student_login, student_assignment_scores=student_assignment_scores,
                               student_first_name=student_first_name, records_2=records_2, student_last_name=student_last_name, response_4=response_4, student_assignments_student_s3=student_assignments_student_s3, student_assignments=student_assignments, student_assignments_originals=student_assignments_originals, assignment_files=assignment_files)

    return redirect(url_for('login'))
