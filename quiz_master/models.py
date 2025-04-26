from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False, unique=True)
    email = db.Column(db.String(120), nullable=False, unique=True)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(10), nullable=False, default='user')  
    status = db.Column(db.String(10), nullable=False, default='active')  
    registered_on = db.Column(db.DateTime, default=datetime.utcnow)
    quizzes_taken = db.relationship('Scores', backref='user', lazy=True)

class Subject(db.Model):
    __tablename__ = 'subjects'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=True)
    chapters = db.relationship('Chapter', backref='subject', cascade='all, delete-orphan', lazy=True)

class Chapter(db.Model):
    __tablename__ = 'chapters'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False)
    quizzes = db.relationship('Quiz', backref='chapter', cascade='all, delete-orphan', passive_deletes=True)
    def get_question_count(self):
        count = 0
        for quiz in self.quizzes:  
            count += len(quiz.questions)
        return count

class Quiz(db.Model):
    __tablename__ = 'quizzes'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    time_duration = db.Column(db.Integer, nullable=False)
    date_of_quiz = db.Column(db.DateTime, default=datetime.utcnow)
    remarks = db.Column(db.Text, nullable=True)
    chapter_id = db.Column(db.Integer, db.ForeignKey('chapters.id', ondelete='CASCADE'))
    questions = db.relationship('Question', backref='quiz', cascade='all, delete-orphan', passive_deletes=True)
    scores = db.relationship('Scores', backref='quiz', cascade='all, delete-orphan', passive_deletes=True)

class Question(db.Model):
    __tablename__ = 'questions'
    id = db.Column(db.Integer, primary_key=True)
    question_text = db.Column(db.Text, nullable=False)
    option_a = db.Column(db.String(200), nullable=False)
    option_b = db.Column(db.String(200), nullable=False)
    option_c = db.Column(db.String(200), nullable=False)
    option_d = db.Column(db.String(200), nullable=False)
    correct_answer = db.Column(db.String(1), nullable=False)  
    quiz_id = db.Column(db.Integer, db.ForeignKey('quizzes.id'), nullable=False)

class Scores(db.Model):
    __tablename__ = 'scores'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quizzes.id'), nullable=False)
    score = db.Column(db.Integer, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

def init_db(app):
    with app.app_context():
        db.init_app(app)
        db.create_all()