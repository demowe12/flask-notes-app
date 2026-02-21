from flask import Flask, render_template, request, redirect, session, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os
import shutil
from datetime import datetime
import markdown

app = Flask(__name__)
app.secret_key = "supersecretkey"

ADMIN_ACTION_PASSWORD = "kali@123"

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

class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    tags = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'))

# ================= LOGIN =================

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and check_password_hash(user.password, request.form['password']):
            session['user_id'] = user.id
            session['username'] = user.username
            return redirect('/')
        return "Invalid credentials"
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

# ================= HOME =================

@app.route('/', methods=['GET', 'POST'])
def home():
    if 'user_id' not in session:
        return redirect('/login')

    # Add subject
    if request.method == 'POST' and request.form.get('type') == 'add_subject':
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

    subjects = Subject.query.filter_by(user_id=session['user_id']).all()
    return render_template('index.html', subjects=subjects)

# ================= DELETE SUBJECT =================

@app.route('/delete_subject/<subject_name>', methods=['POST'])
def delete_subject(subject_name):
    if 'user_id' not in session:
        return redirect('/login')

    if request.form.get('action_password') != ADMIN_ACTION_PASSWORD:
        return "Wrong admin password"

    subject = Subject.query.filter_by(
        name=subject_name,
        user_id=session['user_id']
    ).first()

    if not subject:
        return redirect('/')

    # Delete notes under subject
    Note.query.filter_by(subject_id=subject.id).delete()

    # Delete uploads folder
    folder = os.path.join('uploads', session['username'], subject_name)
    if os.path.exists(folder):
        shutil.rmtree(folder)

    # Delete subject
    db.session.delete(subject)
    db.session.commit()

    return redirect('/')

# ================= SUBJECT PAGE =================

@app.route('/subject/<name>', methods=['GET', 'POST'])
def subject_page(name):
    if 'user_id' not in session:
        return redirect('/login')

    subject = Subject.query.filter_by(
        name=name,
        user_id=session['user_id']
    ).first()

    if not subject:
        return "Subject not found"

    folder = os.path.join('uploads', session['username'], name)
    os.makedirs(folder, exist_ok=True)

    # Upload PDF
    if request.method == 'POST' and request.form.get('type') == 'pdf':
        if request.form.get('action_password') != ADMIN_ACTION_PASSWORD:
            return "Wrong admin password"

        pdf = request.files['pdf']
        if pdf:
            pdf.save(os.path.join(folder, pdf.filename))
        return redirect(f'/subject/{name}')

    # Add Note
    if request.method == 'POST' and request.form.get('type') == 'note':
        db.session.add(
            Note(
                title=request.form['title'],
                content=request.form['content'],
                tags=request.form['tags'],
                subject_id=subject.id
            )
        )
        db.session.commit()
        return redirect(f'/subject/{name}')

    files = os.listdir(folder)
    notes = Note.query.filter_by(subject_id=subject.id)\
                      .order_by(Note.created_at.desc())\
                      .all()

    for note in notes:
        note.rendered_content = markdown.markdown(
            note.content, extensions=['fenced_code']
        )

    return render_template(
        'subject.html',
        name=name,
        files=files,
        notes=notes
    )

# ================= RUN =================

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
if __name__ == "__main__":
    app.run()