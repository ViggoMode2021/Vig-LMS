from flask import request, session, redirect, url_for, render_template, flash, Blueprint
import psycopg2
import psycopg2.extras
import os
from dotenv import load_dotenv, find_dotenv
import datetime
import pytz

load_dotenv(find_dotenv())

#Database info below:

DB_HOST = os.getenv('DB_HOST')
DB_NAME = os.getenv('DB_NAME')
DB_USER = os.getenv('DB_USER')
DB_PASS = os.getenv('DB_PASS')

attendance = Blueprint("attendance", __name__)

@attendance.route('/take_attendance_page', methods=['GET'])
def take_attendance_page():

    if 'loggedin' in session: # Show user and student information from the db
         conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)

         cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

         date = datetime.date.today()

         format_code = '%m-%d-%Y'

         date_object = date.strftime(format_code)

         attendance_date_object = date.strftime(format_code)

         cursor.execute('SELECT * FROM users WHERE id = %s', [session['id']])
         account = cursor.fetchone()

         cursor.execute("SELECT * FROM classes WHERE class_creator = %s;", [session['email']])

         take_attendance_query = cursor.fetchall()

         cursor.close()
         conn.close()

         return render_template('attendance_page.html', attendance_date_object=attendance_date_object, take_attendance_query=take_attendance_query, date_object=date_object, account=account, username=session['username'], class_name=session['class_name'])

    return redirect(url_for('login'))

@attendance.route('/take_attendance/<string:id>', methods=['POST'])
def take_attendance(id):

    if 'loggedin' in session: # Show user and student information from the db
         conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)

         cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

         date = datetime.date.today()

         format_code = '%m-%d-%Y'

         date_object = date.strftime(format_code)

         attendance_date_object = date.strftime(format_code)

         cursor.execute('SELECT * FROM users WHERE id = %s;', [session['id']])
         account = cursor.fetchone()

         cursor.execute('SELECT student_first_name FROM classes WHERE id = %s;', (id,))
         first_name = cursor.fetchone()

         cursor.execute('SELECT student_last_name FROM classes WHERE id = %s;', (id,))
         last_name = cursor.fetchone()

         attendance = request.form.get("attendance")

         cursor.execute('INSERT INTO attendance (date, attendance_status, student_id) VALUES (%s, %s, %s);'.format(id),
                        (attendance_date_object, attendance, id))

         conn.commit()

         for first, last in zip(first_name, last_name):
            flash(f'Attendance recorded for {first} {last} as {attendance} on {date_object}!')

         cursor.execute("SELECT * FROM classes WHERE class_creator = %s;", [session['email']])

         take_attendance_query = cursor.fetchall()

         cursor.close()
         conn.close()

         return redirect(url_for('attendance.take_attendance_page', attendance_date_object=attendance_date_object,take_attendance_query=take_attendance_query, date_object=date_object, account=account, username=session['username'], class_name=session['class_name']))

    return redirect(url_for('login'))

@attendance.route('/view_attendance_for_today', methods=['GET'])
def view_attendance_for_today():

    if 'loggedin' in session: # Show user and student information from the db
         conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)

         cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

         cursor.execute('SELECT * FROM users WHERE id = %s;', [session['id']])
         account = cursor.fetchone()

         date = datetime.date.today()

         format_code = '%m-%d-%Y'

         date_object = date.strftime(format_code)

         attendance_date_object = date.strftime(format_code)

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
            WHERE a.date = %s AND s.class_creator = %s;""", (attendance_date_object, session['email']))

         search_attendance_query = cursor.fetchall()

         cursor.close()
         conn.close()

         return render_template('view_todays_attendance.html', attendance_date_object=attendance_date_object,search_attendance_query=search_attendance_query, date_object=date_object, account=account, username=session['username'], class_name=session['class_name'])

    return redirect(url_for('login'))

@attendance.route('/search_attendance_by_date', methods=['POST', 'GET'])
def search_attendance_by_date():

    if 'loggedin' in session: # Show user and student information from the db
         conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)

         cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

         cursor.execute('SELECT * FROM users WHERE id = %s;', [session['id']])
         account = cursor.fetchone()

         date = datetime.date.today()

         format_code = '%m-%d-%Y'

         date_object = date.strftime(format_code)

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
             return redirect(url_for('attendance.take_attendance_page'))

         cursor.close()
         conn.close()

         return render_template('attendance_by_date.html', search_attendance_query=search_attendance_query, date_object=date_object, account=account, username=session['username'], class_name=session['class_name'],
                                search_attendance_by_date=search_attendance_by_date)

    return redirect(url_for('login'))

@attendance.route('/search_attendance_by_student', methods=['POST', 'GET'])
def search_attendance_by_student():

    if 'loggedin' in session: # Show user and student information from the db
         conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)

         cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

         cursor.execute('SELECT * FROM users WHERE id = %s;', [session['id']])
         account = cursor.fetchone()

         search_attendance_by_student= request.form.get('search_attendance_by_student')

         date = datetime.date.today()

         format_code = '%m-%d-%Y'

         date_object = date.strftime(format_code)

         timezone = pytz.timezone('US/Eastern')

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

         cursor.execute("SELECT student_first_name FROM classes WHERE id = %s;", (search_attendance_by_student,))
         student_first_name = cursor.fetchone()

         cursor.execute("SELECT student_last_name FROM classes WHERE id = %s;", (search_attendance_by_student,))
         student_last_name = cursor.fetchone()

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
             return redirect(url_for('attendance.take_attendance_page'))

         cursor.close()
         conn.close()

         return render_template('attendance_by_student.html', search_attendance_query_student=search_attendance_query_student, date_object=date_object, account=account, username=session['username'], class_name=session['class_name'],
                                search_attendance_by_date=search_attendance_by_date, student_first_name=student_first_name, student_last_name=student_last_name, student_tardy_count=student_tardy_count, student_present_count=student_present_count, student_absent_count=student_absent_count)

    return redirect(url_for('login'))

@attendance.route('/delete_attendance_record/<string:id>', methods = ['DELETE', 'GET'])
def delete_attendance_record(id):

    if 'loggedin' in session: # This removes an attendance record from the db.

        conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        cursor.execute('DELETE FROM attendance WHERE id = {0};'.format(id))
        conn.commit()

        cursor.close()
        conn.close()

        return redirect(url_for('attendance.take_attendance_page'))

    return redirect(url_for('login'))

@attendance.route('/update_attendance_record/<string:id>', methods = ['POST', 'GET'])
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

        return redirect(request.referrer)

    return redirect(url_for('login'))

@attendance.route('/update_attendance_record_query_individual_student/<string:id>', methods = ['POST', 'GET'])
def update_attendance_record_query_individual_student(id):

    if 'loggedin' in session: # This updates an attendance record from the db.

        conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        attendance = request.form.get('attendance')

        cursor.execute("""SELECT attendance_status FROM attendance WHERE id = %s;""", (id,))
        attendance_status = cursor.fetchone()

        cursor.execute("""SELECT date FROM attendance WHERE id = %s;""", (id,))
        attendance_date = cursor.fetchone()

        cursor.execute("""UPDATE attendance 
            SET attendance_status = %s 
            WHERE id = %s;""", (attendance, id))

        conn.commit()

        for attendance_stat, date in zip(attendance_status, attendance_date):
            flash(f'Attendance updated successfully from {attendance_stat} to {attendance} on {date}!')

        cursor.close()
        conn.close()

        return redirect(request.referrer)

    return redirect(url_for('login'))

@attendance.route('/delete_attendance_record_query_individual_student/<string:id>', methods = ['DELETE', 'GET'])
def delete_attendance_record_query_individual_student(id):

    if 'loggedin' in session: # This removes an attendance record from the db.

        conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        cursor.execute('DELETE FROM attendance WHERE id = {0};'.format(id))
        conn.commit()

        cursor.close()
        conn.close()

        return redirect(request.referrer)

    return redirect(url_for('login'))
