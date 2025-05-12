from flask import Flask, abort, render_template, request, redirect, url_for, session, jsonify, send_from_directory, flash
from flask_cors import CORS
from flask_mysqldb import MySQL
from werkzeug.utils import secure_filename
import os
import mysql.connector
import MySQLdb.cursors
from flask import g
import MySQLdb
from datetime import datetime
import random
from flask import send_from_directory
import MySQLdb.cursors
import pymysql.cursors
from datetime import datetime, date
import re



app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'  
app.config['ALLOWED_EXTENSIONS'] = {'pdf'}
CORS(app)

# Secret Key for Session
app.secret_key = 'your_secret_key'

# MySQL Configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'Root12345'  # Replace with your password
app.config['MYSQL_DB'] = 'project'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

# Initialize MySQL
mysql = MySQL(app)

def get_db():
    conn = MySQLdb.connect(
        host="localhost",
        user="root",
        password="Root12345",
        database="project",
        charset="utf8mb4",
        cursorclass=MySQLdb.cursors.DictCursor
    )
    cursor = conn.cursor()  # 🔴 Create a cursor
    return conn, cursor 

@app.teardown_appcontext
def close_db(exception):
    db = g.pop('db', None)
    if db is not None:
        db.close()


def get_db_connection():
    try:
        conn = MySQLdb.connect(
            host="localhost",
            user="root",
            password="Root12345",
            database="project"
        )
        return conn
    except MySQLdb.Error as e:
        print("Database connection error:", e)
        return None



UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# ✅ Ensure base "uploads" directory exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# ✅ Ensure "uploads/resume" folder exists
RESUME_FOLDER = os.path.join(UPLOAD_FOLDER, "resume")
if not os.path.exists(RESUME_FOLDER):
    os.makedirs(RESUME_FOLDER)

# ================= ROUTES =================

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    role = session.get('role', '').lower()
    if role == 'student':
        return redirect(url_for('student_home'))
    elif role == 'admin':
        return redirect(url_for('admin_home'))
    elif role == 'company':
        return redirect(url_for('company_home'))
    return redirect(url_for('index'))

@app.route('/student_home')
def student_home():
    if session.get('role', '').lower() == 'student':
        return render_template('student_home.html')
    return redirect(url_for('index'))

@app.route('/admin_home')
def admin_home():
    if session.get('role', '').lower() == 'admin':
        return render_template('admin_home.html')
    return redirect(url_for('index'))

@app.route('/company_home')
def company_home():
    if session.get('role', '').lower() == 'company':
        return render_template('company_home.html')
    return redirect(url_for('index'))

# ================= LOGIN =================

@app.route('/login', methods=['GET','POST'])
def login():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"message": "Invalid request format"}), 400

    username = data.get('username', '').strip().lower()
    password = data.get('password', '').strip()
    role = data.get('role', '').strip().lower()  # Get role

    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM users WHERE LOWER(username) = %s", (username,))
    user = cur.fetchone()

    if not user:
        return jsonify({"message": "Invalid credentials"}), 401

    if password == user['password']:  # Use hashing in production
        if user['role'].lower() != role:
            return jsonify({"message": "Unauthorized role"}), 403  # Check role

        session.clear()
        session['user_id'] = user['id']
        session['username'] = user['username']
        session['role'] = user['role'].lower()

        return jsonify({"message": "Login successful"}), 200
    else:
        return jsonify({"message": "Invalid credentials"}), 401




# ================= SIGNUP =================

@app.route('/signup', methods=['POST'])
def signup():
    data = request.json
    username = data.get('username', '').strip().lower()
    password = data.get('password', '').strip()
    role = data.get('role', '').strip()

    if not username or not password or not role:
        return jsonify({"message": "All fields are required"}), 400

    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM users WHERE LOWER(username) = %s", (username,))
    existing_user = cur.fetchone()

    if existing_user:
        return jsonify({"message": "Username already exists. Please choose another."}), 409

    cur.execute("INSERT INTO users (username, password, role, created_at) VALUES (%s, %s, %s, NOW())", 
                (username, password, role))
    mysql.connection.commit()
    cur.close()

    return jsonify({"message": "Signup successful"}), 201

# ================= FILE UPLOAD =================

ALLOWED_EXTENSIONS = {'pdf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        return jsonify({"message": "No file part"}), 400
    
    file = request.files['file']
    file_type = request.form.get('file_type')  # New parameter to distinguish resumes from study materials
    department = request.form.get('department')

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)

        if file_type == "resume":
            # ✅ Save resumes in "uploads/resume"
            resume_folder = os.path.join(app.config['UPLOAD_FOLDER'], "resume")
            os.makedirs(resume_folder, exist_ok=True)
            file_path = os.path.join(resume_folder, filename)

            # ✅ Update student_profiles table instead of study_materials
            cur = mysql.connection.cursor()
            user_id = session.get('user_id')  # Ensure user is logged in
            cur.execute("UPDATE student_profiles SET resume=%s WHERE user_id=%s", 
                        (f"uploads/resume/{filename}", user_id))
            mysql.connection.commit()
            cur.close()

        elif file_type == "study_material" and department:
            # ✅ Save study materials inside "uploads/study_materials/{department}"
            department_path = os.path.join(app.config['UPLOAD_FOLDER'], "study_materials", department)
            os.makedirs(department_path, exist_ok=True)
            file_path = os.path.join(department_path, filename)

            # ✅ Insert into study_materials table
            cur = mysql.connection.cursor()
            cur.execute("INSERT INTO study_materials (department, filename) VALUES (%s, %s)", 
                        (department, filename))
            mysql.connection.commit()
            cur.close()
        
        else:
            return jsonify({"message": "Invalid file type or missing department"}), 400

        # ✅ Save the file after determining correct location
        file.save(file_path)

        return jsonify({"message": f'File "{filename}" uploaded successfully'}), 200
    
    return jsonify({"message": "Invalid file type or missing data"}), 400


# ================= LOGOUT =================

@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('role', None)
    return redirect(url_for('index'))

# ================= STATIC FILES =================

@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename)

# ================= TEST LOGO =================

@app.route('/test-logo')
def test_logo():
    return f"<img src='{url_for('static', filename='images/logo_sg.png')}' alt='Test Logo'>"

# ================= VIEW PROFILE =================

@app.route('/view_profile')
def view_profile():
    if 'user_id' not in session:
        return redirect(url_for('index'))  # Redirect if not logged in

    user_id = session['user_id']
    
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT s.name, s.email, s.phone, s.birthday, s.gender, 
               s.address, s.faculty_advisor, s.CGPA, d.name AS department_name
        FROM student_profiles s
        LEFT JOIN departments d ON s.department_id = d.id
        WHERE s.user_id = %s
    """, (user_id,))
    
    profile = cur.fetchone()  # Fetch the result correctly
    cur.close()

    if profile:
        return render_template('profile.html', profile=profile)
    else:
        flash("No profile found. Please create one.", "warning")
        return redirect(url_for('create_profile'))  # Redirect to Create Profile if none exists


@app.route('/update_profile', methods=['POST'])
def update_profile():
    if 'user_id' not in session:
        return redirect(url_for('index'))  # Redirect if not logged in

    user_id = session['user_id']
    email = request.form['email']
    phone = request.form['phone']
    birthday = request.form['birthday']
    gender = request.form['gender']
    address = request.form['address']
    faculty_advisor = request.form['faculty_advisor']
    CGPA = request.form['CGPA']

    try:
        cur = mysql.connection.cursor()
        cur.execute("""
            UPDATE student_profiles 
            SET email = %s, phone = %s, birthday = %s, gender = %s, 
                address = %s, faculty_advisor = %s, CGPA = %s
            WHERE user_id = %s
        """, (email, phone, birthday, gender, address, faculty_advisor, CGPA, user_id))
        mysql.connection.commit()
        cur.close()
        flash("Profile updated successfully!", "success")
    except Exception as e:
        flash("Error updating profile: " + str(e), "danger")

    return redirect(url_for('view_profile'))

@app.route('/create_profile', methods=['GET', 'POST'])
def create_profile():
    if 'user_id' not in session:
        return redirect(url_for('index'))

    user_id = session['user_id']

    # Fetch department list for dropdown
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("SELECT id, name FROM departments")
    departments = cur.fetchall()
    cur.close()

    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        department_id = request.form['department_id']
        faculty_advisor = request.form['faculty_advisor']
        birthday = request.form['birthday']
        gender = request.form['gender']
        address = request.form['address']
        cgpa = request.form['cgpa']

        # Validate email
        if not email.endswith("@saintgits.org"):
            flash("Email must be a valid @saintgits.org address.", "danger")
            return render_template("create_profile.html", departments=departments)

        # Validate phone number (exactly 10 digits)
        if not re.match(r"^\d{10}$", phone):
            flash("Phone number must be exactly 10 digits.", "danger")
            return render_template("create_profile.html", departments=departments)

        # Validate faculty advisor (only letters and spaces)
        if not re.match(r"^[A-Za-z\s]+$", faculty_advisor):
            flash("Faculty advisor name must contain only letters.", "danger")
            return render_template("create_profile.html", departments=departments)

        # Validate CGPA (between 0 and 10)
        try:
            cgpa_val = float(cgpa)
            if not (0 <= cgpa_val <= 10):
                flash("CGPA must be between 0 and 10.", "danger")
                return render_template("create_profile.html", departments=departments)
        except ValueError:
            flash("CGPA must be a valid number.", "danger")
            return render_template("create_profile.html", departments=departments)

        # Validate age (should be at least 18 years old)
        try:
            dob = datetime.strptime(birthday, "%Y-%m-%d").date()
            today = date.today()
            age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
            if age < 18:
                flash("You must be at least 18 years old.", "danger")
                return render_template("create_profile.html", departments=departments)
        except ValueError:
            flash("Invalid date format for birthday.", "danger")
            return render_template("create_profile.html", departments=departments)

        # All validations passed – insert into DB
        cur = mysql.connection.cursor()
        cur.execute('''
            INSERT INTO student_profiles (user_id, name, email, phone, department_id, faculty_advisor, birthday, gender, address, CGPA)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (user_id, name, email, phone, department_id, faculty_advisor, birthday, gender, address, cgpa))
        mysql.connection.commit()
        cur.close()

        flash("Profile created successfully!", "success")
        return redirect(url_for('view_profile'))

    return render_template('create_profile.html', departments=departments)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.route('/uploads/resume/<filename>')
def view_resume(filename):
    resume_folder = os.path.join(app.root_path, "uploads", "resume")  # Absolute path
    file_path = os.path.join(resume_folder, filename)

    print(f"Trying to access: {file_path}")  # Debugging print

    if not os.path.exists(file_path):
        return abort(404, description="File not found")

    return send_from_directory(resume_folder, filename)

@app.route('/upload_resume', methods=['GET', 'POST'])
def upload_resume():
    if 'user_id' not in session:
        return redirect(url_for('index'))  # Redirect if not logged in

    if request.method == 'POST':
        if 'resume' not in request.files:
            flash('No file part', 'danger')
            return redirect(request.url)

        file = request.files['resume']

        if file.filename == '':
            flash('No selected file', 'danger')
            return redirect(request.url)

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)

            # ✅ Ensure resume is saved in "uploads/resume"
            resume_folder = os.path.join(app.config['UPLOAD_FOLDER'], "resume")

            # ✅ Fix: Prevent saving in "study_materials"
            if "study_materials" in resume_folder:
                resume_folder = os.path.join("uploads", "resume")

            # ✅ Ensure folder exists
            os.makedirs(resume_folder, exist_ok=True)

            # ✅ Save file correctly inside "uploads/resume"
            filepath = os.path.join(resume_folder, filename)
            file.save(filepath)

            # ✅ Store the correct relative path in the database
            user_id = session['user_id']
            relative_path = f"uploads/resume/{filename}"

            cur = mysql.connection.cursor()
            cur.execute("UPDATE student_profiles SET resume=%s WHERE user_id=%s", (relative_path, user_id))
            mysql.connection.commit()
            cur.close()

            flash('Resume uploaded successfully!', 'success')
            return redirect(url_for('student_home'))  # Redirect to Student Home Page

        else:
            flash('Invalid file format. Only PDFs are allowed.', 'danger')

    return render_template('upload_resume.html')


@app.route('/job_postings', strict_slashes=False)
def job_postings():
    try:
        conn = get_db_connection()
        if conn is None:
            return "Database Connection Failed", 500

        cursor = conn.cursor(MySQLdb.cursors.DictCursor)
        
        # Updated query to fetch company names from users table
        query = """
        SELECT jp.id, u.username AS company_name, jp.title, jp.description, jp.location, 
               jp.salary, jp.requirements, jp.deadline
        FROM job_postings jp
        JOIN users u ON jp.company_id = u.id
        ORDER BY jp.deadline ASC;
        """
        cursor.execute(query)
        jobs = cursor.fetchall()
        cursor.close()

        # Debugging: Print fetched jobs in Flask console
        print(f"Fetched Jobs: {jobs}")  # This should print job details

        return render_template('job_postings.html', jobs=jobs)
    
    except MySQLdb.OperationalError as e:
        return f"Database Error: {str(e)}", 500
    
    except Exception as e:
        return f"Unexpected Error: {str(e)}", 500

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

@app.route('/apply/<int:job_id>', methods=['GET', 'POST'])
def apply(job_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))  

    conn = get_db_connection()
    cursor = conn.cursor()

    user_id = session['user_id']

    # Fetch job details and convert tuple to dictionary
    cursor.execute("SELECT id, title, description FROM job_postings WHERE id = %s", (job_id,))
    job_data = cursor.fetchone()
    
    if job_data:
        job = {"id": job_data[0], "title": job_data[1], "description": job_data[2]}
    else:
        cursor.close()
        conn.close()
        return "Job not found", 404

    if request.method == 'POST':
        try:
            cursor.execute(
                "INSERT INTO applications (user_id, job_id, status) VALUES (%s, %s, 'Pending')",
                (user_id, job_id)
            )
            conn.commit()
            flash("Application submitted successfully!", "success")
            return redirect(url_for('student_home'))
        except mysql.connector.Error as err:
            flash(f"Error: {err}", "danger")
        finally:
            cursor.close()
            conn.close()

    # Fetch student details and convert tuple to dictionary
    cursor.execute("SELECT name, email, phone, CGPA, resume FROM student_profiles WHERE user_id = %s", (user_id,))
    student_data = cursor.fetchone()
    cursor.close()
    conn.close()

    if student_data:
        student = {
            "name": student_data[0],
            "email": student_data[1],
            "phone": student_data[2],
            "CGPA": student_data[3],
            "resume": student_data[4],
        }
    else:
        flash("Student profile not found!", "danger")
        return redirect(url_for('student_home'))

    # Extract only the filename for the resume URL
    if student["resume"]:
        filename = os.path.basename(student["resume"])  # Ensure only the filename is used
        resume_url = url_for("view_resume", filename=filename)
    else:
        resume_url = None  

    return render_template(
        "apply.html",
        job=job,  
        job_id=job["id"],  
        student_name=student["name"],
        student_email=student["email"],
        student_phone=student["phone"],
        student_cgpa=student["CGPA"],
        student_resume=resume_url,
    )

@app.route('/submit_application/<int:job_id>', methods=['POST'])
def submit_application(job_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    conn = mysql.connection
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)  # ✅ Use DictCursor

    try:
        print(f"User {user_id} is applying for Job {job_id}")

        # ✅ Step 1: Check if job exists
        cursor.execute("SELECT id FROM job_postings WHERE id = %s", (job_id,))
        job = cursor.fetchone()
        if not job:
            print("❌ Job does not exist")
            flash("Invalid Job ID!", "danger")
            return redirect(url_for('student_home'))

        print("✅ Job exists")

        # ✅ Step 2: Check if student profile exists and fetch resume
        cursor.execute("SELECT resume FROM student_profiles WHERE user_id = %s", (user_id,))
        student = cursor.fetchone()

        print(f"Student query result: {student}")  # Debugging output

        if not student or not student.get("resume"):  # ✅ Access 'resume' using dictionary key
            print("❌ No resume found for user!")
            flash("Please upload a resume before applying!", "danger")
            return redirect(url_for('student_home'))

        resume_link = student["resume"]
        print(f"✅ Resume found: {resume_link}")

        # ✅ Step 3: Check if user already applied
        cursor.execute("SELECT id FROM applications WHERE user_id = %s AND job_id = %s", (user_id, job_id))
        existing_application = cursor.fetchone()
        if existing_application:
            print("❌ Already applied for this job")
            flash("You have already applied for this job!", "warning")
            return redirect(url_for('student_home'))

        print("✅ No previous application found. Proceeding to insert...")

        # ✅ Step 4: Insert application
        sql_query = "INSERT INTO applications (user_id, job_id, resume) VALUES (%s, %s, %s)"
        values = (user_id, job_id, resume_link)
        print(f"📝 Running SQL: {sql_query} with values {values}")

        cursor.execute(sql_query, values)
        conn.commit()

        print("✅ Application submitted successfully!")
        flash("Application submitted successfully!", "success")

    except Exception as e:
        import traceback
        print(f"❌ Unexpected Error: {e}")  # Print error message
        print(traceback.format_exc())  # Print full error traceback

        flash(f"Error: {str(e)}", "danger")

    finally:
        cursor.close()

    return redirect(url_for('student_home'))

@app.route('/applied_status')
def applied_status():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    print("Logged-in User ID:", user_id)  # ✅ Debugging Output

    applications = []  # Default empty list

    try:
        # ✅ Use 'with' to ensure connection is properly closed
        with pymysql.connect(
            host="localhost",
            user="root",
            password="Root12345",
            database="project",
            cursorclass=pymysql.cursors.DictCursor  # ✅ Fixes dictionary issue
        ) as conn:

            with conn.cursor() as cursor:
                query = """
                    SELECT 
                        COALESCE(job_postings.title, 'Unknown Job') AS job_title, 
                        applications.resume, 
                        applications.applied_at,
                        applications.status
                    FROM applications
                    LEFT JOIN job_postings ON applications.job_id = job_postings.id
                    WHERE applications.user_id = %s
                    ORDER BY applications.applied_at DESC
                """
                cursor.execute(query, (user_id,))
                applications = cursor.fetchall()

                print("Fetched Applications:", applications)  # ✅ Debugging Output
                print("Total Applications Found:", len(applications))  # ✅ Check count

    except Exception as e:
        print("Database Error:", str(e))  # ✅ Debugging Error

    return render_template('applied_status.html', applications=applications)

def get_random_questions():
    db = get_db_connection()
    if not db:
        return []

    try:
        cursor = db.cursor(MySQLdb.cursors.DictCursor)  # ✅ Corrected cursor type
        cursor.execute("SELECT * FROM aptitude_questions ORDER BY RAND() LIMIT 20")
        questions = cursor.fetchall()
        return questions
    except MySQLdb.Error as e:
        print(f"Database error: {e}")
        return []
    finally:
        cursor.close()
        db.close()

@app.route('/aptitude_test', methods=['GET'])
def aptitude_test():
    if 'user_id' not in session or session.get('role') != 'student':
        return jsonify({"message": "Unauthorized"}), 403

    db = get_db_connection()
    if not db:
        return jsonify({"message": "Database connection failed"}), 500

    try:
        cursor = db.cursor()
        cursor.execute("SELECT user_id FROM student_profiles WHERE user_id = %s", (session['user_id'],))
        student = cursor.fetchone()

        if not student:
            return jsonify({"message": "Student profile not found"}), 404

        session['test_type'] = 'aptitude'  # Set the test type for aptitude test
        session['questions'] = get_random_questions()  # Store questions in session
        session.pop('test_results', None)  # Clear old test results
        return render_template('aptitude_test.html', questions=session['questions'])

    except MySQLdb.Error as e:
        print(f"Database error: {e}")
        return jsonify({"message": "Database error", "error": str(e)}), 500
    finally:
        cursor.close()
        db.close()
@app.route('/submit_test', methods=['POST'])
def submit_test():
    if 'user_id' not in session or session.get('role', '').lower() != 'student':
        return jsonify({"message": "Unauthorized"}), 403

    user_id = session['user_id']
    data = request.get_json()
    if not data or 'answers' not in data:
        return jsonify({"message": "Invalid request format"}), 400

    answers = data['answers']
    db = get_db_connection()
    if not db:
        return jsonify({"message": "Database connection failed"}), 500

    try:
        cursor = db.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT id FROM student_profiles WHERE user_id = %s", (user_id,))
        student = cursor.fetchone()

        if not student:
            return jsonify({"message": "Student not found"}), 404

        student_id = student['id']
        questions = session.get('questions', [])
        if not questions:
            return jsonify({"message": "No test session found"}), 400

        test_type = session.get('test_type', 'aptitude')
        results = []
        correct_answers = 0
        for question in questions:
            qid = str(question['id'])
            selected_option = answers.get(qid, None)
            correct_option = question['correct_option'].strip().upper()
            is_correct = selected_option and selected_option.strip().upper() == correct_option
            if is_correct:
                correct_answers += 1
            results.append({
                "question_id": qid,
                "question_text": question['question'],
                "option_a": question['option_a'],
                "option_b": question['option_b'],
                "option_c": question['option_c'],
                "option_d": question['option_d'],
                "selected_option": selected_option.strip().upper() if selected_option else None,
                "correct_option": correct_option,
                "is_correct": is_correct
            })

        print(f"Correct Answers: {correct_answers}, Total Questions: {len(questions)}")

        # Insert a new record for each test submission
        cursor.execute("""
            INSERT INTO student_performance (student_id, score, total_questions, correct_answers, test_type, test_date)
            VALUES (%s, %s, %s, %s, %s, NOW())
        """, (student_id, correct_answers, len(questions), correct_answers, test_type))

        db.commit()
        session['test_results'] = results
        session['total_questions'] = len(questions)

    except MySQLdb.Error as e:
        db.rollback()
        print(f"Database error: {e}")
        return jsonify({"message": "Database error", "error": str(e)}), 500
    finally:
        cursor.close()
        db.close()

    if test_type == 'special':
        return jsonify({
            "message": "Special Test submitted successfully",
            "score": correct_answers,
            "redirect": url_for('special_test_results')
        })
    else:
        return jsonify({
            "message": "Aptitude Test submitted successfully",
            "score": correct_answers,
            "redirect": url_for('test_results')
        })


@app.route('/test_results')
def test_results():
    if 'test_results' not in session:
        return redirect(url_for('aptitude_test'))  # Redirect if no test data found

    test_results = session['test_results']  # Fetch test results from session
    total_questions = len(test_results)  # Get the total number of questions from session
    score = sum(1 for result in test_results if result['is_correct'])  # Calculate score

    # Debugging: Print out the data stored in session
    print(test_results)  # Check if it contains all the question data

    # Pass the test_results as all_questions to the template
    return render_template('test_result.html', all_questions=test_results, score=score, total_questions=total_questions)

@app.route('/retest')
def retest():
    session.pop('questions', None)  # Clear previous test questions
    session.pop('test_results', None)  # Clear previous test results
    session.pop('total_questions', None)  # Clear total questions count
    return redirect(url_for('aptitude_test'))

@app.route('/special_test')
def special_test():
    session['test_type'] = 'special'
    
    db = get_db_connection()
    cursor = db.cursor(MySQLdb.cursors.DictCursor)

    # Adjust the table name if needed
    cursor.execute("SELECT * FROM special_test_questions ORDER BY RAND() LIMIT 20")
    questions = cursor.fetchall()
    
    cursor.close()
    db.close()

    session['questions'] = questions
    return render_template('special_test.html', questions=questions)


@app.route('/special_test_results')
def special_test_results():
    if 'test_results' not in session:
        return redirect(url_for('special_test'))  # Fallback if no session data

    test_results = session['test_results']
    total_questions = session.get('total_questions', len(test_results))
    score = sum(1 for result in test_results if result['is_correct'])

    return render_template('special_test_result.html', all_questions=test_results, score=score, total_questions=total_questions)
@app.route('/special_retest')
def special_retest():
    session.pop('questions', None)
    session.pop('test_results', None)
    session.pop('total_questions', None)
    session['test_type'] = 'special'
    return redirect(url_for('special_test'))


UPLOAD_FOLDER = 'uploads/study_materials'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/upload_study_material', methods=['GET', 'POST'])
def upload_study_material():
    if request.method == 'POST':
        # Check if a file is uploaded
        if 'file' not in request.files:
            flash('No file part', 'error')
            return redirect(request.url)

        file = request.files['file']

        # If no file was selected
        if file.filename == '':
            flash('No selected file', 'error')
            return redirect(request.url)

        # Get department from form, not URL parameters
        department = request.form.get('department')

        if not department:
            flash('Please select a department.', 'error')
            return redirect(request.url)

        # Create department-specific folder if it doesn't exist
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], department)
        os.makedirs(save_path, exist_ok=True)

        # Save the file inside the corresponding department folder
        file.save(os.path.join(save_path, file.filename))

        flash('File uploaded successfully!', 'success')
        return redirect(url_for('admin_home'))  # Redirect after upload

    return render_template('upload_study_material.html')  # Show upload page


@app.route('/view_study_materials/<department>')
def view_study_materials(department):
    study_materials_path = os.path.join(app.config['UPLOAD_FOLDER'], department)

    # Ensure the department directory exists
    if not os.path.exists(study_materials_path):
        return f"No study materials found for {department}", 404

    # Fetch files from the correct department folder
    files = os.listdir(study_materials_path)
    materials = [(file, os.path.join(department, file)) for file in files]

    return render_template('view_study.html', department=department, materials=materials)

@app.route('/download_study_material/<department>/<filename>')
def download_study_material(department, filename):
    try:
        study_material_path = os.path.join(app.config['UPLOAD_FOLDER'], department)
        return send_from_directory(study_material_path, filename, as_attachment=True)
    except Exception as e:
        return str(e), 500  # Return error message if download fails


@app.route("/add_job_posting", methods=["GET", "POST"])
def add_job_posting():
    db = get_db_connection()
    if not db:
        return jsonify({"message": "Database connection failed"}), 500

    try:
        cursor = db.cursor(MySQLdb.cursors.DictCursor)

        # Fetch companies from users table where role = 'Company'
        cursor.execute("SELECT id, username FROM users WHERE role = 'Company'")
        companies = cursor.fetchall()
        print(f"Fetched companies: {companies}")  # Debugging line

        if request.method == "POST":
            company_id = request.form.get("company_id")  # Changed to use ID
            title = request.form.get("title")
            description = request.form.get("description")
            location = request.form.get("location")
            salary = request.form.get("salary")
            requirements = request.form.get("requirements")
            deadline = request.form.get("deadline")

            print(f"Received data: {company_id}, {title}, {description}, {location}, {salary}, {requirements}, {deadline}")  # Debugging

            if not company_id:
                flash("Please select a valid company.", "warning")
                return redirect("/add_job_posting")

            try:
                # Insert job posting
                insert_query = """
                INSERT INTO job_postings (company_id, title, description, location, salary, requirements, deadline)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(insert_query, (company_id, title, description, location, salary, requirements, deadline))
                db.commit()
                flash("Job posting added successfully!", "success")
                print("Job posting inserted successfully!")

            except MySQLdb.Error as err:
                db.rollback()
                flash(f"Database Error: {err}", "danger")
                print(f"Database Error: {err}")

            return redirect("/admin_home")

    except MySQLdb.Error as e:
        print(f"Database error: {e}")
        return jsonify({"message": "Database error", "error": str(e)}), 500

    finally:
        cursor.close()
        db.close()

    return render_template("add_job_posting.html", companies=companies)  # Pass companies to template


@app.route('/view_students')
def view_students():
    conn = get_db_connection()
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)  # ✅ Use DictCursor

    # Fetch students
    cursor.execute("SELECT user_id, name, email FROM student_profiles")
    students = cursor.fetchall()  # ✅ Returns list of dictionaries

    cursor.close()
    conn.close()

    return render_template('view_students.html', students=students)

# Route to view a specific student’s details
@app.route('/student_details/<int:user_id>')
def student_details(user_id):
    conn = get_db_connection()
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)
    
    cursor.execute("SELECT * FROM student_profiles WHERE user_id = %s", (user_id,))
    student = cursor.fetchone()

    if student is None:
        return "Student not found", 404

    return render_template('student_details.html', student=student)


@app.route('/admin/applied_students')
def applied_students():
    """Display a list of students who have applied for jobs."""
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = mysql.connection
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)

    query = """
        SELECT DISTINCT users.id AS student_id, 
                        student_profiles.name, 
                        student_profiles.email
        FROM applications
        JOIN users ON applications.user_id = users.id
        JOIN student_profiles ON users.id = student_profiles.user_id
        ORDER BY student_profiles.name
    """
    cursor.execute(query)
    students = cursor.fetchall()
    cursor.close()

    return render_template('applied_students.html', students=students)

@app.route('/admin/applied_status/<int:student_id>')
def admin_applied_status(student_id):
    """Display application details for a specific student."""
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = mysql.connection
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)

    query = """
        SELECT 
            job_postings.title AS job_title,
            applications.resume,
            applications.applied_at,
            applications.status
        FROM applications
        JOIN job_postings ON applications.job_id = job_postings.id
        WHERE applications.user_id = %s
        ORDER BY applications.applied_at DESC
    """
    cursor.execute(query, (student_id,))
    applications = cursor.fetchall()
    cursor.close()

    return render_template('admin_applied_status.html', applications=applications)

@app.route('/company/applied_students')
def company_applied_students():
    """Display students who applied to jobs posted by the logged-in company."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = mysql.connection
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute("SELECT id FROM users WHERE id = %s AND role = 'Company'", (session['user_id'],))
    company = cursor.fetchone()
    
    if not company:
        flash("Unauthorized access", "danger")
        return redirect(url_for('company_home'))

    company_id = company['id']

    query = """
        SELECT DISTINCT student_profiles.id AS student_id, student_profiles.name, student_profiles.email
        FROM applications
        JOIN job_postings ON applications.job_id = job_postings.id
        JOIN student_profiles ON applications.user_id = student_profiles.user_id
        WHERE job_postings.company_id = %s
        ORDER BY student_profiles.name
    """
    cursor.execute(query, (company_id,))
    students = cursor.fetchall()
    cursor.close()

    return render_template('company_applied_students.html', students=students)

@app.route('/company/applied_status/<int:student_id>')
def company_applied_status(student_id):
    """Display application details for a specific student in the company."""
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = mysql.connection
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)

    # Get user_id from student_profiles
    cursor.execute("SELECT user_id FROM student_profiles WHERE id = %s", (student_id,))
    student = cursor.fetchone()

    if not student:
        flash("Student not found", "danger")
        return redirect(url_for('company_applied_students'))

    student_user_id = student['user_id']

    # Fetch applications using the correct user_id
    query = """
        SELECT applications.id, job_postings.title AS job_title, applications.resume, 
               applications.applied_at, applications.status
        FROM applications
        JOIN job_postings ON applications.job_id = job_postings.id
        WHERE applications.user_id = %s AND job_postings.company_id = %s
        ORDER BY applications.applied_at DESC
    """
    cursor.execute(query, (student_user_id, session['user_id']))
    applications = cursor.fetchall()
    cursor.close()

    return render_template('company_applied_status.html', applications=applications)


@app.route('/update_application_status', methods=['POST'])
def update_application_status():
    """Update the application status (Accept/Reject)."""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized access'}), 403

    data = request.json
    application_id = data.get('application_id')
    new_status = data.get('status')

    if not application_id or new_status not in ['Accepted', 'Rejected']:
        return jsonify({'success': False, 'message': 'Invalid data'}), 400

    conn = mysql.connection
    cursor = conn.cursor()

    query = """
        UPDATE applications
        SET status = %s
        WHERE id = %s AND job_id IN (
            SELECT id FROM job_postings WHERE company_id = %s
        )
    """
    cursor.execute(query, (new_status, application_id, session['user_id']))
    conn.commit()
    cursor.close()

    if cursor.rowcount > 0:
        return jsonify({'success': True, 'message': f'Application {new_status} successfully!'})
    else:
        return jsonify({'success': False, 'message': 'Action not allowed'}), 403

@app.route('/company/accepted_applications')
def company_accepted_applications():
    """Display only the applications that have been accepted."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = mysql.connection
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)

    query = """
        SELECT student_profiles.id AS student_id, student_profiles.name, student_profiles.email,
               job_postings.title AS job_title, applications.applied_at, applications.resume
        FROM applications
        JOIN job_postings ON applications.job_id = job_postings.id
        JOIN student_profiles ON applications.user_id = student_profiles.user_id
        WHERE job_postings.company_id = %s AND applications.status = 'Accepted'
        ORDER BY student_profiles.name
    """
    cursor.execute(query, (session['user_id'],))
    accepted_applications = cursor.fetchall()
    cursor.close()

    return render_template('company_accepted_applications.html', applications=accepted_applications)


@app.route('/book_slot', methods=['GET', 'POST'])
def book_slot():
    if 'user_id' not in session or session.get('role') != 'student':
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute("SELECT id, username FROM users WHERE LOWER(role) = 'admin'")
    admins = cursor.fetchall()

    message = None

    if request.method == 'POST':
        admin_id = request.form.get('admin_id')
        date = request.form.get('date')
        time = request.form.get('time')

        if not admin_id or not date or not time:
            message = "Invalid request format"
        else:
            # Validate time range (09:00 to 16:30)
            try:
                time_obj = datetime.strptime(time, "%H:%M").time()
                if not (datetime.strptime("09:00", "%H:%M").time() <= time_obj <= datetime.strptime("16:30", "%H:%M").time()):
                    message = "Meetings can only be scheduled between 9:00 AM and 4:30 PM."
                else:
                    student_id = session['user_id']
                    cursor.execute(
                        "INSERT INTO meeting_slots (student_id, admin_id, date, time, status) VALUES (%s, %s, %s, %s, 'Pending')",
                        (student_id, admin_id, date, time)
                    )
                    conn.commit()
                    message = "Slot booked successfully!"
            except Exception as e:
                message = "Database error: " + str(e)
            finally:
                cursor.close()
                conn.close()

    return render_template('book_slot.html', admins=admins, message=message)


@app.route('/view_meetings')
def view_meetings():
    if 'user_id' not in session or session.get('role') != 'student':
        return redirect(url_for('login'))

    student_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)

    # Fetch meetings for the logged-in student
    cursor.execute("""
        SELECT meeting_slots.id, users.username AS admin_name, meeting_slots.date, meeting_slots.time, meeting_slots.status 
        FROM meeting_slots 
        JOIN users ON meeting_slots.admin_id = users.id
        WHERE meeting_slots.student_id = %s
        ORDER BY meeting_slots.date DESC, meeting_slots.time ASC
    """, (student_id,))
    
    meetings = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template('view_meetings.html', meetings=meetings)

@app.route('/admin_view_meetings')
def admin_view_meetings():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))

    admin_id = session['user_id']
    
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT ms.id, s.username AS student_name, ms.date, ms.time, ms.status 
        FROM meeting_slots ms
        JOIN users s ON ms.student_id = s.id
        WHERE ms.admin_id = %s
        ORDER BY ms.date, ms.time
    """, (admin_id,))
    
    meetings = cur.fetchall()
    cur.close()
    
    return render_template('admin_view_meetings.html', meetings=meetings)

@app.route('/admin/manage_meetings', methods=['GET', 'POST'])
def manage_meetings():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))

    admin_id = session['user_id']
    cur = mysql.connection.cursor()
    
    # Fetch upcoming meetings for this admin
    cur.execute("""
        SELECT m.id, sp.name AS student_name, m.date, m.time, m.status
        FROM meeting_slots m
        JOIN student_profiles sp ON m.student_id = sp.user_id  
        WHERE m.admin_id = %s AND m.status = 'Pending'
        ORDER BY m.date, m.time
    """, (admin_id,))
    
    meetings = cur.fetchall()
    cur.close()

    return render_template('admin_manage_meetings.html', meetings=meetings)


@app.route('/admin/update_meeting_status', methods=['POST'])
def update_meeting_status():
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({'message': 'Unauthorized'}), 403

    data = request.get_json()
    meeting_id = data.get('meeting_id')
    new_status = data.get('status')

    # Map the status values to match the ENUM values in the database
    status_map = {
        'accepted': 'Approved',  # 'accepted' maps to 'Approved' in the database
        'rejected': 'Rejected'   # 'rejected' maps to 'Rejected' in the database
    }

    # Check if meeting_id exists and new_status is valid
    if not meeting_id or new_status not in status_map:
        return jsonify({'message': 'Invalid request'}), 400

    new_status = status_map[new_status]  # Convert the status to the correct value for the database

    cur = mysql.connection.cursor()
    cur.execute("UPDATE meeting_slots SET status = %s WHERE id = %s", (new_status, meeting_id))
    mysql.connection.commit()
    cur.close()

    return jsonify({'message': 'Meeting updated successfully'})


@app.route('/student_performance')
def student_performance():
    conn, cursor = get_db()  # ✅ Use get_db() to get (conn, cursor)
    
    cursor.execute("SELECT id, name, email FROM student_profiles")
    students = cursor.fetchall()  # ✅ No need for `dictionary=True`, already a DictCursor
    
    conn.close()
    return render_template('student_performance.html', students=students)

# Route to view performance of a specific student
@app.route('/student_performance/<int:student_id>')
def student_performance_detail(student_id):
    conn, cursor = get_db()  # ✅ Use get_db() which returns (conn, cursor)

    # Fetch student details
    cursor.execute("SELECT name, email FROM student_profiles WHERE id = %s", (student_id,))
    student = cursor.fetchone()  # ✅ Already returns a dictionary

    # Fetch performance data
    cursor.execute("""
        SELECT test_date, score, total_questions, correct_answers 
        FROM student_performance 
        WHERE student_id = %s ORDER BY test_date DESC
    """, (student_id,))
    performance_records = cursor.fetchall()  # ✅ List of dictionaries

    conn.close()  # ✅ Close connection properly
    return render_template('student_performance_detail.html', student=student, performance_records=performance_records)

# ================= RUN APP =================

if __name__ == "__main__":
    print(app.url_map)
    app.run(debug=True)
