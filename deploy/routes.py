# 가상머신 배포 기능을 담당하는 모듈
from flask import Blueprint, render_template, request, redirect, flash, url_for, session

from models import User, Deployment, Credential
from optimize.optimizer import make_info_dict, nsga2_with_filtered_routes, select_weighted_best, find_routes
from auth.routes import is_logged_in
import subprocess
from cryptography.fernet import Fernet

deploy_bp = Blueprint('deploy', __name__)


@deploy_bp.route('/deploy_summary', methods=['POST'])
def deploy_summary():
    is_logged_in()

    csp_list = request.form.getlist('csp')
    vm_count = int(request.form['vm_count'])
    cost_limit = float(request.form['cost_limit'])
    rtt_limit = float(request.form['rtt_limit'])

    info_dict = make_info_dict('Combinations.xlsx')
    route_list = find_routes(info_dict, vm_count)

    try:
        pareto_front, filtered_routes = nsga2_with_filtered_routes(route_list, csp_list, rtt_limit, cost_limit)
        best_route = select_weighted_best(pareto_front, filtered_routes)

        region_map = {}
        for each in best_route['route']:
            csp, region = each.split('-')[0], "-".join(each.split('-')[1:])
            if csp not in region_map:
                region_map[csp] = []
            region_map[csp].append(region)

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
        total_cost=round(best_route['total_cost'], 2),
        region_map=region_map  # 리전 정보 전달
    )


@deploy_bp.route('/deploy', methods=['GET', 'POST'])
def deploy():
    is_logged_in()

    user = User.query.filter_by(username=session['username']).first()

    if request.method == 'POST':
        csp_list = eval(request.form.getlist('csp_list')[0])  # 사용자가 선택한 CSP들
        vm_count = request.form['vm_count']
        cost_limit = request.form['cost_limit']
        rtt_limit = request.form['rtt_limit']

        region_map = {}
        for csp in csp_list:
            region_map[csp] = request.form.getlist(f'region_{csp}')

        is_passed, missing_csp = check_user_credential(user, csp_list)

        if not is_passed:
            flash(f'{missing_csp}의 자격 정보가 등록되지 않았습니다 ', 'danger')
            return redirect(url_for('credentials.credentials'))

        # 배포 로직
        deployed_vms = []
        for csp in csp_list:
            credential = Credential.query.filter_by(user_id=user.id, csp=csp).first()

            cipher = Fernet(user.encryption_key.encode('utf-8'))
            decrypted_data = cipher.decrypt(credential.credential_data).decode('utf-8')

            for region in region_map[csp]:
                pass

        flash(f'{", ".join(deployed_vms)} (비용 상한: {cost_limit} USD, RTT 상한: {rtt_limit} ms)', 'success')
        return redirect(url_for('main.menu'))

    return render_template('deploy.html', user=user)


# 배포한 가상 머신 배포 명세서 보기
@deploy_bp.route('/deployments', methods=['GET'])
def deployments():
    is_logged_in()

    user = User.query.filter_by(username=session['username']).first()
    deployments = Deployment.query.filter_by(user_id=user.id).all()

    return render_template('deployments.html', deployments=deployments)


# 사용자 자격 증명 확인
def check_user_credential(user, csp_list):

    missing_credentials = []
    for csp in csp_list:
        credential = Credential.query.filter_by(user_id=user.id, csp=str(csp).upper()).first()

        if not credential:
            missing_credentials.append(csp)

    if missing_credentials:
        return False, missing_credentials
    return True, None


def generate_terraform_file(csp, user_credentials, vm_count, region):
    pass


def run_terraform(csp, user_credentials, vm_count, region):
    pass

