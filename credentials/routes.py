import csv

from flask import Blueprint, render_template, request, redirect, flash, url_for, session, current_app
from app import db
from models import User, Credential
from auth.routes import is_logged_in
import json

credentials_bp = Blueprint('credentials', __name__)


@credentials_bp.route('/credentials', methods=['GET', 'POST'])
def credentials():
    is_logged_in()

    user = User.query.filter_by(username=session['username']).first()

    if request.method == 'POST':
        csp = request.form.get('csp')
        credential_file = request.files.get('credential_file')
        if not credential_file:
            flash('자격 증명 파일을 업로드 하세요')
            return redirect(url_for('credentials.credentials'))

        if csp == 'AWS':
            access_key, secret_key = process_aws_csv(credential_file)
            description = f'AWS 자격 증명 (Access Key: {access_key[:4]}****)'
            credential_data = f'{access_key},{secret_key}'.encode()  # CSV 형식으로 저장

        elif csp == 'GCP':
            file_data = credential_file.read()  # 파일 데이터를 읽음
            credential_json = json.loads(file_data)  # JSON으로 변환
            project_id = credential_json.get('project_id', 'Unknown Project')  # 프로젝트 ID 얻기
            description = f'GCP 자격 증명 (프로젝트: {project_id})'
            credential_data = file_data

        elif csp == 'Azure':
            credential_data = credential_file.read()  # 파일 데이터를 읽음
            credential_json = json.loads(credential_data)  # JSON으로 변환
            subscription_id = credential_json.get('subscriptionId', 'Unknown Subscription')  # 구독 ID 얻기
            description = f'Azure 자격 증명 (구독 ID: {subscription_id})'

        else:
            flash('CSP를 선택하세요.', 'danger')
            return redirect(url_for('credentials.credentials'))

        credential = Credential(user_id=user.id, csp=csp, credential_data=credential_data, description=description)
        db.session.add(credential)
        db.session.commit()

        flash(f'{csp} 자격 증명이 성공적으로 등록되었습니다.', 'success')
        return redirect(url_for('main.menu'))

    return render_template('credentials.html', user=user)


@credentials_bp.route('/credentials/view', methods=['GET'])
def credentials_view():
    is_logged_in()

    user = User.query.filter_by(username=session['username']).first()
    return render_template('credentials_view.html', credentials=user.credentials)

@credentials_bp.route('/credentials/delete/<int:credential_id>', methods=['POST'])
def delete(credential_id):
    is_logged_in()

    # 해당 자격 증명을 DB에서 삭제
    credential = Credential.query.get_or_404(credential_id)
    db.session.delete(credential)
    db.session.commit()

    flash('자격 증명이 성공적으로 삭제되었습니다.', 'success')
    return redirect(url_for('credentials.credentials_view'))


def process_aws_csv(file):
    # CSV 파일을 읽어서 AWS 자격 증명을 추출
    file_content = file.read().decode('utf-8-sig')
    reader = csv.DictReader(file_content.splitlines())
    for row in reader:
        aws_key_id = row['Access key ID']
        aws_secret_key = row['Secret access key']
    return aws_key_id, aws_secret_key