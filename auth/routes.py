from flask import Blueprint, render_template, redirect, request, flash, session, url_for
from app import db
from models import User
import bcrypt

auth_bp = Blueprint('auth', __name__)

# 프로필 화면
@auth_bp.route('/profile', methods=['GET'])
def profile():
    if 'username' not in session:
        flash('로그인이 필요합니다.', 'danger')
        return redirect(url_for('auth.login'))

    user = User.query.filter_by(username=session['username']).first()
    return render_template('profile.html', user=user)


# 사용자 이름 변경
@auth_bp.route('/profile/change_username', methods=['GET', 'POST'])
def change_username():
    if 'username' not in session:
        flash('로그인이 필요합니다.', 'danger')
        return redirect(url_for('auth.login'))

    user = User.query.filter_by(username=session['username']).first()
    new_username = request.form['new_username']
    password = request.form['password'].encode('utf-8')

    if bcrypt.checkpw(password, user.password.encode('utf-8')):
        if not User.query.filter_by(username=new_username).first():
            user.username = new_username
            db.session.commit()
            session['username'] = new_username
            flash('사용자 이름이 변경되었습니다.', 'success')
        else:
            flash('이미 존재하는 사용자 이름입니다.', 'danger')
    else:
        flash('비밀번호가 잘못되었습니다.', 'danger')

    return redirect(url_for('auth.profile'))


# 비밀번호 변경
@auth_bp.route('/profile/change_password', methods=['POST'])
def change_password():
    if 'username' not in session:
        flash('로그인이 필요합니다.', 'danger')
        return redirect(url_for('auth.login'))

    user = User.query.filter_by(username=session['username']).first()
    current_password = request.form['current_password'].encode('utf-8')
    new_password = request.form['new_password'].encode('utf-8')

    if bcrypt.checkpw(current_password, user.password.encode('utf-8')):
        hashed_new_password = bcrypt.hashpw(new_password, bcrypt.gensalt())
        user.password = hashed_new_password.decode('utf-8')
        db.session.commit()
        flash('비밀번호가 변경되었습니다.', 'success')
    else:
        flash('현재 비밀번호가 잘못되었습니다.', 'danger')

    return redirect(url_for('auth.profile'))


# 회원가입
@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password'].encode('utf-8')

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('이미 존재하는 사용자 이름입니다.', 'danger')
            return redirect(url_for('auth.signup'))

        hashed_password = bcrypt.hashpw(password, bcrypt.gensalt())

        # 새 사용자 생성
        new_user = User(username=username, password=hashed_password.decode('utf-8'))
        db.session.add(new_user)
        db.session.commit()

        flash('회원가입이 완료되었습니다! 로그인 하세요.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('signup.html')

# 로그인
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password'].encode('utf-8')

        user = User.query.filter_by(username=username).first()

        if user:
            if bcrypt.checkpw(password, user.password.encode('utf-8')):
                session['username'] = user.username
                return redirect(url_for('main.menu'))
            else:
                flash('비밀번호가 잘못되었습니다.' 'danger')
        else:
            flash('존재하지 않는 사용자 입니다.', 'danger')

        return redirect(url_for('auth.login'))
    return render_template('index.html')


# 로그아웃
@auth_bp.route('/logout')
def logout():
    session.pop('username', None)
    flash('로그아웃되었습니다.', 'info')
    return redirect(url_for('auth.login'))
