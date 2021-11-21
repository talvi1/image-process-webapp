from flask import render_template, redirect, url_for, request, g, session
import requests
from app import webapp
import uuid
import mysql.connector
import os
import bcrypt
from app.config import db_config
from wand.image import Image
import boto3

s3 = boto3.client('s3')
mybucket = 'webapp-images-ece1779'
s3address = 'https://webapp-images-ece1779.s3.amazonaws.com/'
webapp.config['UPLOAD_PATH'] = 'app/static' 
webapp.config['MAX_CONTENT_LENGTH'] = 10*1024*1024

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

@webapp.route('/', methods=['GET'])
@webapp.route('/home', methods=['GET'])
def home_page():
    """ home_page() - shows user homepage.
    """
    if session.get('logged_in'):
        print(session.get('username'))
        return render_template('home.html', username=session.get('username'))
    else:
        return redirect(url_for('login'))
    return render_template('home.html')

@webapp.route('/upload', methods=['GET','POST'])
def upload_image():
    """upload_image() - uploads a single user image via url or local files. 
    Function checks if user is logged in. If user is logged, checks for POST request
    for either URL submission or local file upload. A random file # is assigned to the file name.
    Add_image() helper function is used to add the image refeence to the database. Function 
    redirects to webpage to show uploaded image.
    """
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    if request.method == "POST":
        file_uuid = str(uuid.uuid4())
        if request.form.get('url') == 'Submit':
            image_url = request.form.get('image-url')
            print(os.path.splitext(image_url))
            file, file_ext = os.path.splitext(image_url)
            response = requests.get(image_url)
            image_path = os.path.join(webapp.config['UPLOAD_PATH'], file_uuid + file_ext)
            image_name = file_uuid + file_ext
            file = open(image_path, 'wb')
            file.write(response.content)
            file.close()
            session["image_uploaded"] = image_name
            add_image()
            return redirect(url_for('show_image'))
            
        elif request.form.get('image') == 'Submit':
            image_file = request.files['image']
            if image_file.filename == '':
                error_msg = "No image selected for upload."
                return render_template('upload-image.html', error_msg=error_msg)
            file, file_ext = os.path.splitext(image_file.filename)
            image_path = os.path.join(webapp.config['UPLOAD_PATH'], file_uuid + file_ext)
            image_name = file_uuid + file_ext
            image_file.save(image_path)
            session["image_uploaded"] = image_name
            add_image()
            s3_upload()
            return redirect(url_for('show_image'))
    return render_template('upload-image.html')

def s3_upload():
    image_name = session["image_uploaded"]
    fname, fext = os.path.splitext(session["image_uploaded"])
    fpath = os.path.join(webapp.config['UPLOAD_PATH'] + '/', session["image_uploaded"])
    fname_blur = os.path.join(webapp.config['UPLOAD_PATH'] + '/', fname +'-blur'+ fext)
    fname_shade = os.path.join(webapp.config['UPLOAD_PATH'] + '/', fname +'-shade'+ fext)
    fname_spread = os.path.join(webapp.config['UPLOAD_PATH'] + '/', fname +'-spread'+ fext)
    with Image(filename=fpath) as img:
        img.blur(radius=0, sigma=8)
        img.save(filename=fname_blur)
    with Image(filename=fpath) as img:
        img.shade(gray=True, azimuth=286.0, elevation=45.0)
        img.save(filename=fname_shade)
    with Image(filename=fpath) as img:
        img.spread(radius=8.0)
        img.save(filename=fname_spread)
    s3.upload_file(fpath, mybucket, image_name)
    s3.upload_file(fname_blur, mybucket, fname+'-blur'+fext)
    s3.upload_file(fname_shade, mybucket, fname+'-shade'+fext)
    s3.upload_file(fname_spread, mybucket, fname+'-spread'+fext)

def add_image():
    """add_image() - helper function to insert uploaded image reference 
    into database and save image transformations into local directory.
    """
    con = get_db()
    cursor = con.cursor()
    query = '''INSERT INTO images (username, image) 
                                VALUES (%s, %s)'''                         
    cursor.execute(query,(session["username"], session["image_uploaded"]))
    con.commit()


@webapp.route('/image-uploaded', methods=['GET'])
def show_image():
    """show_image() - shows uploaded image and corresponding transformations
    on webpage after an image has been uploaded.
    """
    full_filename = session["image_uploaded"]
    fname, fext = os.path.splitext(full_filename)
    image_blur = fname+'-blur'+fext
    image_shade = fname+'-shade'+fext
    image_spread = fname+'-spread'+fext

    return render_template('show-image.html', username=session["username"], 
                        imagename=full_filename, blur=image_blur, shade=image_shade, 
                        spread=image_spread)
    
@webapp.route('/view-images', methods=['GET'])
def view_images():
    """view_image() - allows user to view all images uploaded in the past.
    """
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    username = session["username"]
    con = get_db()
    cursor = con.cursor()
    query = '''SELECT image FROM images WHERE username =%s'''
    cursor.execute(query, (username,))
    result = cursor.fetchall()
    image_addr = []
    for i in range(len(result)):
        addr = s3address + result[i][0]
        image_addr.append([addr, result[i][0]])
    return render_template('view-images.html', image_addr=image_addr)
@webapp.route('/transformation/<variable>', methods=['GET'])
def show_transformations(variable):
    """show_transformations() - shows image transformations if an image is clicked on.
    """   
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    file, file_ext = os.path.splitext(variable)
    print(file)
    print(file_ext)
    image_orig = s3address + file + file_ext
    image_blur = s3address + file +'-blur'+ file_ext
    image_shade = s3address + file +'-shade'+ file_ext
    image_spread = s3address + file +'-spread'+ file_ext
    return render_template('transformed.html', imagename=image_orig, blur=image_blur, shade=image_shade, 
                        spread=image_spread)

@webapp.route('/api/upload', methods=['POST'])
def api_upload():
    """api_upload() - api interface for an image to be uploaded for a single user. 
    Validation for form data is completed and then used identity is confirmed before 
    saving image. JSON objects are returned confirming if image has been uploaded successfully.
    """
    if request.method == "POST":
        file_uuid = str(uuid.uuid4())
        username = request.form.get('username')
        password = request.form.get('password')
        image_file = request.files['file']
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
        if image_file.filename == '':
            error_msg = "No image selected for upload."
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
        if not result:
            error_msg = "Error: Username not found. Enter correct username or contact administrator to register account."
            return {
                "success": False,
                "error":
                {
                    "code": 400,
                    "message": error_msg    
                }
                }
        username = result[1]
        salt = result[2]
        hashed = result[3]
        if not hashed == bcrypt.hashpw(password.encode(), salt):
            error_msg = "User password is not correct."
            return {
                "success": False,
                "error":
                {
                "code": 400,
                "message": error_msg        
                }
                }
        file, file_ext = os.path.splitext(image_file.filename)
        image_path = os.path.join(webapp.config['UPLOAD_PATH'], file_uuid + file_ext)
        image_name = file_uuid + file_ext
        image_file.save(image_path)
        con = get_db()
        cursor = con.cursor()
        query = '''INSERT INTO images (username, image) 
                                VALUES (%s, %s)'''                         
        cursor.execute(query,(username, image_name))
        con.commit()
        fname_blur = os.path.join(webapp.config['UPLOAD_PATH'] + '/', file_uuid +'-blur'+ file_ext)
        fname_shade = os.path.join(webapp.config['UPLOAD_PATH'] + '/', file_uuid +'-shade'+ file_ext)
        fname_spread = os.path.join(webapp.config['UPLOAD_PATH'] + '/', file_uuid +'-spread'+ file_ext)
        with Image(filename=image_path) as img:
            original_size = os.path.getsize(image_path)
            img.blur(radius=0, sigma=8)
            img.save(filename=fname_blur)
            blur_size = os.path.getsize(fname_blur)
        with Image(filename=image_path) as img:
            img.shade(gray=True, azimuth=286.0, elevation=45.0)
            img.save(filename=fname_shade)
            shade_size = os.path.getsize(fname_shade)
        with Image(filename=image_path) as img:
            img.spread(radius=8.0)
            spread_size = img.size
            img.save(filename=fname_spread)
            spread_size = os.path.getsize(fname_spread)
        s3.upload_file(image_path, mybucket, image_name)
        s3.upload_file(fname_blur, mybucket, file_uuid+'-blur'+file_ext)
        s3.upload_file(fname_shade, mybucket, file_uuid+'-shade'+file_ext)
        s3.upload_file(fname_spread, mybucket, file_uuid+'-spread'+file_ext)
        
        return {
                "success": True,
                "payload":
                {
                "original_size": original_size,
                "blur_size": blur_size,
                "shade_size": shade_size,
                "spread_size": spread_size         
                }
                }
            
@webapp.route('/health-check', methods=['GET', 'POST'])
def health_check():
    """
    """   
    return {
                "Status": 200
                }
