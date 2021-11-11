from flask import render_template, redirect, url_for, request, g, session
from app import webapp
import bcrypt
import smtplib
import mysql.connector
from app.config import db_config

webapp.secret_key = 'my_secret_key'

def connect_to_database():
    return mysql.connector.connect(user=db_config['user'], 
                                    password=db_config['password'], 
                                    host=db_config['host'],
                                    database=db_config['database'])

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = connect_to_database()
    return db

@webapp.route('/login', methods=['GET','POST'])
def login():
    '''login() - used for user login.
    If user is already logged in, redirect to home page. Otherwise get user data
    from submitted form and do basic validation. If user is found, the password is checked,
    if password is correct, user is re-directed to homepage.
    '''
    if session.get('logged_in'):
        return redirect(url_for('home_page'))

    if request.method == 'POST':
        if request.form.get('forgot') == 'Forgot Password':
            return redirect(url_for('forgot_password'))
        username = request.form['username']
        password = request.form['password']
    
        if username == "" or password == "":
            error_msg = "Error: All fields are required."
            return render_template("login.html", error_msg=error_msg)
        con = get_db()
        cursor = con.cursor()
        query = "SELECT * FROM users WHERE username= %s"
        cursor.execute(query,(username,))
        result = cursor.fetchone()
        if not result:
            error_msg = "Error: Username not found. Enter correct username or contact administrator to register account."
            return render_template("login.html", error_msg=error_msg)
        username = result[1]
        salt = result[2]
        hashed = result[3]
        admin = result[5]
        if hashed == bcrypt.hashpw(password.encode(), salt):
            session['username'] = username
            session['admin'] = admin
            session['logged_in'] = True
            return redirect(url_for('home_page'))
        else:
            error_msg = "Error: Incorrect password. Try entering your password again, or use the 'Forgot Password' button."
            return render_template("login.html", error_msg=error_msg)
    return render_template('login.html')

@webapp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    '''forgot_password() - used to recover user password, if password is forgotten.
    Receives user name and confirms if user exists. If user exists, sends email to 
    user with a randomly generated recovery code. Recovery code is added to database,
    corresponding to username.
    '''
    if request.method == 'POST':
        if request.form.get('login-page') == 'Return to Login':
            return redirect(url_for('login'))
        elif request.form.get('recover') == 'Recover Password':
            username = request.form.get('username')
            con = get_db()
            cursor = con.cursor()
            query = "SELECT * FROM users WHERE username=%s"
            cursor.execute(query,(username,))
            result = cursor.fetchone()
            if not result:
                error_msg = "Error: Username not found. Enter correct username or contact administrator to register account."
                return render_template("forgot-password.html", error_msg=error_msg)
            email = result[4]
            code = bcrypt.gensalt()
            x = 'Your recovery code is:' + str(code)
            server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
            server.login("t.alvi.ece1779@gmail.com", "uoft.ece1779")
            server.sendmail(
                "t.alvi.ece1779@gmail.com",
                email,
                x)
            query = '''INSERT into recover (username, recoverykey) VALUES (%s, %s)'''
            cursor.execute(query, (username, code))
            con.commit()
    return render_template('forgot-password.html') 
@webapp.route('/recover-password', methods=['GET', 'POST'])
def recover_password():
    '''recover_password() - used to change password based on recovery code provided
    to user via email. 
    '''
    if request.method == 'POST':
        username = request.form.get('username')
        recovery_code = request.form.get('code')
        password = request.form.get('password')
        con = get_db()
        cursor = con.cursor()
        query = '''SELECT * FROM recover WHERE username=%s AND recoverykey=%s'''
        cursor.execute(query,(username,recovery_code))
        result = cursor.fetchone()
        if not result:
            error_msg = "Username or recovery code incorrect."
            return render_template("recover-password.html", error_msg=error_msg)
        new_salt = bcrypt.gensalt()
        new_hash = bcrypt.hashpw(password.encode(), new_salt)
        query = '''UPDATE users SET salt=%s, password=%s WHERE username=%s'''
        cursor.execute(query, (new_salt, new_hash, username,))
        con.commit()
        render_template('login.html', error_msg='Password changed. Please login with new password.')
    return render_template('recover-password.html')

@webapp.route('/change-password', methods=['GET', 'POST'])
def change_password():
    '''change_password() - used to change user password, if user is logged in
    Checks if used is logged in. If so form request for new password is received,
    and old password enter is compared with existing password in the database. If 
    the passwords match, the new user password is hashed and stored in the database.
    '''   
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    if request.method == 'POST':
        username = session["username"]
        existing_password = request.form['password1']
        new_password = request.form['password2']
        con = get_db()
        cursor = con.cursor()
        query = "SELECT * FROM users WHERE username=%s"
        cursor.execute(query,(username,))
        result = cursor.fetchone()
        salt = result[2]
        hashed = result[3]
        if not hashed == bcrypt.hashpw(existing_password.encode(), salt):
            error_msg = "Password you entered doesn't match your existing password."
            return render_template("change-password.html", error_msg=error_msg)
        new_salt = bcrypt.gensalt()
        new_hash = bcrypt.hashpw(new_password.encode(), new_salt)
        query = '''UPDATE users SET salt=%s, password=%s WHERE username=%s'''
        cursor.execute(query, (new_salt, new_hash, username,))
        con.commit()
        return render_template("change-password.html", error_msg='Password Changed!')
    return render_template('change-password.html')     

@webapp.route('/logout')
def logout():
    '''logout()
    Logs user out by removing all user session information. 
    '''
    session.pop('logged_in', None)
    session.pop('username', None)
    session.pop('image_uploaded', None)
    session.pop('admin', None)
    return redirect(url_for('login'))

@webapp.route('/register/', methods=['GET', 'POST'])    
def register():
    """register()
    Function checks if a user is logged in and user admin privileges via user session
    information. Username, password and email are obtained from form submitted by admin.
    If any of the fields are empty an error is raised. Database is checked, if existing
    user information is already present, an error is returned. User password is hashed
    before being stored in the database along with the salt value.
    Otherwise, new user is registered by saving information in database.
    """
    if session.get('logged_in') == True and session.get('admin') == True:
        print('Admin Access')
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        email = request.form.get('email')
        admin_access = request.form.get('admin') != None

        if username == "" or password == "" or email == "":
            error_msg = "Error: All fields are required."
            return render_template("register.html", error_msg=error_msg)
        con = get_db()
        cursor = con.cursor()
        query = "SELECT * FROM users WHERE username=%s"
        cursor.execute(query,(username,))
        result = cursor.fetchone()
        if result:
            error_msg = "User already exists. Enter a different username."
            return render_template("register.html", error_msg=error_msg)
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode(), salt)   
        query = '''INSERT INTO users (username, salt, password, email, admin) 
                                VALUES (%s, %s, %s, %s, %s)'''                         
        cursor.execute(query,(username, salt, hashed, email, admin_access))
        con.commit()
    return render_template('register.html')

@webapp.route('/api/register', methods=['POST'])    
def register_user():
    """register_user()
    Function checks if 'POST' method has been used to submit a form. 
    Username, and password are obtained from the submitted request.
    If any of the fields are empty an error is raised. Database is checked, if existing
    user information is already present, an error is returned.
    Otherwise, a new user is registered by saving information in database. Provided password is
    hashed before being stored in the database.
    Error or success is returned to the server as a JSON object. 
    """
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == "" or password == "":
            error_msg = "Username or password are empty!"
            return {
                    "success": False,
                    "error":
                    {
                        "code": 400,
                        "message": error_msg
                        
                    }
                }
                
        con = get_db()
        cursor = con.cursor()
        query = "SELECT * FROM users WHERE username=%s"
        cursor.execute(query,(username,))
        result = cursor.fetchone()
        if result:
            error_msg = "User already exists. Enter a different username."
            return {
                    "success": False,
                    "error":
                    {
                        "code": 400,
                        "message": error_msg
                        
                    }
                }        
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode(), salt)   
        query = '''INSERT INTO users (username, salt, password) 
                                VALUES (%s, %s, %s)'''                         
        cursor.execute(query,(username, salt, hashed))
        con.commit()
        return { "success": True}
    