# 가상머신 배포 기능을 담당하는 모듈
from flask import Blueprint, render_template, request, redirect, flash, url_for, session
from app import db
from models import User, Deployment, Credential
from optimize.optimizer import make_info_dict, nsga2_with_filtered_routes, select_weighted_best, find_routes
from auth.routes import is_logged_in
from deploy.deploy_terraform import deploy_vm
from cryptography.fernet import Fernet
import json

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
        only_best_route=best_route['route'],
        vm_count=vm_count,
        cost_limit=cost_limit,
        rtt_limit=rtt_limit,
        total_rtt=round(best_route['total_rtt'], 2),
        total_cost=round(best_route['total_cost'], 2),
        region_map=region_map,  # 리전 정보 전달
        best_route=best_route
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
        best_route = eval(request.form.get('best_route')) # 최적 배포 경로

        region_map = {}
        for csp in csp_list:
            region_map[csp] = request.form.getlist(f'region_{csp}')

        is_passed, missing_csp = check_user_credential(user, csp_list)

        if not is_passed:
            flash(f'{missing_csp}의 자격 정보가 등록 되지 않았습니다 ', 'danger')
            return redirect(url_for('credentials.credentials'))

        deployed_vms, success = deploy_vms_to_region(user, csp_list, region_map)

        if success:
            save_deployment_to_db(user.id, best_route, vm_count, cost_limit, rtt_limit)
            flash(f'{vm_count}개 가상머신 배포 완료', 'success')
        else:
            flash("가상머신 배포에 실패했습니다.", 'danger')

        return redirect(url_for('main.menu'))

    return render_template('deploy.html', user=user)


# 배포한 가상 머신 배포 명세서 보기
@deploy_bp.route('/deployments', methods=['GET'])
def deployments():
    is_logged_in()

    user = User.query.filter_by(username=session['username']).first()
    deployments = Deployment.query.filter_by(user_id=user.id).all()

    parsed_deployments = []
    for deployment in deployments:
        details = json.loads(deployment.details)
        details['total RTT'] = round(details['total RTT'], 2)
        details['total Cost'] = round(details['total Cost'], 2)

        parsed_deployments.append({
            'id':deployment.id,
            'details':details,
        })
    return render_template('deployments.html', deployments=parsed_deployments)

@deploy_bp.route('/deployments/delete/<int:deployment_id>', methods=['POST'])
def delete_deployment(deployment_id):
    is_logged_in()

    user = User.query.filter_by(username=session['username']).first()

    deployment = Deployment.query.get(deployment_id)
    if not deployment or deployment.user_id != user.id:
        flash('삭제할 배포 명세서를 찾을 수 없거나 권한이 없습니다.', 'danger')
        return redirect(url_for('main.menu'))

    db.session.delete(deployment)
    db.session.commit()

    flash('배포 명세서가 성공적으로 삭제되었습니다.', 'success')
    return redirect(url_for('deploy.deployments'))


# 배포 로직
def deploy_vms_to_region(user, csp_list, region_map):
    deployed_vms = []
    success = True # 배포 성공 여부

    for csp in csp_list:
        credential = Credential.query.filter_by(user_id=user.id, csp=csp.upper()).first()

        cipher = Fernet(user.encryption_key.encode('utf-8'))
        decrypted_data = cipher.decrypt(credential.credential_data).decode('utf-8')

        # CSP에 맞는 자격 증명 파싱
        if csp == 'aws':
            access_key, secret_key = decrypted_data.split(',')
            credential_data = {'access_key': access_key, 'secret_key': secret_key}
        elif csp == 'gcp':
            gcp_credentials = decrypted_data
            project_id = json.loads(gcp_credentials).get('project_id')
            credential_data = {'gcp_credentials': gcp_credentials, 'project_id': project_id}

        # 각 리전에 대해 가상머신 배포
        for region in region_map[csp]:
            print(f"{csp}, {region} deploy !)")
            output = deploy_vm(csp, region, credential_data)
            if output.get('instance_public_ip', None):
                deployed_vms.append(f"{csp}-{region} VM : {output.get('instance_public_ip', {}).get('value', 'N/A')}")
            else:
                success = False
                break

    return deployed_vms, success


def save_deployment_to_db(user_id, best_route, vm_count, cost_limit, rtt_limit):
    deployment_details = {
        'route'     : " <-> ".join(best_route['route']),
        'total RTT' : best_route['total_rtt'],
        'total Cost': best_route['total_cost'],
        'RTT Limit' : rtt_limit,
        'Cost Limit': cost_limit,
        'VM Count'  : vm_count,
    }

    new_deployment = Deployment(user_id = user_id, details=json.dumps(deployment_details))
    db.session.add(new_deployment)
    db.session.commit()


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




