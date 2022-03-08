CREATE TABLE users (
	id serial PRIMARY KEY,
	fullname VARCHAR ( 100 ) NOT NULL,
	username VARCHAR ( 50 ) NOT NULL,
	password VARCHAR ( 255 ) NOT NULL,
	email VARCHAR ( 50 ) NOT NULL,
	class VARCHAR (20) NOT NULL,
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
	user_id INT NOT NULL,
	class_creator VARCHAR (50) NOT NULL,
	FOREIGN KEY ("user_id") REFERENCES users("id") ON DELETE CASCADE
	FOREIGN KEY ("class_creator") REFERENCES users("email") ON DELETE CASCADE);
