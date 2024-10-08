from flask import Blueprint, render_template, request, redirect, flash, url_for, session
from app import db
from models import User
import os
import configparser

credentials_bp = Blueprint('credentials', __name__)

@credentials_bp.route('/credentials', methods=['GET', 'POST'])
def credentials():
    if 'username' not in session:
        flash('로그인이 필요합니다.', 'danger')
        return redirect(url_for('auth.login'))

    user = User.query.filter_by(username=session['username']).first()

    if request.method == 'POST':
        csp = request.form.get('csp')

        if csp == 'AWS':
            # AWS 자격 증명 파일 처리
            aws_file = request.files.get('aws_credentials')
            if aws_file:
                aws_filepath = os.path.join(app.config['UPLOAD_FOLDER'], aws_file.filename)
                aws_file.save(aws_filepath)

                # 파일에서 AWS 자격 증명 읽기
                config = configparser.ConfigParser()
                config.read(aws_filepath)
                user.aws_access_key = config['default']['aws_access_key_id']
                user.aws_secret_key = config['default']['aws_secret_access_key']
                db.session.commit()
                flash('AWS 자격 증명이 성공적으로 등록되었습니다.', 'success')

        elif csp == 'GCP':
            # GCP 자격 증명 파일 처리
            gcp_file = request.files.get('gcp_credentials')
            if gcp_file:
                gcp_filepath = os.path.join(app.config['UPLOAD_FOLDER'], gcp_file.filename)
                gcp_file.save(gcp_filepath)
                user.gcp_credentials = gcp_filepath
                db.session.commit()
                flash('GCP 자격 증명이 성공적으로 등록되었습니다.', 'success')

        elif csp == 'Azure':
            # Azure 자격 증명 파일 처리
            azure_file = request.files.get('azure_credentials')
            if azure_file:
                azure_filepath = os.path.join(app.config['UPLOAD_FOLDER'], azure_file.filename)
                azure_file.save(azure_filepath)
                user.azure_credentials = azure_filepath
                db.session.commit()
                flash('Azure 자격 증명이 성공적으로 등록되었습니다.', 'success')

        else:
            flash('CSP를 선택하세요.', 'danger')

        return redirect(url_for('main.menu'))

    return render_template('credentials.html', user=user)
