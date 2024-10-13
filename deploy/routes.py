# 가상머신 배포 기능을 담당하는 모듈
from flask import Blueprint, render_template, request, redirect, flash, url_for, session

from models import User, Deployment
from optimize.optimizer import make_info_dict, nsga2_with_filtered_routes, select_weighted_best, make_combination

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

    info_dict = make_info_dict()
    route_list = make_combination(info_dict, vm_count)  # 가상머신 개수에 따른 조합 생성

    try:
        pareto_front = nsga2_with_filtered_routes(route_list, csp_list, rtt_limit, cost_limit)
        best_route = select_weighted_best(pareto_front, route_list)
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
        total_rtt=best_route['total_rtt'],
        total_cost=best_route['total_cost']
    )


@deploy_bp.route('/deploy', methods=['GET', 'POST'])
def deploy():
    if 'username' not in session:
        flash('로그인이 필요합니다.', 'danger')
        return redirect(url_for('auth.login'))

    user = User.query.filter_by(username=session['username']).first()

    if request.method == 'POST':
        csp_list = request.form.getlist('csp')  # 사용자가 선택한 CSP들
        vm_count = request.form['vm_count']  # VM 개수
        cost_limit = request.form['cost_limit']  # 비용 상한
        rtt_limit = request.form['rtt_limit']  # RTT 상한

        # 사용자 자격 증명 확인
        if 'AWS' in csp_list and (not user.aws_access_key or not user.aws_secret_key):
            flash('AWS 자격 증명을 등록해야 합니다.', 'danger')
            return redirect(url_for('credentials.credentials'))

        if 'GCP' in csp_list and not user.gcp_credentials:
            flash('GCP 자격 증명을 등록해야 합니다.', 'danger')
            return redirect(url_for('credentials.credentials'))

        if 'Azure' in csp_list and not user.azure_credentials:
            flash('Azure 자격 증명을 등록해야 합니다.', 'danger')
            return redirect(url_for('credentials.credentials'))

        # 배포 로직 (CSP별로 처리 로직을 구현해야 합니다)
        deployed_vms = []
        for csp in csp_list:
            if csp == 'AWS':
                # AWS 가상머신 배포 로직 추가 (boto3 사용)
                deployed_vms.append(f'{vm_count}개의 VM을 AWS에 배포했습니다.')

            elif csp == 'GCP':
                # GCP 가상머신 배포 로직 추가 (Google Cloud SDK 사용)
                deployed_vms.append(f'{vm_count}개의 VM을 GCP에 배포했습니다.')

            elif csp == 'Azure':
                # Azure 가상머신 배포 로직 추가 (Azure SDK 사용)
                deployed_vms.append(f'{vm_count}개의 VM을 Azure에 배포했습니다.')

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