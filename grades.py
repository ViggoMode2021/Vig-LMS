from flask import request, session, redirect, url_for, render_template, flash, Blueprint
import psycopg2
import psycopg2.extras
import os
from dotenv import load_dotenv, find_dotenv
import csv
import io
import boto3

s3 = boto3.client('s3',
                    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
                     )

BUCKET_NAME = os.getenv('BUCKET_NAME_VAR')

# Start environment variables #

load_dotenv(find_dotenv())

#Database info below:

DB_HOST = os.getenv('DB_HOST')
DB_NAME = os.getenv('DB_NAME')
DB_USER = os.getenv('DB_USER')
DB_PASS = os.getenv('DB_PASS')

grades = Blueprint("grades", __name__)

@grades.route('/grade_ASC', methods=['GET'])
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

        return render_template('class_roster.html', records_2=records_2, account=account, username=session['username'], class_name=session['class_name'])

    return redirect(url_for('login'))

@grades.route('/request_csv', methods=['GET'])
def request_csv():

    if 'loggedin' in session: # This orders the students by grade (lowest - highest)

        conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        cursor.execute('SELECT * FROM users WHERE id = %s;', [session['id']])
        account = cursor.fetchone()

        cursor.execute('SELECT email FROM users WHERE id = %s;', [session['id']])
        email = cursor.fetchone()[0]

        cursor.execute("SELECT * FROM classes WHERE class_creator = %s ORDER BY student_grade ASC;", [session['email']])
        records_2 = cursor.fetchall()

        headers = ['id', 'class', 'teacher', 'first name', 'last name', 'graduation year', 'grade', 'email']
        csvio = io.StringIO()
        writer = csv.writer(csvio)
        writer.writerow(header for header in headers)
        for row in records_2:
            writer.writerow(row)

        s3.put_object(Body=csvio.getvalue(), ContentType='application/vnd.ms-excel', Bucket=BUCKET_NAME, Key=f'{email}-class_grade_ascending.csv')

        csvio.close()

        csv_url = s3.generate_presigned_url(
                    'get_object',
                    Params={
                        'Bucket': BUCKET_NAME,
                        'Key': f'{email}-class_grade_ascending.csv'
                    },
                    ExpiresIn=3600
                )

        csv_message = "Click link to download a csv copy of your gradebook"

        cursor.close()
        conn.close()

        return render_template('class_roster.html', records_2=records_2, account=account, username=session['username'], class_name=session['class_name'], csv_url=csv_url, csv_message=csv_message)

    return redirect(url_for('login'))

@grades.route('/grade_DESC', methods=['GET'])
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

        return render_template('class_roster.html', records_2=records_2, account=account, username=session['username'], class_name=session['class_name'])

    return redirect(url_for('login'))

@grades.route('/update_grade/<id>', methods=['PATCH', 'GET', 'POST'])
def update_grade(id):

    if 'loggedin' in session: # This updates the student grade via user input.

        conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        cursor.execute('SELECT * FROM users WHERE id = %s;', [session['id']])
        account = cursor.fetchone()

        updated_grade = request.form.get("update grade")

        if not updated_grade:
            flash("Please enter a new grade if you wish to update the student's grade.")
            cursor.close()
            conn.close()
            return redirect(url_for('student_info_for_teachers.query'))
        if updated_grade.isalpha():
            flash("Please enter a new grade number if you wish to update the student's grade.")
            cursor.close()
            conn.close()
            return redirect(url_for('student_info_for_teachers.query'))
        else:
            cursor.execute('SELECT student_first_name FROM classes WHERE id = %s;', (id,))
            student_first_name = cursor.fetchone()
            cursor.execute('SELECT student_last_name FROM classes WHERE id = %s;', (id,))
            student_last_name = cursor.fetchone()
            cursor.execute('SELECT student_grade FROM classes WHERE id = %s;', (id,))
            student_grade = cursor.fetchone()

            cursor.execute("""UPDATE classes 
            SET student_grade = %s 
            WHERE id = %s;""", (updated_grade, id))

            for first_name, last_name, grade in zip(student_first_name, student_last_name, student_grade):
                flash(f"Grade updated from {grade} to {updated_grade} for {first_name} {last_name}!")

            conn.commit()

            cursor.execute("SELECT * FROM classes WHERE class_creator = %s;", [session['email']])
            records_2 = cursor.fetchall()

            cursor.close()
            conn.close()
            return redirect(url_for('student_info_for_teachers.query', records_2=records_2, account=account, username=session['username'], class_name=session['class_name']))

    return redirect(url_for('login'))

@grades.route('/edit_assignment_grade/<string:id>', methods=['GET'])
def edit_assignment_grade(id):

    if 'loggedin' in session: # This routes the user to the edit assignment grade page.

        conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        cursor.execute('SELECT * FROM users WHERE id = %s', [session['id']])
        account = cursor.fetchone()

        cur = conn.cursor()

        cur.execute("SELECT assignment_name FROM assignments WHERE id = {0} AND assignment_creator = %s;".format(id), (session['email'],))
        records_2 = cur.fetchall()

        cur.execute('SELECT * FROM classes WHERE class_creator = %s ORDER BY id ASC;', [session['email']])
        records_3 = cur.fetchall()

        cur.execute("SELECT id FROM assignments WHERE id = {0} AND assignment_creator = %s;".format(id), (session['email'],))
        records_4 = cur.fetchone()

        cur.execute("SELECT description FROM assignments WHERE id = {0} AND assignment_creator = %s;".format(id), (session['email'],))
        description = cur.fetchall()

        session['assignment_id'] = records_4

        cur.execute("SELECT due_date FROM assignments WHERE id = {0} AND assignment_creator = %s;".format(id), (session['email'],))
        due_date = cur.fetchall()

        cur.execute("SELECT category FROM assignments WHERE id = {0} AND assignment_creator = %s;".format(id), (session['email'],))
        category = cur.fetchall()

        cur.execute("SELECT * FROM assignments WHERE id = {0} AND assignment_creator = %s;".format(id), (session['email'],))
        records_5 = cur.fetchone()
        session['assignment_id'] = records_5[0]
        session['assignment_name'] = records_5[1]

        assignment_id = records_4[0]

        cur.execute("""SELECT
        ar.student_id AS student_id,
        cl.student_first_name,
        cl.student_last_name,
        ar.score
        FROM classes cl
        INNER JOIN assignment_results AS ar
        ON ar.student_id = cl.id
        WHERE assignment_id = %s
        ORDER BY ar.student_id ASC;""", (assignment_id,))

        scores = cur.fetchall()

        cursor.close()
        conn.close()

        return render_template('edit_assignment_score.html', due_date=due_date, category=category, account=account, records_2=records_2, records_3=records_3, records_4=records_4, username=session['username'], class_name=session['class_name'], scores=scores,
                               description=description)

    return redirect(url_for('login'))

@grades.route('/edit_assignment_grade_2/<id>', methods=['POST', 'GET'])
def edit_assignment_grade_2(id):

    if 'loggedin' in session:

        conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        grade_assignment = request.form.get("grade_assignment")
        student_id = request.form.get("student_id")

        cur = conn.cursor()

        conn.commit()

        cur.execute("""SELECT id FROM classes WHERE id = %s;""", (id,))
        student_id_query = cur.fetchone()

        cur.execute("""SELECT * FROM assignment_results WHERE student_id = %s AND assignment_id = %s;""", (id, session['assignment_id']))
        result_check = cur.fetchall()

        if not grade_assignment:
            flash('Please input the updated grade here.')
            cursor.close()
            conn.close()
            return redirect(url_for('assignments.assignment'))
        if result_check:
            cur.execute("""UPDATE assignment_results SET
            score = %s WHERE student_id = %s AND assignment_id = %s;
            """, (grade_assignment, student_id_query, session['assignment_id']))

            conn.commit()
            cursor.close()
            conn.close()
            return redirect(request.referrer)
        else:
            cur.execute("""INSERT INTO assignment_results
            (score, student_id, assignment_id) VALUES (%s, %s, %s) 
            """, (grade_assignment, student_id_query, session['assignment_id']))

            conn.commit()

            cursor.execute("""SELECT ROUND(AVG(score)) FROM assignment_results WHERE student_id = %s""", (student_id_query,))

            updated_grade_average = cursor.fetchone()[0]

            cursor.execute("""UPDATE classes 
                            SET student_grade = %s
                            WHERE id = %s;""", (updated_grade_average, student_id_query))

            conn.commit()

            flash('Assignment grade successfully updated!')

            cursor.close()
            conn.close()

            return redirect(request.referrer)

    return redirect(url_for('login'))

@grades.route('/view_assignment_scores', methods=['GET'])
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

        return render_template('assignment_scores.html', account=account, assignment_scores=assignment_scores, username=session['username'], class_name=session['class_name'])

    return redirect(url_for('login'))
