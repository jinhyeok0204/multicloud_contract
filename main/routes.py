from flask import Blueprint, render_template, session, redirect, url_for, flash
from auth.routes import is_logged_in
main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def home():
    # 만약 사용자가 로그인된 상태라면 메뉴로 이동, 그렇지 않으면 로그인 페이지로 이동
    if 'username' in session:
        return redirect(url_for('main.menu'))
    return redirect(url_for('auth.login'))


# 로그인 후 제공하는 메뉴
@main_bp.route('/menu')
def menu():
    is_logged_in()
    return render_template('menu.html')
