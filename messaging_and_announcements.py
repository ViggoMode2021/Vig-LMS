from flask import request, session, redirect, url_for, render_template, flash, Blueprint
import psycopg2
import psycopg2.extras
import os
from dotenv import load_dotenv, find_dotenv
import datetime
import pytz

# Start environment variables #

load_dotenv(find_dotenv())

dotenv_path = os.path.join(os.path.dirname(__file__), ".env_vig_lms")
load_dotenv(dotenv_path)

#Database info below:

DB_HOST = os.getenv('DB_HOST')
DB_NAME = os.getenv('DB_NAME')
DB_USER = os.getenv('DB_USER')
DB_PASS = os.getenv('DB_PASS')

messaging_and_announcements = Blueprint("messaging_and_announcements", __name__)

@messaging_and_announcements.route('/announcements_page', methods=['GET'])
def announcements_page():

    conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    if 'loggedin' in session:
        date = datetime.date.today()

        format_code = '%m-%d-%Y'

        date_object = date.strftime(format_code)

        timezone = pytz.timezone('US/Eastern')
        now = datetime.datetime.now(tz=timezone)
        current_time = now.strftime("%I:%M %p")
        cursor.execute('SELECT * FROM users WHERE id = %s', [session['id']])
        account = cursor.fetchone()
        cursor.close()
        conn.close()
        return render_template('announcements.html', account=account, date_object=date_object, current_time=current_time, username=session['username'], class_name=session['class_name'])

    return redirect(url_for('login'))

@messaging_and_announcements.route('/announcements_page_submit', methods=['POST', 'GET'])
def announcements_page_submit():

    conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    if 'loggedin' in session:
        date = datetime.date.today()

        format_code = '%m-%d-%Y'

        date_object = date.strftime(format_code)

        timezone = pytz.timezone('US/Eastern')
        now = datetime.datetime.now(tz=timezone)
        current_time = now.strftime("%I:%M %p")
        announcement_box = request.form.get("announcement_box")
        cursor.execute("INSERT INTO announcements(announcement_date, announcement_time, class, announcement, announcement_creator) VALUES (%s,%s,%s,%s,%s);", (date_object, current_time, session['class_name'], announcement_box, session['email']))
        conn.commit()
        cursor.close()
        conn.close()
        flash(f'Announcement recorded for {date_object} at {current_time}. Your announcement was "{announcement_box}"')
        return redirect(request.referrer)

@messaging_and_announcements.route('/view_announcements_by_date', methods=['POST', 'GET'])
def view_announcements_by_date():

    if 'loggedin' in session: # Show user and student information from the db
         conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)

         cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

         cursor.execute('SELECT * FROM users WHERE id = %s', [session['id']])
         account = cursor.fetchone()

         date = datetime.date.today()

         format_code = '%m-%d-%Y'

         date_object = date.strftime(format_code)

         search_announcements_by_date = request.form.get("search_announcements_by_date")

         if '/' in search_announcements_by_date:
            mended_search_announcements_by_date = search_announcements_by_date.replace("/", "-")
            cursor.execute("""SELECT * FROM announcements WHERE announcement_date = %s AND announcement_creator = %s;""", (mended_search_announcements_by_date, session['email']))
            search_announcements_query = cursor.fetchall()
            cursor.close()
            conn.close()
         else:
            search_announcements_by_date = request.form.get("search_announcements_by_date")
            cursor.execute("""SELECT
            * FROM announcements WHERE announcement_date = %s AND announcement_creator = %s;""", (search_announcements_by_date, session['email']))

            search_announcements_query = cursor.fetchall()
            cursor.close()
            conn.close()

         return render_template('announcements_by_date.html', search_announcements_query=search_announcements_query, search_announcements_by_date=search_announcements_by_date, date_object=date_object, account=account, username=session['username'], class_name=session['class_name'])

    return redirect(url_for('login'))

@messaging_and_announcements.route('/delete_announcement/<string:id>', methods=['DELETE', 'GET'])
def delete_announcement(id):

    if 'loggedin' in session: # This removes an attendance record from the db.

        conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        cursor.execute('DELETE FROM announcements WHERE id = {0};'.format(id))
        conn.commit()

        cursor.close()
        conn.close()

        flash('Announcement deleted!')

        return redirect(url_for('messaging_and_announcements.announcements_page'))

    return redirect(url_for('login'))

@messaging_and_announcements.route('/student_direct_message_page/<string:id>', methods=['GET'])
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

@messaging_and_announcements.route('/delete_direct_message_to_student/<string:id>', methods=['DELETE', 'GET'])
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

@messaging_and_announcements.route('/delete_direct_message_from_student/<string:id>', methods = ['DELETE', 'GET'])
def delete_direct_message_from_student(id):

    if 'loggedin' in session: # This removes an attendance record from the db.

        conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        cursor.execute('SELECT message_subject FROM teacher_direct_message WHERE id = {0};'.format(id))
        message_subject = cursor.fetchone()

        cursor.execute('SELECT message FROM teacher_direct_message WHERE id = {0};'.format(id))
        message_body = cursor.fetchone()

        cursor.execute('SELECT date FROM teacher_direct_message WHERE id = {0};'.format(id))
        message_date = cursor.fetchone()

        cursor.execute('SELECT time FROM teacher_direct_message WHERE id = {0};'.format(id))
        message_time = cursor.fetchone()

        cursor.execute('DELETE FROM teacher_direct_message WHERE id = {0};'.format(id))
        conn.commit()

        cursor.close()
        conn.close()

        for subject, body, the_date, the_time in zip(message_subject, message_body, message_date, message_time):
            flash(f'Message deleted! The message subject was "{subject}" and the message was "{body}". The message was'
                  f' originally sent on {the_date} at {the_time}.')

        return redirect(request.referrer)

    return redirect(url_for('login'))

@messaging_and_announcements.route('/view_student_direct_message_page/<string:id>', methods=['GET'])
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

        return render_template('check_student_direct_message_page.html', student_first_name_message=student_first_name_message, student_last_name_message=student_last_name_message, account=account, student_direct_message_id = student_direct_message_id, view_student_direct_messages = view_student_direct_messages, username=session['username'], class_name=session['class_name']
                               )

    return redirect(url_for('login'))

@messaging_and_announcements.route('/view_teacher_direct_message_page/<string:id>', methods=['GET'])
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

        cursor.execute('SELECT student_last_name FROM classes WHERE id = {0} AND class_creator = %s;'.format(id), (session['email'],))
        student_last_name_message = cursor.fetchone()

        cursor.close()
        conn.close()

        return render_template('check_teacher_direct_message_page.html', account=account, student_first_name_message=student_first_name_message,student_last_name_message=student_last_name_message, student_direct_message_id=student_direct_message_id, view_teacher_direct_messages=view_teacher_direct_messages, username=session['username'], class_name=session['class_name']
                               )

    return redirect(url_for('login'))

@messaging_and_announcements.route('/student_direct_message_page_submit', methods=['POST'])
def student_direct_message_page_submit(): #This function routes the logged in user to the page to students

    conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    if 'loggedin' in session:
        date = datetime.date.today()

        format_code = '%m-%d-%Y'

        date_object = date.strftime(format_code)

        timezone = pytz.timezone('US/Eastern')
        now = datetime.datetime.now(tz=timezone)
        current_time = now.strftime("%I:%M %p")
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
                  f'Your subject was: "{message_subject}" and the \n'
                  f' message was "{student_direct_message_box}".')

        return redirect(request.referrer)

    return redirect(url_for('login'))
