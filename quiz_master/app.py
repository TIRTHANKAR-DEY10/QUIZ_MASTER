
from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, Subject, Chapter, Quiz, Question, Scores, init_db
import matplotlib.pyplot as plt
from io import BytesIO
import base64
from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tirthankar.sqlite'  # Database URI
app.config['SECRET_KEY'] = 'secret_key'

# Initialize the database
init_db(app)

# Hardcoded admin credentials 
ADMIN_CREDENTIALS = {'username': 'tirtha', 'password': 'tirtha10'}

def get_chart_base64():
    """Convert matplotlib plot to base64 image"""
    buffer = BytesIO()
    plt.savefig(buffer, format='png', bbox_inches='tight', dpi=100)
    buffer.seek(0)
    return base64.b64encode(buffer.getvalue()).decode('utf-8')


# Home Page
@app.route('/')
def home():
    return render_template('home.html')

# Register User
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if password != confirm_password:
            flash('Passwords do not match!', 'danger')
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

        new_user = User(username=username, email=email, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()

        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('user_login'))

    return render_template('user_registration.html')

# Admin Login
@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == ADMIN_CREDENTIALS['username'] and password == ADMIN_CREDENTIALS['password']:
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        flash('Invalid Admin Credentials', 'danger')
    return render_template('admin_login.html')

# User Login
@app.route('/user_login', methods=['GET', 'POST'])
def user_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            if user.status == 'blocked': 
                flash('Your account has been blocked by admin', 'danger')
                return redirect(url_for('user_login'))
                
            session['user_id'] = user.id
            flash('Login successful!', 'success')
            return redirect(url_for('user_dashboard'))
        else:
            flash('Login failed. Check your credentials and try again.', 'danger')

    return render_template('user_login.html')

# User Dashboard
@app.route('/user_dashboard')
def user_dashboard():
    if 'user_id' not in session:
        flash('Please login to access the dashboard.', 'danger')
        return redirect(url_for('user_login'))
        
    user = User.query.get(session['user_id'])
    if user.status == 'blocked': 
        flash('Your account has been blocked by admin', 'danger')
        return redirect(url_for('user_logout'))
        
    quizzes = Quiz.query.all()
    return render_template('user_dashboard.html', quizzes=quizzes)

# Quiz Details
@app.route('/quiz_details/<int:quiz_id>')
def quiz_details(quiz_id):
    if 'user_id' not in session:
        flash('Please login to view quiz details.', 'danger')
        return redirect(url_for('user_login'))

    quiz = Quiz.query.get_or_404(quiz_id)
    return render_template('quiz_details.html', quiz=quiz)

# Quiz Attempt
@app.route('/quiz_attempt/<int:quiz_id>', methods=['GET', 'POST'])
def quiz_attempt(quiz_id):
    if 'user_id' not in session:
        flash('Please login to attempt the quiz.', 'danger')
        return redirect(url_for('user_login'))
        
    user = User.query.get(session['user_id'])
    if user.status == 'blocked': 
        flash('Your account has been blocked by admin', 'danger')
        return redirect(url_for('user_dashboard'))
        
    quiz = Quiz.query.get_or_404(quiz_id)
    return render_template('quiz_attempt.html', quiz=quiz)

# Submit Quiz
@app.route('/submit_quiz/<int:quiz_id>', methods=['POST'])
def submit_quiz(quiz_id):
    if 'user_id' not in session:
        flash('Please login to submit the quiz.', 'danger')
        return redirect(url_for('user_login'))

    quiz = Quiz.query.get_or_404(quiz_id)
    user_id = session['user_id']

    score = 0
    for question in quiz.questions:
        selected_option = request.form.get(f'question_{question.id}')
        if selected_option == question.correct_answer:
            score += 1

    new_score = Scores(user_id=user_id, quiz_id=quiz.id, score=score)
    db.session.add(new_score)
    db.session.commit()

    flash(f'Quiz submitted! Your score is {score}/{len(quiz.questions)}', 'success')
    return redirect(url_for('quiz_scores'))

# Quiz Scores
@app.route('/quiz_scores')
def quiz_scores():
    if 'user_id' not in session:
        flash('Please login to view your scores.', 'danger')
        return redirect(url_for('user_login'))

    user_id = session['user_id']
    scores = Scores.query.filter_by(user_id=user_id).all()
    return render_template('quiz_scores.html', scores=scores)

# Admin Dashboard
@app.route('/admin_dashboard')
def admin_dashboard():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    users = User.query.all()
    return render_template('admin_dashboard.html', users=users)

# Block/Unblock Users
@app.route('/admin/block_user/<int:user_id>')
def block_user(user_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    user = User.query.get(user_id)
    if user:
        user.status = 'blocked'
        db.session.commit()
        flash(f'User {user.username} has been blocked', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/unblock_user/<int:user_id>')
def unblock_user(user_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    user = User.query.get(user_id)
    if user:
        user.status = 'active'
        db.session.commit()
        flash(f'User {user.username} has been unblocked', 'success')
    return redirect(url_for('admin_dashboard'))

# Manage Subjects
@app.route('/manage_subjects')
def manage_subjects():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    subjects = Subject.query.all()
    return render_template('manage_subjects.html', subjects=subjects)

# CRUD Subject
@app.route('/create_subject', methods=['GET', 'POST'])
def create_subject():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        new_subject = Subject(name=name, description=description)
        db.session.add(new_subject)
        db.session.commit()
        flash('Subject created successfully!', 'success')
        return redirect(url_for('manage_subjects'))
    return render_template('create_subject.html')

@app.route('/edit_subject/<int:id>', methods=['GET', 'POST'])
def edit_subject(id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    subject = Subject.query.get(id)
    if request.method == 'POST':
        subject.name = request.form.get('name')
        subject.description = request.form.get('description')
        db.session.commit()
        flash('Subject updated successfully!', 'success')
        return redirect(url_for('manage_subjects'))
    return render_template('edit_subject.html', subject=subject)

@app.route('/delete_subject/<int:id>')
def delete_subject(id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    subject = Subject.query.get(id)
    db.session.delete(subject)
    db.session.commit()
    flash('Subject deleted successfully!', 'success')
    return redirect(url_for('manage_subjects'))

#CRUD Chapter
@app.route('/create_chapter/<int:subject_id>', methods=['GET', 'POST'])
def create_chapter(subject_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        new_chapter = Chapter(name=name, subject_id=subject_id)
        db.session.add(new_chapter)
        db.session.commit()
        flash('Chapter created successfully!', 'success')
        return redirect(url_for('manage_subjects'))
    
    subject = Subject.query.get(subject_id)
    return render_template('create_chapter.html', subject_id=subject_id, subject=subject)

@app.route('/edit_chapter/<int:id>', methods=['GET', 'POST'])
def edit_chapter(id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    chapter = Chapter.query.get_or_404(id)
    subjects = Subject.query.all()
    
    if request.method == 'POST':
        name = request.form.get('name')
        subject_id = request.form.get('subject_id')
        
        if not name or not subject_id:
            flash('All fields are required!', 'danger')
        else:
            chapter.name = name
            chapter.subject_id = subject_id
            db.session.commit()
            flash('Chapter updated successfully!', 'success')
            return redirect(url_for('manage_subjects'))
    
    return render_template('edit_chapter.html', chapter=chapter, subjects=subjects)

@app.route('/delete_chapter/<int:id>')
def delete_chapter(id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    chapter = Chapter.query.get(id)
    if chapter:
        db.session.delete(chapter)
        db.session.commit()
        flash('Chapter deleted successfully!', 'success')
    
    return redirect(url_for('manage_subjects'))

# Manage Quizzes
@app.route('/manage_quizzes')
def manage_quizzes():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    quizzes = Quiz.query.all()
    chapters = Chapter.query.all()
    return render_template('manage_quizzes.html', quizzes=quizzes, chapters=chapters)

# CRUD Quiz 
@app.route('/create_quiz', methods=['GET', 'POST'])
def create_quiz():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    chapters = Chapter.query.all()
    
    if request.method == 'POST':
        title = request.form.get('title')
        time_duration = request.form.get('time_duration')
        remarks = request.form.get('remarks')
        chapter_id = request.form.get('chapter_id')
        
        if not all([title, time_duration, chapter_id]):
            flash('Title, duration and chapter are required!', 'danger')
        else:
            try:
                new_quiz = Quiz(title=title, time_duration=int(time_duration), remarks=remarks, chapter_id=chapter_id, date_of_quiz=datetime.utcnow())
                db.session.add(new_quiz)
                db.session.commit()
                flash('Quiz created successfully!', 'success')
                return redirect(url_for('manage_quizzes'))
            except ValueError:
                flash('Duration must be a number!', 'danger')
    
    return render_template('create_quiz.html', chapters=chapters)

@app.route('/edit_quiz/<int:id>', methods=['GET', 'POST'])
def edit_quiz(id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    quiz = Quiz.query.get(id)
    if not quiz:
        flash('Quiz not found!', 'danger')
        return redirect(url_for('manage_quizzes'))
    
    if request.method == 'POST':
        quiz.title = request.form.get('title')
        quiz.time_duration = request.form.get('time_duration')
        quiz.remarks = request.form.get('remarks')
        quiz.chapter_id = request.form.get('chapter_id')
        db.session.commit()
        flash('Quiz updated successfully!', 'success')
        return redirect(url_for('manage_quizzes'))
    
    chapters = Chapter.query.all()
    return render_template('edit_quiz.html', quiz=quiz, chapters=chapters)

@app.route('/delete_quiz/<int:id>')
def delete_quiz(id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    quiz = Quiz.query.get(id)
    db.session.delete(quiz)
    db.session.commit()
    flash('Quiz deleted successfully!', 'success')
    return redirect(url_for('manage_quizzes'))

# CRUD QUESTION
@app.route('/create_question/<int:quiz_id>', methods=['GET', 'POST'])
def create_question(quiz_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    if request.method == 'POST':
        question_text = request.form.get('question_text')
        option_a = request.form.get('option_a')
        option_b = request.form.get('option_b')
        option_c = request.form.get('option_c')
        option_d = request.form.get('option_d')
        correct_answer = request.form.get('correct_answer')
        new_question = Question(
            question_text=question_text,
            option_a=option_a,
            option_b=option_b,
            option_c=option_c,
            option_d=option_d,
            correct_answer=correct_answer,
            quiz_id=quiz_id
        )
        db.session.add(new_question)
        db.session.commit()
        flash('Question created successfully!', 'success')
        return redirect(url_for('manage_quizzes'))
    
    quiz = Quiz.query.get(quiz_id)
    return render_template('create_question.html', quiz_id=quiz_id, quiz=quiz)

@app.route('/edit_question/<int:id>', methods=['GET', 'POST'])
def edit_question(id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    question = Question.query.get(id)
    if not question:
        flash('Question not found!', 'danger')
        return redirect(url_for('manage_quizzes'))
    
    if request.method == 'POST':
        question.question_text = request.form.get('question_text')
        question.option_a = request.form.get('option_a')
        question.option_b = request.form.get('option_b')
        question.option_c = request.form.get('option_c')
        question.option_d = request.form.get('option_d')
        question.correct_answer = request.form.get('correct_answer')
        question.quiz_id = request.form.get('quiz_id')
        db.session.commit()
        flash('Question updated successfully!', 'success')
        return redirect(url_for('manage_quizzes'))
    
    quizzes = Quiz.query.all()
    return render_template('edit_question.html', question=question, quizzes=quizzes)

@app.route('/delete_question/<int:id>')
def delete_question(id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    question = Question.query.get(id)
    db.session.delete(question)
    db.session.commit()
    flash('Question deleted successfully!', 'success')
    return redirect(url_for('manage_quizzes'))

# Admin Search
@app.route('/admin_search', methods=['GET', 'POST'])
def admin_search():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    search_results = None
    search_type = None
    
    if request.method == 'POST':
        search_type = request.form.get('search_type')
        query = request.form.get('search_query').strip()
        
        if search_type == 'users':
            search_results = User.query.filter(User.username.ilike(f'%{query}%')).all()
        elif search_type == 'subjects':
            search_results = Subject.query.filter(Subject.name.ilike(f'%{query}%')).all()
        elif search_type == 'quizzes':
            search_results = Quiz.query.join(Chapter).filter(Quiz.title.ilike(f'%{query}%')).all()
    
    return render_template('admin_search.html', 
                         search_results=search_results,
                         search_type=search_type)

# User Search
@app.route('/user_search', methods=['GET', 'POST'])
def user_search():
    if 'user_id' not in session:
        return redirect(url_for('user_login'))
    
    search_results = None
    
    if request.method == 'POST':
        search_type = request.form.get('search_type')
        query = request.form.get('search_query').strip()
        
        if search_type == 'chapters':
            search_results = Quiz.query.join(Chapter)\
                .filter(Chapter.name.ilike(f'%{query}%')).all()
    
    return render_template('user_search.html', 
                         search_results=search_results)


# Admin Summary Route
@app.route('/admin_summary')
def admin_summary():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    # 1. Subject-wise top scores
    subjects = Subject.query.all()
    subject_data = []
    for subject in subjects:
        scores = []
        for chapter in subject.chapters:
            for quiz in chapter.quizzes:
                if quiz.scores:
                    scores.extend([s.score for s in quiz.scores])
        subject_data.append({
            'name': subject.name,
            'top_score': max(scores) if scores else 0,
            'attempts': len(scores)
        })
    
    plt.figure(figsize=(10,5))
    bars = plt.bar(
        [s['name'] for s in subject_data],
        [s['top_score'] for s in subject_data],
        color=['#4e79a7','#f28e2b','#e15759']
    )
    plt.title('Top Scores by Subject', pad=15)
    plt.xlabel('Subjects')
    plt.ylabel('Highest Score')
    plt.xticks(rotation=45, ha='right')
    for bar in bars:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height,
                f'{height}',
                ha='center', va='bottom')
    top_scores_chart = get_chart_base64()
    plt.close()

    # 2. Subject-wise attempts
    plt.figure(figsize=(8,8))
    plt.pie(
        [s['attempts'] for s in subject_data],
        labels=[s['name'] for s in subject_data],
        autopct='%1.1f%%',
        colors=['#59a14f','#edc948','#af7aa1'],
        wedgeprops={'linewidth': 1, 'edgecolor': 'white'}
    )
    plt.title('Quiz Attempts by Subject', pad=20)
    attempts_pie = get_chart_base64()
    plt.close()

    # 3. Monthly active users (basic line chart)
    monthly_data = db.session.query(
        db.func.strftime('%Y-%m', Scores.timestamp).label('month'),
        db.func.count(db.distinct(Scores.user_id)).label('users')
    ).group_by('month').order_by('month').all()
    
    months = [data.month for data in monthly_data]
    active_users = [data.users for data in monthly_data]
    
    plt.figure(figsize=(10,5))
    plt.plot(months, active_users, marker='o', color='#76b7b2', linewidth=2)
    plt.title('Monthly Active Users', pad=15)
    plt.xlabel('Month')
    plt.ylabel('Number of Users')
    plt.grid(True, linestyle='--', alpha=0.6)
    monthly_users_chart = get_chart_base64()
    plt.close()

    return render_template('admin_summary.html',
                         top_scores_chart=top_scores_chart,
                         attempts_pie=attempts_pie,
                         monthly_users_chart=monthly_users_chart)

# User Summary Route
@app.route('/user_summary')
def user_summary():
    if 'user_id' not in session:
        return redirect(url_for('user_login'))
    
    user_id = session['user_id']
    
    # 1. Subject-wise quizzes (histogram)
    subjects = Subject.query.all()
    subject_names = [s.name for s in subjects]
    quiz_counts = [sum(len(chapter.quizzes) for chapter in s.chapters) for s in subjects]
    
    plt.figure(figsize=(10,5))
    bars = plt.bar(subject_names, quiz_counts, color=['#ff9da7','#9c755f','#bab0ac'])
    plt.title('Available Quizzes by Subject', pad=15)
    plt.xlabel('Subjects')
    plt.ylabel('Number of Quizzes')
    plt.xticks(rotation=45, ha='right')
    for bar in bars:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height,
                f'{height}',
                ha='center', va='bottom')
    quizzes_hist = get_chart_base64()
    plt.close()

    # 2. Monthly attempts (pie)
    monthly_attempts = db.session.query(
        db.func.strftime('%Y-%m', Scores.timestamp).label('month'),
        db.func.count(Scores.id).label('attempts')
    ).filter(Scores.user_id == user_id).group_by('month').all()
    
    months = [data.month for data in monthly_attempts]
    attempts = [data.attempts for data in monthly_attempts]
    
    plt.figure(figsize=(8,8))
    plt.pie(attempts, labels=months, autopct='%1.1f%%',
            colors=['#8cd3ff','#ffb3ba','#baffc9','#ffdfba'],
            wedgeprops={'linewidth': 1, 'edgecolor': 'white'})
    plt.title('Your Attempts by Month', pad=20)
    monthly_pie = get_chart_base64()
    plt.close()

    # 3. Performance comparison (bar chart)
    user_scores = db.session.query(
        Quiz.title,
        Scores.score,
        db.func.avg(Scores.score).over(partition_by=Quiz.id).label('avg_score'),
        db.func.max(Scores.score).over(partition_by=Quiz.id).label('max_score')
    ).join(Scores.quiz).filter(Scores.user_id == user_id).all()
    
    if user_scores:
        quiz_titles = [score.title for score in user_scores]
        user_scores_values = [score.score for score in user_scores]
        avg_scores = [score.avg_score for score in user_scores]
        max_scores = [score.max_score for score in user_scores]
        
        x = range(len(quiz_titles))
        width = 0.25
        
        plt.figure(figsize=(12,6))
        plt.bar(x, max_scores, width, label='Top Score', color='#59a14f')
        plt.bar([i + width for i in x], user_scores_values, width, label='Your Score', color='#4e79a7')
        plt.bar([i + 2*width for i in x], avg_scores, width, label='Average', color='#f28e2b')
        
        plt.title('Your Performance Comparison', pad=15)
        plt.xlabel('Quizzes')
        plt.ylabel('Scores')
        plt.xticks([i + width for i in x], quiz_titles, rotation=45, ha='right')
        plt.legend()
        plt.grid(True, axis='y', linestyle='--', alpha=0.6)
        performance_chart = get_chart_base64()
        plt.close()
    else:
        performance_chart = None

    return render_template('user_summary.html',
                         quizzes_hist=quizzes_hist,
                         monthly_pie=monthly_pie,
                         performance_chart=performance_chart)

# Admin presses each subject to see details
@app.route('/subject/<int:subject_id>')
def subject_detail(subject_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    subject = Subject.query.get_or_404(subject_id)
    return render_template('subject_detail.html', subject=subject)

# Admin presses each quiz to see details
@app.route('/quiz/<int:quiz_id>')
def quiz_detail(quiz_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    quiz = Quiz.query.get_or_404(quiz_id)
    return render_template('quiz_detail.html', quiz=quiz)

# Admin Logout
@app.route('/admin_logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    flash('You have been logged out.', 'success')
    return redirect(url_for('admin_login'))

# User Logout
@app.route('/user_logout')
def user_logout():
    session.pop('user_id', None)
    flash('You have been logged out.', 'success')
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)


