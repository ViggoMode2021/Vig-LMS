CREATE TABLE users(
	id serial PRIMARY KEY,
	fullname VARCHAR ( 100 ) NOT NULL,
	username VARCHAR ( 50 ) NOT NULL,
	password VARCHAR ( 255 ) NOT NULL,
	email VARCHAR ( 50 ) NOT NULL,
	class VARCHAR (20) NOT NULL,
	secret_question VARCHAR ( 50 ) NOT NULL,
	UNIQUE (email)
);

CREATE TABLE classes(
	id SERIAL PRIMARY KEY,
	class_name TEXT,
	teacher TEXT,
	student_first_name TEXT,
	student_last_name TEXT,
	student_graduation_year INT,
	student_grade INT,
	class_creator VARCHAR (50) NOT NULL,
	FOREIGN KEY ("class_creator") REFERENCES users("email") ON DELETE CASCADE);

CREATE TABLE assignments(
    id SERIAL PRIMARY KEY,
    assignment_name TEXT NOT NULL,
    category TEXT NOT NULL,
    due_date TEXT NOT NULL,
    overall_points INT NOT NULL,
	assignment_creator VARCHAR (50) NOT NULL,
	FOREIGN KEY ("assignment_creator") REFERENCES users("email") ON DELETE CASCADE);

CREATE TABLE assignment_results(
    id SERIAL PRIMARY KEY,
    score REAL NOT NULL,
    student_id INT NOT NULL,
    assignment_id INT NOT NULL,
    FOREIGN KEY ("student_id") REFERENCES classes("id") ON DELETE CASCADE,
    FOREIGN KEY ("assignment_id") REFERENCES assignments("id") ON DELETE CASCADE);

CREATE TABLE attendance(
id SERIAL PRIMARY KEY,
month TEXT NOT NULL,
day INT NOT NULL,
attendance_status TEXT NOT NULL,
student_id INT NOT NULL,
teacher_id TEXT NOT NULL,
FOREIGN KEY ("student_id") REFERENCES classes("id") ON DELETE CASCADE,
FOREIGN KEY ("teacher_id") REFERENCES users("email") ON DELETE CASCADE);

CREATE TABLE student_accounts(
	id SERIAL PRIMARY KEY,
	student_first_name TEXT NOT NULL,
	student_last_name TEXT NOT NULL,
	password VARCHAR (250) NOT NULL,
	class TEXT NOT NULL,
    secret_question VARCHAR (30) NOT NULL
);
