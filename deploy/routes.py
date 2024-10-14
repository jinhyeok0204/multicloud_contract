# 가상머신 배포 기능을 담당하는 모듈
from flask import Blueprint, render_template, request, redirect, flash, url_for, session

from models import User, Deployment, Credential
from optimize.optimizer import make_info_dict, nsga2_with_filtered_routes, select_weighted_best, find_routes
import subprocess

deploy_bp = Blueprint('deploy', __name__)


@deploy_bp.route('/deploy_summary', methods=['POST'])
def deploy_summary():
    if 'username' not in session:
        flash('로그인이 필요합니다.', 'danger')
        return redirect(url_for('auth.login'))

    csp_list = request.form.getlist('csp')
    vm_count = int(request.form['vm_count'])
    cost_limit = float(request.form['cost_limit'])
    rtt_limit = float(request.form['rtt_limit'])

    info_dict = make_info_dict('Combinations.xlsx')
    route_list = find_routes(info_dict, vm_count)

    try:
        pareto_front, filtered_routes = nsga2_with_filtered_routes(route_list, csp_list, rtt_limit, cost_limit)
        best_route = select_weighted_best(pareto_front, filtered_routes)
        print(best_route)

    except Exception as e:
        flash(str(e), 'danger')
        return redirect(url_for('deploy.deploy'))

    return render_template(
        'deploy_summary.html',
        csp_list=csp_list,
        best_route=best_route['route'],
        vm_count=vm_count,
        cost_limit=cost_limit,
        rtt_limit=rtt_limit,
        total_rtt=round(best_route['total_rtt'], 2),
        total_cost=round(best_route['total_cost'], 2)
    )


@deploy_bp.route('/deploy', methods=['GET', 'POST'])
def deploy():
    if 'username' not in session:
        flash('로그인이 필요합니다.', 'danger')
        return redirect(url_for('auth.login'))

    user = User.query.filter_by(username=session['username']).first()

    if request.method == 'POST':
        csp_list = request.form.getlist('csp_list')  # 사용자가 선택한 CSP들
        vm_count = request.form['vm_count']  # VM 개수
        cost_limit = request.form['cost_limit']  # 비용 상한
        rtt_limit = request.form['rtt_limit']  # RTT 상한


        is_passed, missing_csp = check_user_credential(user, csp_list)

        if not is_passed:
            flash(f'{", ".join(missing_csp).upper()[1:-1]} 자격 증명이 등록되지 않았습니다.', 'danger')
            return redirect(url_for('credentials.credentials'))

        # 배포 로직
        deployed_vms = []
        for csp in csp_list:
            if csp == 'AWS':
                # AWS 가상머신 배포 로직 추가 (boto3 사용)
                deployed_vms.append(f'{vm_count}개의 VM을 AWS에 배포했습니다.')

            elif csp == 'GCP':
                # GCP 가상머신 배포 로직 추가 (Google Cloud SDK 사용)
                deployed_vms.append(f'{vm_count}개의 VM을 GCP에 배포했습니다.')

            # elif csp == 'Azure':
            #     # Azure 가상머신 배포 로직 추가 (Azure SDK 사용)
            #     deployed_vms.append(f'{vm_count}개의 VM을 Azure에 배포했습니다.')

        flash(f'{", ".join(deployed_vms)} (비용 상한: {cost_limit} USD, RTT 상한: {rtt_limit} ms)', 'success')
        return redirect(url_for('main.menu'))

    return render_template('deploy.html', user=user)


# 배포한 가상 머신 배포 명세서 보기
@deploy_bp.route('/deployments', methods=['GET'])
def deployments():
    # 세션에 로그인된 사용자가 있는지 확인
    if 'username' not in session:
        flash('로그인이 필요합니다.', 'danger')
        return redirect(url_for('auth.login'))

    # 현재 로그인된 사용자 찾기
    user = User.query.filter_by(username=session['username']).first()

    # 사용자와 연결된 배포 내역 가져오기
    deployments = Deployment.query.filter_by(user_id=user.id).all()

    # 배포 내역을 템플릿으로 렌더링
    return render_template('deployments.html', deployments=deployments)


# 사용자 자격 증명 확인
def check_user_credential(user, csp_list):

    missing_credentials = []

    for csp in csp_list:

        credential = Credential.query.filter_by(user_id=user.id, csp=csp).first()

        if not credential:
            missing_credentials.append(csp)

    if missing_credentials:
        return False, missing_credentials
    return True, None


# def generate_terraform_file(csp, user_credentials, vm_count, region):
#
#     return tf_file_path, temp_dir

#
# def run_terraform(csp, user_credentials, vm_count, region):
#     tf_file, temp_dir = generate_terraform_file(csp, user_credentials, vm_count, region)
#
#     # Terraform 초기화 및 실행
#     subprocess.run(['terraform', 'init'], cwd=temp_dir, check=True)
#     subprocess.run(['terraform', 'apply', '-auto-approve'], cwd=temp_dir, check=True)
#
#     # 임시 디렉토리 삭제
#     subprocess.run(['terraform', 'destroy', '-auto-approve'], cwd=temp_dir, check=True)
#
#     return


