from flask import Flask, render_template, request, redirect, session, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os

# ================= APP SETUP =================
app = Flask(__name__)
app.secret_key = "supersecretkey"

# 🔒 PASSWORD REQUIRED FOR ADD / UPLOAD
ADMIN_ACTION_PASSWORD = "kali@123"

# ================= DATABASE =================
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///notes.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ================= MODELS =================
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

class Subject(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

# ================= LOGIN =================
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(
            username=request.form['username']
        ).first()

        if user and check_password_hash(user.password, request.form['password']):
            session['user_id'] = user.id
            session['username'] = user.username
            return redirect('/')
        return "Invalid credentials"

    return render_template('login.html')

# ================= LOGOUT =================
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

# ================= HOME =================
@app.route('/', methods=['GET', 'POST'])
def home():
    if 'user_id' not in session:
        return redirect('/login')

    if request.method == 'POST':
        if request.form.get('action_password') != ADMIN_ACTION_PASSWORD:
            return "Wrong admin password"

        db.session.add(
            Subject(
                name=request.form['subject'],
                user_id=session['user_id']
            )
        )
        db.session.commit()
        return redirect('/')

    subjects = Subject.query.filter_by(
        user_id=session['user_id']
    ).all()

    return render_template('index.html', subjects=subjects)

# ================= SUBJECT PAGE + UPLOAD =================
@app.route('/subject/<name>', methods=['GET', 'POST'])
def subject_page(name):
    if 'user_id' not in session:
        return redirect('/login')

    folder = os.path.join('uploads', session['username'], name)
    os.makedirs(folder, exist_ok=True)

    if request.method == 'POST':
        if request.form.get('action_password') != ADMIN_ACTION_PASSWORD:
            return "Wrong admin password"

        pdf = request.files['pdf']
        if pdf:
            pdf.save(os.path.join(folder, pdf.filename))
        return redirect(f'/subject/{name}')

    files = os.listdir(folder)
    return render_template('subject.html', name=name, files=files)

# ================= SERVE FILES =================
@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory('uploads', filename)

# ================= RUN =================
if __name__ == '__main__':
    with app.app_context():
        db.create_all()

        if not User.query.filter_by(username="admin").first():
            db.session.add(
                User(
                    username="admin",
                    password=generate_password_hash("1234")
                )
            )
            db.session.commit()

    app.run(debug=True)
