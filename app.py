from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from werkzeug.utils import secure_filename
import os
import shutil
from PIL import Image
import bcrypt
import datetime
import random
from random import choice

app = Flask(__name__)
app.secret_key = 'supersecretkey'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)

    def __repr__(self):
        return f'<User {self.username}>'


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def create_thumbnail(image_path):
    size = (200, 200)
    image = Image.open(image_path)
    image.thumbnail(size)
    thumb_path = image_path.rsplit('.', 1)[0] + '.thumb.jpg'
    image.save(thumb_path, "JPEG")
    return thumb_path

@app.context_processor
def inject_current_year():
    return {'current_year': datetime.datetime.now().year}

@app.route('/')
def index():
    categories = {}
    for root, dirs, files in os.walk(app.config['UPLOAD_FOLDER']):
        relative_path = os.path.relpath(root, app.config['UPLOAD_FOLDER'])
        if relative_path == '.':
            continue
        category = relative_path
        if category:
            categories[category] = [os.path.join(root, file) for file in files if 'thumb' in file]
    return render_template('index.html', categories=categories)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists. Please choose a different one.', 'danger')
            return redirect(url_for('register'))
        
        new_user = User(username=username, password_hash=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        
        flash('Account created successfully. You can now login.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')



@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password'].encode('utf-8')
        user = User.query.filter_by(username=username).first()
        if user and bcrypt.checkpw(password, user.password_hash):
            session['logged_in'] = True
            session['username'] = username
            flash('Login successful', 'success')
            return redirect(url_for('upload'))
        else:
            flash('Invalid credentials', 'danger')
    return render_template('login.html')

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        file = request.files['image']
        name = request.form.get('name')
        category = request.form.get('category')
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            if name:
                filename = secure_filename(name + '.' + filename.rsplit('.', 1)[1].lower())
            category_path = os.path.join(app.config['UPLOAD_FOLDER'], category)
            os.makedirs(category_path, exist_ok=True)
            filepath = os.path.join(category_path, filename)
            file.save(filepath)
            create_thumbnail(filepath)
            flash('Image uploaded successfully', 'success')
            return redirect(url_for('upload'))
    return render_template('upload.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/delete_album/<category>', methods=['POST'])
def delete_album(category):
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    category_path = os.path.join(app.config['UPLOAD_FOLDER'], category)
    if os.path.exists(category_path):
        shutil.rmtree(category_path)
        flash(f'Album "{category}" deleted successfully', 'success')
    else:
        flash(f'Album "{category}" not found', 'danger')
    return redirect(url_for('index'))

@app.route('/delete_image/<category>/<image>', methods=['POST'])
def delete_image(category, image):
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    image_path = os.path.join(app.config['UPLOAD_FOLDER'], category, image)
    thumb_path = os.path.join(app.config['UPLOAD_FOLDER'], category, image.rsplit('.', 1)[0] + '.thumb.jpg')
    if os.path.exists(image_path):
        os.remove(image_path)
        if os.path.exists(thumb_path):
            os.remove(thumb_path)
        flash(f'Image "{image}" deleted successfully', 'success')
    else:
        flash(f'Image "{image}" not found', 'danger')
    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('username', None)
    flash('You have been logged out', 'success')
    return redirect(url_for('index'))

@app.route('/rps_game', methods=['GET', 'POST'])
def rps_game():
    images = {
        'rock': url_for('static', filename='images/rock.png'),
        'paper': url_for('static', filename='images/paper.png'),
        'scissors': url_for('static', filename='images/scissors.png')
    }
    
    if request.method == 'POST':
        user_choice = request.form['choice']
        computer_choice = random.choice(['rock', 'paper', 'scissors'])
        
        if user_choice == computer_choice:
            result = 'It\'s a tie!'
        elif (user_choice == 'rock' and computer_choice == 'scissors') or \
             (user_choice == 'paper' and computer_choice == 'rock') or \
             (user_choice == 'scissors' and computer_choice == 'paper'):
            result = 'You win!'
        else:
            result = 'Computer wins!'
        
        return render_template('rps_result.html', user_choice=user_choice, 
                               computer_choice=computer_choice, result=result, images=images)
    
    return render_template('rps_game.html', images=images)

@app.route('/games')
def games():
    return render_template('games.html')

word_list = ['apple', 'berry', 'chery', 'grape', 'mango']

@app.route('/wordle', methods=['GET', 'POST'])
def wordle():
    if 'wordle_word' not in session:
        session['wordle_word'] = random.choice(word_list)
        session['attempts'] = []
        session['max_attempts'] = 6
    
    wordle_word = session['wordle_word']
    attempts = session['attempts']
    max_attempts = session['max_attempts']
    result = None
    feedback = None
    attempts_left = max_attempts - len(attempts)
    
    if request.method == 'POST':
        user_guess = request.form['guess'].lower()
        attempts.append(user_guess)
        session['attempts'] = attempts
        
        if user_guess == wordle_word:
            result = 'Congratulations! You guessed the word.'
            return redirect(url_for('wordle_end', result=result))
        elif len(attempts) >= max_attempts:
            result = f'Sorry, you have used all your attempts. The word was "{wordle_word}".'
            return redirect(url_for('wordle_end', result=result))
        else:
            feedback = provide_feedback(user_guess, wordle_word)
            result = 'Incorrect guess. Try again.'

        attempts_left = max_attempts - len(attempts)

    
    return render_template('wordle.html', feedback= feedback, result=result, attempts=attempts, attempts_left=attempts_left, max_attempts=max_attempts)


@app.route('/wordle_end')
def wordle_end():
    result = request.args.get('result', 'Game over.')
    return render_template('wordle_end.html', result=result)

@app.route('/reset')
def reset():
    session.pop('wordle_word', None)
    session.pop('attempts', None)
    return redirect(url_for('wordle'))

def provide_feedback(guess, word):
    feedback = []
    for g, w in zip(guess, word):
        if g == w:
            feedback.append(f'{g.upper()} (correct)')
        elif g in word:
            feedback.append(f'{g.upper()} (wrong position)')
        else:
            feedback.append(f'{g.upper()} (not in word)')
    return feedback

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
