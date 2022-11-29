from flask import request, session, redirect, url_for, render_template, flash, Blueprint
import psycopg2
import psycopg2.extras
import os
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

dotenv_path = os.path.join(os.path.dirname(__file__), ".env_vig_lms")

#Database info below:

DB_HOST = os.getenv('DB_HOST')
DB_NAME = os.getenv('DB_NAME')
DB_USER = os.getenv('DB_USER')
DB_PASS = os.getenv('DB_PASS')

assignments = Blueprint("assignments", __name__)

@assignments.route('/update_individual_assignment_grade/<string:id>', methods=['POST'])
def update_individual_assignment_grade(id):

    if 'loggedin' in session: # Show user and student information from the db
         conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
         cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

         update_assignment_grade = request.form.get('update_assignment_grade')

         cursor.execute("""SELECT score FROM assignment_results WHERE id = {0};""".format(id))
         original_score = cursor.fetchone()

         cursor.execute("""SELECT assignment_id FROM assignment_results WHERE id = {0};""".format(id))
         assignment_id = cursor.fetchone()[0]

         cursor.execute("""SELECT assignment_name FROM assignments WHERE id = %s;""", (assignment_id,))
         assignment_name = cursor.fetchone()

         cursor.execute("""UPDATE assignment_results 
            SET score = %s 
            WHERE id = %s;""".format(id), (update_assignment_grade, id))

         cursor.execute("""SELECT student_first_name FROM classes WHERE id = %s""", [session['student_id']],)
         first_name = cursor.fetchone()

         cursor.execute("""SELECT student_first_name FROM classes WHERE id = %s""", [session['student_id']],)
         last_name = cursor.fetchone()

         cursor.execute("""UPDATE classes 
                        SET student_grade = (
                        SELECT ROUND(AVG(score))
                        FROM assignment_results WHERE student_id = %s)
                        WHERE id = %s;""", (session['student_id'], session['student_id']))

         conn.commit()

         for first, last, original, assignment in zip(first_name,last_name, original_score, assignment_name):
            flash(f'Assignment grade for {first} {last} updated successfully from {original} to {update_assignment_grade} for'
                  f' assignment titled "{assignment}".')

         cursor.close()
         conn.close()

         return redirect(request.referrer)

    return redirect(url_for('login'))

@assignments.route('/delete_assignment_score_query_individual_student/<string:id>', methods = ['DELETE', 'GET'])
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

@assignments.route('/assignment', methods=['GET', 'POST'])
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

        return render_template('assignment_list.html', account=account, assignments=assignments, username=session['username'], class_name=session['class_name'])

    return redirect(url_for('login'))

@assignments.route('/new_assignment', methods=['POST'])
def new_assignment():

    if 'loggedin' in session: # This creates a new assignment
        conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        assignment_name = request.form.get("assignment name")
        category = request.form.get("category")
        due_date = request.form.get("due date")
        overall_points = request.form.get("max points")
        description = request.form.get("description")

        cursor.execute("INSERT INTO assignments (assignment_name, category, due_date, overall_points, assignment_creator, description) "
                       "VALUES (%s, %s, %s, %s, (SELECT email from users WHERE email = %s), %s)", (assignment_name, category,
                        due_date, overall_points, session['email'], description))

        conn.commit()

        cursor.close()
        conn.close()

        return redirect(url_for('assignments.assignment'))

    return redirect(url_for('login'))

@assignments.route('/update_assignment_name/<string:id>', methods=['POST', 'GET'])
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

@assignments.route('/update_assignment_due_date/<string:id>', methods=['POST', 'GET'])
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

@assignments.route('/delete_assignment/<string:id>', methods=['DELETE', 'POST', 'GET'])
def delete_assignment(id):

    if 'loggedin' in session:

        conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        cursor.execute('SELECT * FROM users WHERE id = %s;', [session['id']])
        account = cursor.fetchone()

        delete_assignment_name = request.form.get('delete_assignment_name')

        cursor.execute('DELETE FROM assignments WHERE id = %s;', (id,))

        conn.commit()

        flash('Assignment removed successfully.')

        cursor.execute("SELECT * FROM assignments WHERE assignment_creator = %s;", [session['email']])

        assignments = cursor.fetchall()

        cursor.close()
        conn.close()

        return redirect(url_for('assignments.assignment', account=account, assignments=assignments))

    return redirect(url_for('login'))

@assignments.route('/delete_assignment_score/<string:id>', methods = ['DELETE', 'GET'])
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

        return redirect(url_for('assignments.view_assignment_scores', account=account, assignments=assignments, username=session['username'], class_name=session['class_name']))

    return redirect(url_for('login'))
