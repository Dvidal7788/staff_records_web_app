from flask import Flask, render_template, redirect, request, session
from flask_session import Session
from flask_mail import Mail, Message
# from flask_wtf import CSRFProtect, FlaskForm
from werkzeug.security import check_password_hash, generate_password_hash
from functools import wraps
import sqlite3
from datetime import datetime, date
import os
import re
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

app = Flask(__name__)

# Configure session
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_TYPE'] = 'filesystem'
# app.config['SESSION_USE_SIGNER'] = True
Session(app)

# # Generate a random SECRET_KEY
# if 'SECRET_KEY' not in app.config:
#     app.config['SECRET_KEY'] = os.urandom(24).hex()

# # Generate a random WTF_CSRF_SECRET_KEY
# if 'WTF_CSRF_SECRET_KEY' not in app.config:
#     app.config['WTF_CSRF_SECRET_KEY'] = os.urandom(24).hex()

# # Configure CSRF
# csrf = CSRFProtect(app)
# csrf.init_app(app)

# Configure e-mail
app.config['MAIL_DEFAULT_SENDER'] = 'staffrecordsdatabase@gmail.com'
app.config['MAIL_USERNAME'] = 'staffrecordsdatabase@gmail.com'
app.config['MAIL_PASSWORD'] = 'pjqvksurkccnhsbj'
app.config['MAIL_PORT'] = 587 # TCP port
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_USE_TLS'] = True # Use encryption
app.config['MAIL_USE_SSL'] = False
mail = Mail(app)


# Class Definitions
class Results():
    def __init__(self, department, sort_by, num_of_results, asc_desc):
        self.department = department
        self.sort_by = sort_by
        self.num_of_results = num_of_results
        self.asc_desc = asc_desc
        return

class RemoveStaff():
    # Struct:
    emp_id: int
    first_name: str
    last_name: str
    department: str
    title: str
    reason: str
    end_date: str
    notes: str

    # Reset struct
    def reset(self):
        self.emp_id = None
        self.first_name = None
        self.last_name = None
        self.department = None
        self.reason = None
        self.end_date = None
        self.notes = None
        return


class PieChart():

    def __init__(self):
        self.sum = True
        self.percentage = False
        self.redirect = False
        self.joined_df = pd.DataFrame()
        self.file_path = ''
        return


# # This will only be used for {{ form.hidden_tag() }}, as the {{ csrf_token() }} syntax seems to have bugs
# class Form(FlaskForm):
#     pass


# Globals
departments_all = False
staff_added = False
email_sent = False
emp_to_remove = RemoveStaff()
emp_to_remove.reset()
access = {}
access['show_page2'] = False
access['show_page3'] = False
registration_success = False
password_reset_successful = False
results = None
dept_added = False
dept_removed = False
pie_chart = PieChart()




db = sqlite3.connect("sql/staff.db")
# Retrieve up to date staff column names
tmp_cursor = db.execute("SELECT name FROM PRAGMA_TABLE_INFO('staff')")
staff_columns = []
for tmp_tuple in tmp_cursor:
    staff_columns.append(tmp_tuple[0])

# Retrieve up to date salary column names
tmp_cursor = db.execute("SELECT name FROM PRAGMA_TABLE_INFO('salary')")
salary_columns = []
for tmp_tuple in tmp_cursor:
    salary_columns.append(tmp_tuple[0])


reasons_for_leaving = ['terminated', 'quit', 'retired', 'layed off', 'other']
security_questions = ["What is your mother's maiden name?", "In which city were you born?", "What is the name of your first crush?", "What is the name of your first pet?", "What is the name of your childhood best friend?", "What was the make and model of your first car?"]


# print('\n\nDEBUG SESSION BEGIN\n\n', session)
# print('\n\nDEBUG SESSION BEGIN\n\n')

def login_required(f):
    # Decorate routes to require login.
    # https://flask.palletsprojects.com/en/1.1.x/patterns/viewdecorators/

    @wraps(f)
    def decorated_function(*args, **kwargs):
        # if 'user_id' not in session:
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function


# Routes
@app.route("/")
def index():

    # print('\n\nDEBUG Index Session:\n', session)
    # print('\n\nDEBUG Index Request:\n', request.form)
    # print('\n\nDEBUG Index app.config["WTF_CSRF_SECRET_KEY"]:\n\n', app.config['WTF_CSRF_SECRET_KEY'])

    if not 'username' in session:
        # if not 'csrf_token' in session:
            # session['csrf_token'] = generate_password_hash(app.config['WTF_CSRF_SECRET_KEY'], method='pbkdf2:sha512')
        return render_template('index.html')
    else:
        username = session['username']
        return render_template('index.html', username=username)


@app.route("/register", methods=['GET', 'POST'])
def register():

    # print('\n\nDEBUG Register BEGIN\n', session)
    # print('\n\nDEBUG Register BEGIN\n', request.form)
    # print('\n\nDEBUG Register app.config["WTF_CSRF_SECRET_KEY"]:\n\n', app.config['WTF_CSRF_SECRET_KEY'])

    # Don't register if already logged in
    if 'user_id' in session:
        return redirect('/')

    # GET
    if request.method == 'GET':
        return render_template('register.html', security_questions=security_questions)

    # POST
    else:
        username = request.form.get('username').strip()
        password = request.form.get('password')
        confirmation = request.form.get('confirmation')
        security_question = request.form.get('security_question')
        security_answer = request.form.get('security_answer').strip()

        # Confirm form filled out
        if not username and not password and not confirmation:
            return render_template('error.html', message="You left the form blank")
        elif not username:
            return render_template('error.html', message="Username field left blank")
        elif not password:
            return render_template('error.html', message="Password field left blank")
        elif not confirmation:
            return render_template('error.html', message="Password Confirmation field left blank")
        elif not security_question or not security_answer:
            return render_template('error.html', message="Security Question/Answer not complete")

        # Make sure username is not already taken
        db = sqlite3.connect("sql/backend.db")
        tmp_cursor = db.execute("SELECT username FROM users")

        for tmp_tuple in tmp_cursor:
            if username == tmp_tuple[0]:
                return render_template('error.html', message="The username you entered is already taken")

        # Verify password meets criteria
        pw_criteria1 = 'Password must have at least 8 characters.'
        pw_criteria2 = '(At least 1 uppercase letter, 1 lowercase letter, 1 number & 1 special character.)'

        if len(password) < 8:
            return render_template('error.html', message=pw_criteria1, message2=pw_criteria2)

        # Verify password meets pw_criteria2 as stated above
        pw_letter = False
        pw_number = False
        pw_special_char = False
        pw_upper = False
        pw_lower = False

        for char in password:
            if char.isalpha():
                pw_letter = True
                if char.isupper():
                    pw_upper = True
                else:
                    pw_lower = True
            elif char.isnumeric():
                pw_number = True
            elif not char.isalnum():
                pw_special_char = True

        if not pw_letter or not pw_number or not pw_special_char or not pw_upper or not pw_lower:
            return render_template('error.html', message=pw_criteria1, message2=pw_criteria2)


        # Verify password matches confirmation password
        if password != confirmation:
            return render_template('error.html', message="The password you entered does not match your confirmation")

        # --- Add user to database ---
        # Create new user_id
        tmp_cursor = db.execute("SELECT MAX(user_id) FROM users")
        for tmp_tuple in tmp_cursor:
            if tmp_tuple[0] == None:
                new_id = 0
            else:
                new_id = tmp_tuple[0] + 1

        db.execute("INSERT INTO users (user_id, username, pw_hash) VALUES(?,?,?)", (new_id, username, generate_password_hash(password, method='pbkdf2:sha512')))
        db.commit()

        # Add security question/answer to table if user entered this info
        if security_question and security_answer:
            db.execute("UPDATE users SET security_question = ?, security_answer = ?  WHERE user_id = ?", (security_question, generate_password_hash(security_answer, method='pbkdf2:sha512'), new_id))
            db.commit()

        global registration_success
        registration_success = True

        return redirect("/login")


@app.route("/login", methods=['GET', 'POST'])
def login():

    # print('\n\nDEBUG Login BEGIN\n', session)
    # print('\n\nDEBUG Login BEGIN\n', request.form)
    # print('\n\nDEBUG Login app.config["WTF_CSRF_SECRET_KEY"]:\n\n', app.config['WTF_CSRF_SECRET_KEY'])

    # Don't log in if already logged in
    if 'user_id' in session:
        return redirect('/')

    # GET
    if request.method == 'GET':

        # Show alerts or not
        global registration_success
        global password_reset_successful

        if registration_success:

            # Reset bool to default
            registration_success = False
            return render_template('login.html', registration_success=True)

        elif password_reset_successful:

            # Reset bool to default
            password_reset_successful = False
            return render_template('login.html', password_reset_successful=True)

        return render_template('login.html', registration_success=False)


    # POST
    else:
        username = request.form.get('username')
        password = request.form.get('password')

        db = sqlite3.connect("sql/backend.db")
        tmp_cursor = db.execute("SELECT * FROM users WHERE username = ?", (username,))

        user_found = False
        for tmp_tuple in tmp_cursor:
            if username == tmp_tuple[1]:
                user_found = True
                session['user_id'] = tmp_tuple[0]
                session['username'] = tmp_tuple[1]
                hash = tmp_tuple[2]

        if not user_found:
            return render_template('error.html', message='Username incorrect.', message2='Try again.')

        if not check_password_hash(hash, password):
            session.clear()
            return render_template('error.html', message='Password incorrect.', message2='Try again.')

        return redirect("/")


@app.route("/logout")
def logout():
    global email_sent, staff_added, departments_all, registration_success, results

    # Reset globals and redirect to "/"
    session.clear()
    emp_to_remove.reset()
    for key in access:
        access[key] = False

    email_sent = staff_added = departments_all = registration_success = False
    results = None
    dept_added = dept_removed = False

    # Remove CSVs from CSV directory
    os.system('rm -f csv/*')

    return redirect("/")


@app.route("/password_reset", methods=['GET', 'POST'])
def password_reset():
    global username

    # GET
    if request.method == 'GET':
        return render_template("/password_reset.html", security_questions=security_questions)

    # POST
    else:
        # Check Page 1
        if request.form.get('username'):

            username = request.form.get('username')

            # Retrive security question from SQL database
            db = sqlite3.connect("sql/backend.db")
            tmp_cursor = db.execute("SELECT security_question FROM users WHERE username = ?", (username,))
            for tmp_tuple in tmp_cursor:
                # Display Page 2
                return render_template("/password_reset.html", security_question=tmp_tuple[0], show_page2=True)

            # Username not found
            return render_template("/password_reset.html", username_not_found=True)

        # Check Page 2
        elif request.form.get('security_answer'):

            db = sqlite3.connect("sql/backend.db")
            tmp_cursor = db.execute("SELECT security_answer FROM users WHERE username = ?", (username,))
            for tmp_tuple in tmp_cursor:
                security_answer_hashed = tmp_tuple[0]

            if check_password_hash(security_answer_hashed, request.form.get('security_answer')):
                # Display Page 3
                return render_template("/password_reset.html", show_page3=True, username=username)
            else:
                return render_template("/password_reset.html", answer_incorrect=True)

        elif request.form.get('new_password') and request.form.get('confirmation'):
            new_password = request.form.get('new_password')
            confirmation = request.form.get('confirmation')

            if new_password != confirmation:
                return render_template("password_reset.html", passwords_did_not_match=True)

            db = sqlite3.connect("sql/backend.db")
            db.execute("UPDATE users SET pw_hash = ? WHERE username = ?", (generate_password_hash(new_password ,method='pbkdf2:sha512'), username))
            db.commit()

            # Reset global
            username = None

            global password_reset_successful
            password_reset_successful = True

            return redirect("/login")


@app.route("/add_new_staff", methods=['GET', 'POST'])
@login_required
def add_new_staff():
    global staff_added

    # Retreive departments
    departments = get_departments()

    departments = format_list(departments)

    # GET
    if request.method == 'GET':
        if staff_added:
            # Reset staff_added before rendering template
            staff_added = False

            return render_template('add_new_staff.html', departments=departments, staff_added=True, username=session['username'], today=date.today())
        else:
            return render_template('add_new_staff.html', departments=departments, staff_added=False, username=session['username'], today=date.today())


    # POST
    else:
        first_name = request.form.get('first_name').strip()
        last_name = request.form.get('last_name').strip()
        department = request.form.get('department')
        title = request.form.get('title').strip()
        salary = request.form.get('salary')
        start_date = request.form.get('start_date')

        # Validate form
        if not first_name or not last_name or not department or not title or not start_date:
            return render_template('error.html', message="Missing information", username=session['username'])


        # Get max emp_id
        db = sqlite3.connect("sql/staff.db")
        tmp_cursor = db.execute("SELECT MAX(emp_id) FROM staff")
        tmp_cursor2 = db.execute("SELECT MAX(emp_id) FROM former_staff")

        for tmp_tuple in tmp_cursor:
            if tmp_tuple[0] == None:
                new_id = 0
            else:
                new_id = tmp_tuple[0] + 1

        # Checking former_staff max emp_id ensures if the most recent employee added was recently let go (inwhich case the max emp_id will be a former employee), each employee, former and current each have a unique ID
        for tmp_tuple in tmp_cursor2:
            # Can't compare NoneType to int
            if tmp_tuple[0] != None and tmp_tuple[0] >= new_id:
                new_id = tmp_tuple[0] + 1

        # cur = db.cursor()
        db.execute("INSERT INTO staff VALUES (?,?,?,?,?,?)", (new_id, first_name.lower(), last_name.lower(), department.lower(), title.lower(), start_date))
        db.execute("INSERT INTO salary VALUES (?, ?)", (new_id, salary))
        db.commit()

        staff_added = True

        return redirect("/add_new_staff")


@app.route("/all_staff")
@login_required
def all_staff():
    global departments_all

    departments_all = True
    return redirect("/departments")


@app.route("/departments", methods=['GET', 'POST'])
@login_required
def departments():
    global departments_all
    global email_sent
    global staff
    global results

    # Retrieve department list
    departments = get_departments()
    departments = format_list(departments)

    columns = format_list(staff_columns)

    # GET
    if request.method == 'GET' and not departments_all:
        if email_sent:
            email_sent = False
            return render_template('departments.html', departments=departments, columns=columns, staff=staff, results=results, username=session['username'], email_sent=True, display_results=True)
        else:
            return render_template('departments.html', departments=departments, columns=columns, landing_page=True, username=session['username'], email_sent=False)

    # POST
    elif request.method == 'POST' or departments_all:

        # Check if asc/desc
        if request.form.get('asc_desc') and results and staff:

            asc_desc = request.form.get('asc_desc')
            results.sort_by = request.form.get('resort_by')
            results.asc_desc = asc_desc

            # Resort
            if asc_desc == 'ascending':
                staff.sort(key=lambda x: x[deformat_str(results.sort_by, True)])
            else:
                staff.sort(key=lambda x: x[deformat_str(results.sort_by, True)], reverse=True)

            return render_template('departments.html', departments=departments, columns=columns, staff=staff, results=results, display_results=True, username=session['username'])


        # Retreive form
        department = request.form.get('department')
        sort_by = request.form.get('sort_by')

        # Validate form
        if sort_by and not department:
            return render_template('departments.html', departments_blank=True, departments=departments, columns=columns, username=session['username'])
        elif not department and not sort_by and not departments_all:
            return render_template('departments.html', form_blank=True, departments=departments, columns=columns, username=session['username'])

        # All
        if departments_all:
            department = 'all'
            # departments_all = False

        # SQL
        staff = access_staff_sql(deformat_str(department, False))

        # Sort
        if sort_by:
            staff.sort(key=lambda x: x[deformat_str(sort_by, True)])
        else:
            sort_by = 'Employee ID'

        # Format staff
        staff_count = len(staff)
        for i in range(staff_count):
            staff[i] = format_dict(staff[i])

        # Results
        results = Results(department, sort_by, staff_count, 'ascending')

        land = False
        if departments_all:
            departments_all = False
            land = True
        return render_template('departments.html', departments=departments, columns=columns, staff=staff, results=results, display_results=True, landing_page=land, username=session['username'])



@app.route("/csv_export", methods=['POST'])
@login_required
def csv_export():
    print('HERE DEBUG CSV EXPORT')
    # Remove any previous CSVs
    os.system('rm -f csv/*')

    global email_sent

    # Retrieve info from database
    staff = access_staff_sql(deformat_str(results.department, False))

    if len(staff) == 0:
        return redirect('/departments')

    # Sort
    if results.asc_desc == 'ascending':
        staff.sort(key=lambda x: x[deformat_str(results.sort_by, True)])
    else:
        staff.sort(key=lambda x: x[deformat_str(results.sort_by, True)], reverse=True)

    # Format
    staff = format_list(staff)

    # Create timestamp (without milliseconds/microseconds normally present in datetime's standard format)
    now = datetime.now()
    timestamp = f'{now.date()}_{now.hour}:{now.minute}:{now.second}'

    # Create filename
    filename = f'{deformat_str(results.department, False)}_{timestamp}.csv'

    num_of_columns = len(staff_columns)

    # Write data to new csv file
    with open(f'csv/{filename}', 'w') as file:

        # Write header
        for i in range(num_of_columns):
            if i < num_of_columns-1:
                file.write(f'{staff_columns[i]},')
            else:
                file.write(f'{staff_columns[i]}\n')

        # Write rest of file
        for person in staff:
            i = 0
            for key in person:
                if i < len(staff_columns)-1:
                    file.write(f'{person[key]},')
                else:
                    file.write(f'{person[key]}\n')
                i += 1

    if not request.form.get('download_csv'):

        # E-mail
        email = request.form.get('email')

        # Validate email server side
        if not re.search('^.+@.+\....$', email):
            return redirect('/departments')

        message = Message('The csv file you requested', recipients=[email])

        if results.department != 'all':
            message.body = f"Here is the csv file you requested of:\n\nThe '{results.department}' Department sorted by '{results.sort_by}' ({results.asc_desc})."
        else:
            message.body = f"Here is the csv file you requested of:\n\n'All departments' sorted by '{results.sort_by}' ({results.asc_desc})."

        # Attach
        with app.open_resource(f'csv/{filename}') as csv_fp:
            message.attach(filename, 'application/csv', csv_fp.read())

        # Send e-mail
        mail.send(message)

        # Email confirmation
        email_sent = True

        # Remove csv
        # os.remove(file_path)

        return redirect("/departments")

    return render_template("download_csv.html", filename=filename, username=session['username'])




@app.route("/remove_staff", methods=['GET', 'POST'])
@login_required
def remove_staff():
    global access_pages
    global employee_to_remove

    # GET
    if request.method == 'GET':

        if access['show_page3']:

            # Page 3 - FINAL PIN Page
            access['show_page3'] = False
            return render_template('remove_staff.html', show_page2=False, show_page3=True, username=session['username'])

        elif access['show_page2']:

            # Page 2 - Remove Staff Page
            access['show_page2'] = False
            return render_template('remove_staff.html', reasons_for_leaving=format_list(reasons_for_leaving), show_page2=True, show_page3=False, departments=format_list(get_departments()), username=session['username'])

        else:

            # Page 1 - PIN Page
            return render_template('remove_staff.html', show_page2=False, show_page3=False, username=session['username'])


    # POST
    else:

        # Page 1 - PIN Page
        if request.form.get('check_page1'):

            # Retrieve manager PIN
            manager_pin = request.form.get('manager_pin')

            # Check PIN is correct
            db = sqlite3.connect("sql/backend.db")
            tmp_cursor = db.execute("SELECT hash FROM manager_pin")

            for tmp_tuple in tmp_cursor:
                if check_password_hash(tmp_tuple[0], manager_pin):
                    access['show_page2'] = True
                    return redirect("/remove_staff")

            return render_template('error.html', message="The PIN you entered is incorrect.", username=session['username'])


        # Page 2 - Remove Staff Page
        elif request.form.get('check_page2'):

            if not request.form.get('emp_id') or not request.form.get('first_name') or not request.form.get('last_name') or not request.form.get('department') or not request.form.get('reason') or not request.form.get('end_date'):
                return render_template('error.html', message="Please make sure all fields are filled out.", username=session['username'])

            # REMOVE Staff Member
            emp_id = request.form.get('emp_id')
            first_name = request.form.get('first_name').lower()
            last_name = request.form.get('last_name').lower()
            department = request.form.get('department').lower()
            reason = request.form.get('reason').lower()
            end_date = request.form.get('end_date')
            notes = request.form.get('notes')

            db = sqlite3.connect("sql/staff.db")
            tmp_cursor = db.execute("SELECT * FROM staff WHERE emp_id = ?", (emp_id,))

            for tmp_tuple in tmp_cursor:
                # Validate submission
                if tmp_tuple[1] != first_name or tmp_tuple[2] != last_name:
                    return render_template('error.html', message="The name you entered does not match the employee ID you entered", username=session['username'])
                elif tmp_tuple[3] != department:
                    return render_template('error.html', message="The employee who matches the name and employee ID that you entered is assigned to a different department than you entered.", username=session['username'])
                elif tmp_tuple[0] == int(emp_id):

                    # Remember employee to remove
                    emp_to_remove.emp_id = int(emp_id)
                    emp_to_remove.first_name = first_name
                    emp_to_remove.last_name = last_name
                    emp_to_remove.department = department
                    emp_to_remove.title = tmp_tuple[4]
                    emp_to_remove.reason = reason
                    emp_to_remove.end_date = end_date
                    if notes:
                        emp_to_remove.notes = notes

                    # Allow access to Final page
                    access['show_page3'] = True

                    # Validated (move on to final PIN)
                    return redirect("/remove_staff")

            # Final validation if never entered into for loop above (tmp_cursor)
            return render_template('error.html', message="No staff member matches the employee ID that you entered.", username=session['username'])

        # Final Confirmation Page - Remove staff from SQL database/ Update former_employees table
        elif request.form.get('check_page3'):

            # Retrieve PIN
            manager_pin = request.form.get('manager_pin')

            # Check PIN is correct one last time
            db = sqlite3.connect("sql/backend.db")
            tmp_cursor = db.execute("SELECT hash FROM manager_pin")

            for tmp_tuple in tmp_cursor:
                if check_password_hash(tmp_tuple[0], manager_pin):

                    # Remove
                    db = sqlite3.connect("sql/staff.db")

                    # Retreive start date
                    tmp_cursor = db.execute("SELECT start_date FROM staff WHERE emp_id = ?", (emp_to_remove.emp_id,))
                    for tmp_tuple in tmp_cursor:
                        start_date = tmp_tuple[0]

                    # Remove from staff table
                    db.execute("DELETE FROM staff WHERE emp_id = ?", (emp_to_remove.emp_id,))
                    db.commit()

                    # Remove from salary table - ON DELETE CASCADE doesn't seem to be working
                    db.execute("DELETE FROM salary WHERE emp_id = ?", (emp_to_remove.emp_id,))
                    db.commit()

                    # Update former_employees table
                    query = "INSERT INTO former_staff VALUES(?,?,?,?,?,?,?,?,?)"
                    db.execute(query, (emp_to_remove.emp_id, emp_to_remove.first_name, emp_to_remove.last_name, emp_to_remove.department, emp_to_remove.title, emp_to_remove.reason, start_date, emp_to_remove.end_date, emp_to_remove.notes))
                    db.commit()



                    # Prepare confirmation message
                    confirmation_message2 = f'Employee ID: {emp_to_remove.emp_id}, Name: {emp_to_remove.first_name.title()} {emp_to_remove.last_name.title()}, Department: {format_str(emp_to_remove.department)}'

                    # Reset global
                    emp_to_remove.reset()

                    return render_template('success.html', message="The following staff member has been successfully removed from the staff database:", message2=confirmation_message2, username=session['username'])

                else:
                    return render_template('error.html', message="The PIN you entered is incorrect.", username=session['username'])



@app.route("/staff_lookup", methods=['GET', 'POST'])
@login_required
def staff_lookup():

    # Format column names for better readability
    columns = format_list(staff_columns)

    # GET
    if request.method == 'GET':

        return render_template('staff_lookup.html', columns=columns, found=False, username=session['username'])

    # POST
    else:
        column = request.form.get('column')
        search = request.form.get('search')

        # SQL
        staff = access_staff_sql_like(column, search)

        results = {}
        results['num_of_results'] = len(staff)
        results['column'] = format_str(column)
        results['search'] = search.replace('%', '')

        if len(staff) > 0:
            return render_template('staff_lookup.html', columns=columns, found=True, staff=staff, results=results, username=session['username'])

        return render_template('staff_lookup.html', columns=columns, no_results=True, results=results, username=session['username'])


@app.route("/edit_staff", methods=['GET', 'POST'])
@login_required
def edit_staff():
    global staff
    global edit_info

    columns = format_list(staff_columns)

    # GET
    if request.method == 'GET':
        return render_template('edit_staff.html', columns=columns, first_page=True, username=session['username'])

    # POST
    else:

        # EDIT STAFF MEMBER
        if request.form.get('confirm_edit') == 'yes':

            # Type check DATE SQL data type. (It is string, so sqlite3.IntegrityError will not catch it as long as its a string)
            if 'date' in edit_info['column_to_edit'] and edit_info['new_value'].count('-') != 2:
                return render_template('edit_staff.html', columns=columns, datatype_mismatch=True, first_page=True, username=session['username'])

            # Set up query (column names don't work with ? placeholder)
            query = f"UPDATE staff SET {edit_info['column_to_edit']} = ? WHERE emp_id = ?"

            # Try to UPDATE table - type checking new value
            db = sqlite3.connect("sql/staff.db")
            try:
                db.execute(query, (deformat_str(edit_info['new_value'], False), edit_info['emp_id']))
                db.commit()
            except sqlite3.IntegrityError:
                return render_template('edit_staff.html', columns=columns, datatype_mismatch=True, first_page=True, username=session['username'])

            staff.clear()
            edit_info.clear()

            return render_template('edit_staff.html', columns=columns, staff_edited=True, first_page=True, username=session['username'])

        elif request.form.get('confirm_edit') == 'no':
            return redirect('/edit_staff')


        # -- Page 3 --
        elif request.form.get('column_to_edit') and request.form.get('new_value') and request.form.get('emp_id'):

            edit_info = {}
            edit_info['column_to_edit'] = request.form.get('column_to_edit')
            edit_info['new_value'] = request.form.get('new_value')
            edit_info['emp_id'] = request.form.get('emp_id')

            message2 = f"Employee ID: {edit_info['emp_id']}'s {format_str(edit_info['column_to_edit'])} to '{edit_info['new_value']}'?"
            return render_template('confirmation.html', message=f"Are you sure you want to edit:", message2=message2, confirm_edit_staff=True, username=session['username'])

        # -- Page 2 --
        elif request.form.get('person_to_edit_emp_id'):

            # Get full dict of person to edit
            for person in staff:
                if person['emp_id'] == int(request.form.get('person_to_edit_emp_id')):
                    person_to_edit = person

            return render_template('edit_staff2.html', columns=columns, person_to_edit=person_to_edit, username=session['username'])


        else:

            # -- Page 1 --
            # Retrieve form
            column = request.form.get('column')
            search = request.form.get('search')

            # SQL
            staff = access_staff_sql_like(column, search)

            results = {}
            results['num_of_results'] = len(staff)
            results['column'] = format_str(column)
            results['search'] = search.replace('%', '')

            if len(staff) > 0:
                return render_template('edit_staff.html', columns=columns, found=True, staff=staff, results=results, username=session['username'])

            return render_template('edit_staff.html', columns=columns, no_results=True, staff=staff, results=results, username=session['username'])



@app.route("/salary")
@login_required
def salary():

    columns = format_list(staff_columns)
    columns.insert(1, 'Salary')

    # SQL
    db = sqlite3.connect("sql/staff.db")
    tmp_cursor = db.execute("SELECT salary.emp_id, salary, first_name, last_name, department, title, start_date FROM salary JOIN staff on salary.emp_id = staff.emp_id")

    staff = []
    for tmp_tuple in tmp_cursor:
        tmp_dict = {}
        for i in range(len(columns)):
            if columns[i] == 'Salary':
                tmp_dict[columns[i]] = usd(tmp_tuple[i], True)
            else:
                tmp_dict[columns[i]] = tmp_tuple[i]
        staff.append(format_dict(tmp_dict))


    return render_template('salary.html', columns=columns, staff=staff, username=session['username'])


@app.route("/former_staff")
@login_required
def former_staff():

    db = sqlite3.connect("sql/staff.db")

    # Retrieve up to date column names from SQL
    tmp_cursor = db.execute("SELECT name FROM PRAGMA_TABLE_INFO('former_staff')")
    former_staff_columns = []

    # Iterate through cursor
    for tmp_tuple in tmp_cursor:
        former_staff_columns.append(tmp_tuple[0])


    # Retrieve Former Staff from SQL
    tmp_cursor = db.execute("SELECT * FROM former_staff")

    # Iterate through cursor
    former_staff = []
    for tmp_tuple in tmp_cursor:
        tmp_dict = {}
        for i in range(len(former_staff_columns)):

            # Don't format notes (last index)
            if i == len(former_staff_columns)-1:
                tmp_dict[former_staff_columns[i]] = tmp_tuple[i]
            else:
                tmp_dict[former_staff_columns[i]] = format_str(tmp_tuple[i])

        former_staff.append(tmp_dict)

    return render_template('former_staff.html', former_staff=former_staff, columns=format_list(former_staff_columns), username=session['username'])


@app.route('/add_remove_department', methods=['GET', 'POST'])
@login_required
def add_remove_departmemt():
    global dept_added
    global dept_removed

    # GET
    if request.method == 'GET':
        if dept_added:
            dept_added = False
            return render_template('add_remove_department.html', dept_added=True, username=session['username'])
        elif dept_removed:
            dept_removed = False
            return render_template('add_remove_department.html', dept_removed=True, username=session['username'])

        return render_template('add_remove_department.html', username=session['username'])

    # POST
    else:
        # Add department view
        if request.form.get('add_dept'):
            return render_template('add_remove_department.html', departments=format_list(get_departments()), username=session['username'], add_dept=True)

        # Remove department view
        else:
            return render_template('add_remove_department.html', departments=format_list(get_departments()), username=session['username'], remove_dept=True)


@app.route('/add_dept', methods=['POST'])
@login_required
def add_dept():
    global new_dept
    global dept_added

    if not request.form.get('confirm_add_dept'):

        new_dept = request.form.get('new_dept')
        departments = get_departments()

        if new_dept.lower() in departments:
            return render_template('error.html', message='The department below already exists', message2=f"'{format_str(new_dept)}'", username=session['username'])
        elif len(new_dept) == 0:
            return render_template('error.html', message='You did not enter a department name', username=session['username'])
        else:
            return render_template('confirmation.html', message='Are you sure you want to add the department:', message2=f"'{format_str(new_dept)}'", confirm_add_dept=True, username=session['username'])

    # Coming from confirmation
    else:

        if request.form.get('confirm_add_dept') == 'yes':
            db = sqlite3.connect('sql/staff.db')
            db.execute('INSERT INTO departments VALUES (?)', (new_dept.lower(),))
            db.commit()
            dept_added = True

        # Redirect whether yes or no
        return redirect('/add_remove_department')


@app.route('/remove_dept', methods=['POST'])
@login_required
def remove_dept():
    global dept_to_remove
    global dept_removed

    if not request.form.get('confirm_remove_dept'):

        dept_to_remove = request.form.get('dept_to_remove')

        return render_template('confirmation.html', message='CAUTION: Are you sure you want to REMOVE the following department?', message2=f"'{dept_to_remove}'", confirm_remove_dept=True, username=session['username'])

    # Coming from confirmation
    else:

        if request.form.get('confirm_remove_dept') == 'yes':

            # SQL
            db = sqlite3.connect('sql/staff.db')
            db.execute('DELETE FROM departments WHERE department = (?)', (dept_to_remove.lower(),))
            db.execute('UPDATE staff SET department = NULL WHERE department = (?)', (dept_to_remove.lower(),))
            db.commit()
            dept_removed = True

        # Redirect whether yes or no
        return redirect('/add_remove_department')




@app.route('/visualization', methods=['GET', 'POST'])
@login_required
def visualization():

    global pie_chart

    numeric_column = 'salary'
    categorical_column = 'department'

    pie_chart.sum_mean = 'Mean' if pie_chart.sum else 'Sum'
    pie_chart.percentage_value = 'Dollar Value' if pie_chart.percentage else 'Percentage'


    #           -- GET --
    if not pie_chart.redirect:

        # Retrieve data from database
        db = sqlite3.connect('sql/staff.db')
        tmp_cursor = db.execute('SELECT * FROM staff')

        data = []

        # Each row
        for tmp_tuple in tmp_cursor:

            # Each value in row
            row = {}
            for column, value in zip(staff_columns, tmp_tuple):
                row[column] = value

            data.append(row)

        staff_df = pd.DataFrame(data)

        tmp_cursor = db.execute('SELECT * FROM salary')

        data = []

        # Each row
        for tmp_tuple in tmp_cursor:

            # Each value in row
            row = {}
            for column, value in zip(salary_columns, tmp_tuple):
                row[column] = value

            data.append(row)

        salary_df = pd.DataFrame(data)

        # JOIN
        pie_chart.joined_df = pd.merge(staff_df, salary_df, on='emp_id', how='inner')

        print('\n\nNOT REDIRECT', pie_chart.sum, pie_chart.percentage,'\n\n')
        # Group joined_df and create pie chart
        create_pie_chart(numeric_column, categorical_column, pie_chart)

        return render_template('visualization.html', pie_chart=pie_chart, username=session['username'])


    #           --- POST ---

    # Reset bool to default
    pie_chart.redirect = False

    print('\n\nREDIRECT', pie_chart.sum, pie_chart.percentage,'\n\n')

    # Group joined_df and create pie chart
    create_pie_chart(numeric_column, categorical_column, pie_chart)

    return render_template('visualization.html', pie_chart=pie_chart, username=session['username'])



def create_pie_chart(numeric_column, categorical_column, pie_chart):

    # Group joined_df by categorical column
    if pie_chart.sum:
        print('GROUP SUM\n')
        grouped = pie_chart.joined_df[[numeric_column, categorical_column]].groupby([categorical_column], as_index=False).sum()
    else:
        print('GROUP MEAN\n')
        grouped = pie_chart.joined_df[[numeric_column, categorical_column]].groupby([categorical_column], as_index=False).mean()

    # File path of chart
    file_path = f'static/graphs/{numeric_column}_{categorical_column}_pie_chart.png'
    pie_chart.file_path = file_path

    # Legend file path
    dot_index = file_path.find('.')
    legend_file_path = f'{file_path[:dot_index]}_legend.png'

    # Create a pie chart
    plt.figure(figsize=(8,6))

    if pie_chart.percentage:
        plt.pie(grouped[numeric_column], labels=format_list(list(grouped[categorical_column])), autopct='%1.1f%%', startangle=90)
    else:
        plt.pie(grouped[numeric_column], labels=format_list(list(grouped[categorical_column])), autopct=lambda p: '${:,.0f}'.format(p * sum(grouped['salary']) / 100, p), pctdistance=.8, startangle=90)
        # plt.pie(grouped['salary'], labels=format_list(list(grouped['department'])), autopct=lambda p: '${:,.0f}\n({:.1f}%)'.format(p * sum(grouped['salary']) / 100, p), pctdistance=.8, startangle=90)

    # Equal aspect ratio ensures that pie is drawn as a circle.
    plt.axis('equal')

    plt.title(f'Total (SUM) {numeric_column.title()} per {categorical_column.title()}', y=1.065) if pie_chart.sum else plt.title(f'Average (MEAN) {numeric_column.title()} per {categorical_column.title()}', y=1.065)


    # salary_with_dollarsign = [usd(sal, True) for sal in grouped['salary']]

    # Save legend separately
    # legend = plt.legend(salary_with_dollarsign, loc='upper right')

    # fig  = legend.figure
    # fig.canvas.draw()
    # bbox  = legend.get_window_extent().transformed(fig.dpi_scale_trans.inverted())
    # fig.savefig(filename, dpi="figure", bbox_inches=bbox)

    # Delete previous chart/legend
    os.system(f'rm -f {file_path}')
    # os.system(f'rm -f {legend_file_path}')

    # Save the chart
    plt.savefig(file_path)
    # legend.savefig(legend_file_path)



@app.route('/pie_chart_toggle', methods=['POST'])
@login_required
def pie_chart_toggle():

    global pie_chart

    # Toggle between sum/mean
    if request.form.get('toggle') == 'sum_mean':
        pie_chart.sum = not pie_chart.sum

    # Toggle between percentage/value
    else:
        pie_chart.percentage = not pie_chart.percentage

    pie_chart.redirect = True

    return redirect('/visualization')






#   --- SQL FUNCTIONS ---

def access_staff_sql(department):

    # Retrieves info from selected department
        db = sqlite3.connect("sql/staff.db")

        if department == 'all':
            tmp_cursor = db.execute("SELECT * FROM staff")
        else:
            tmp_cursor = db.execute("SELECT * FROM staff WHERE department = ?", (department,))

        staff = []
        for tmp_tuple in tmp_cursor:
            tmp_dict = {}
            for i in range(len(staff_columns)):
                tmp_dict[staff_columns[i]] = tmp_tuple[i]
            staff.append(tmp_dict)

        # Return list of dicts
        return staff



def access_staff_sql_like(column, search):

    # Create SQL query string because can not use column as ? since it should not be a type string
    query = f'SELECT * FROM staff WHERE {deformat_str(column, True)} LIKE ?'

    db = sqlite3.connect("sql/staff.db")
    tmp_cursor = db.execute(query, (f'%{search}%',))

    staff = []
    for tmp_tuple in tmp_cursor:
        tmp_dict = {}
        for i in range(len(staff_columns)):
            if type(tmp_tuple[i]) == str:
                tmp_dict[deformat_str(staff_columns[i], True)] = format_str(tmp_tuple[i])
            else:
                tmp_dict[deformat_str(staff_columns[i], True)] = tmp_tuple[i]

        staff.append(tmp_dict)

    # Return list of dicts
    return staff



#   --- UTILITY FUNCTIONS ---

def get_departments():
    db = sqlite3.connect("sql/staff.db")
    tmp_cursor = db.execute("SELECT department FROM departments")

    departments = []
    for tmp_tuple in tmp_cursor:
        departments.append(tmp_tuple[0])

    departments.sort()

    # Return list of department names
    return departments


def format_list(input_list):

    formatted_list = []
    for item in input_list:

        # Although input is type checked in format_str() for strings, still need to type check for dicts, so I can format lists of dicts
        if type(item) == str:
            item = format_str(item)
        elif type(item) == dict:
            item = format_dict(item)

        formatted_list.append(item)

    return formatted_list

def format_dict(input_dict):

    formatted_dict = {}
    for key in input_dict:

        # Input is type checked in format_str(), so no need to type check here
        formatted_dict[key] = format_str(input_dict[key])

    return formatted_dict



def format_str(input_str):

    if type(input_str) == str:
        return input_str.replace('_', ' ').title().replace('Emp ', 'Employee ').replace('It', 'IT').replace('Id', 'ID').replace('Of ', 'of ')
    return input_str


def deformat_str(input_str, is_column_name):
    # For fields in tables, the only deformatting that is necessary is .lower(), however this function gets rid of need for if statement in other functions for if type == str
    if type(input_str) == str:

        # Column names formatted with '_' replacing space
        if is_column_name:
            return input_str.lower().replace(' ', '_').replace('employee', 'emp')
        else:
            return input_str.lower()
    return input_str


def usd(x, with_cents):
    if with_cents:
        return f'${x:,.2f}'
    else:
        return f'${x:,f}'



