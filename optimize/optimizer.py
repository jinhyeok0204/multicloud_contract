import random
from deap import base, creator, algorithms, tools
import pandas as pd
from collections import deque


def filter_routes(route_list, csp_list, rtt_limit, cost_limit):
    filtered_routes = []

    for route in route_list:
        route_csp_set = {csp.split('-')[0] for csp in route['route']}

        # 사용자가 선택한 모든 CSP가 경로에 포함되었는지 확인
        if route_csp_set == set(csp_list):
            # RTT 및 비용 상한을 넘지 않는 경로만 추가
            if route['total_rtt'] <= rtt_limit and route['total_cost'] <= cost_limit:
                filtered_routes.append(route)

    return filtered_routes


# 사용자가 제공한 데이터를 기반으로 최적화 정보를 구성
def make_info_dict(excel_file):
    info_dict = {}

    df = pd.read_excel(excel_file)

    for _, row in df.iterrows():
        start = f"{row['start csp']}-{row['start region']}"
        end = f"{row['end csp']}-{row['end region']}"
        rtt = row['rtt']
        cost = row['total cost']

        if start not in info_dict:
            info_dict[start] = []
        info_dict[start].append((end, rtt, cost))

    return info_dict


def find_routes(info_dict, count):
    routes_list = []
    unique_routes = set()

    for start in info_dict:
        q = deque([([start], 0, 0)])

        while q:
            current_route, total_rtt, total_cost = q.popleft()

            if len(current_route) == count:
                if tuple(current_route) not in unique_routes:
                    routes_list.append({
                        'route': current_route,
                        'total_rtt' : total_rtt,
                        'total_cost': total_cost
                    })
                    unique_routes.add(tuple(current_route))
                continue

            last_node = current_route[-1]

            # 다음 노드 탐색
            if last_node in info_dict:
                for end, rtt, cost in info_dict[last_node]:
                    if end not in current_route: # 중복 방지
                        new_route = current_route + [end]
                        q.append((new_route, total_rtt + rtt, total_cost + cost))

    return routes_list


def nsga2_with_filtered_routes(route_list, csp_list, rtt_limit, cost_limit):

    # 사용자 입력에 의한 경로 필터링
    filtered_routes = filter_routes(route_list, csp_list, rtt_limit, cost_limit)
    print(filtered_routes)
    if not filtered_routes:
        raise ValueError("사용자 조건에 맞는 경로가 없습니다.")

    creator.create("FitnessMulti", base.Fitness, weights=(-1.0, -1.0))  # 두 개의 목표, 둘 다 최소화
    creator.create("Individual", list, fitness=creator.FitnessMulti)

    toolbox = base.Toolbox()
    toolbox.register("attr_int", random.randint, 0, len(filtered_routes) - 1)  # 0부터 n-1까지의 랜덤 인덱스
    toolbox.register("individual", tools.initRepeat, creator.Individual, toolbox.attr_int, 1)  # 개체는 하나의 인덱스만 포함

    population_size = len(filtered_routes) // 10
    toolbox.register("population", tools.initRepeat, list, toolbox.individual, population_size)  # 10%의 개체로 초기 인구 생성

    # 평가 함수 등록
    toolbox.register("evaluate", eval_route, routes=filtered_routes)
    toolbox.register("mate", tools.cxUniform, indpb=0.5)  # 교차
    toolbox.register("mutate", tools.mutUniformInt, low=0, up=len(filtered_routes) - 1, indpb=0.5)  # 돌연변이
    toolbox.register("select", tools.selNSGA2)  # NSGA-II 선택

    # 유전 알고리즘 실행
    population = toolbox.population()  # 초기 인구 생성

    ngen = 300  # 세대 수
    mu = population_size  # 부모 개체 수
    lambda_ = int(mu * 1.5)  # 자손 개체 수
    cxpb, mutpb = 0.8, 0.1  # 교차 및 돌연변이 확률

    algorithms.eaMuPlusLambda(population, toolbox, mu=mu, lambda_=lambda_, cxpb=cxpb, mutpb=mutpb, ngen=ngen,
                              stats=None, halloffame=None, verbose=False)

    # Pareto 최적 경로 추출
    pareto_front = tools.sortNondominated(population, len(population), first_front_only=True)[0]

    # 중복 제거된 Pareto front 생성
    unique_routes = set()
    final_pareto_front = []

    for individual in pareto_front:
        route = tuple(filtered_routes[individual[0]]['route'])
        if route not in unique_routes:
            unique_routes.add(route)
            final_pareto_front.append(individual)

    return final_pareto_front, filtered_routes


# NSGA-II 결과로 도출된 Pareto front 중 가중합을 이용하여 최적 경로를 추출
# 기본 가중치 => (0.5, 0.5) / 사용자 조절 가능
def select_weighted_best(pareto_front, routes, rtt_weight=0.5, cost_weight=0.5):
    best_route = None
    best_score = float('inf')  # 최소화 문제 -> 초기 값 무한대

    for individual in pareto_front:
        route = routes[individual[0]]
        score = rtt_weight * route["total_rtt"] + cost_weight * route["total_cost"]

        if score < best_score:
            best_score = score
            best_route = route

    return best_route


# NSGA-II에서 사용하는 경로 평가 함수
def eval_route(individual, routes):
    route = routes[individual[0]]
    return route["total_rtt"], route["total_cost"]


# 최적화된 전체 흐름을 사용하는 예시
if __name__ == "__main__":
    excel_file = '../Combinations.xlsx'
    info_dict = make_info_dict(excel_file)

    # 가능한 경로 조합 만들기 (모든 리전을 출발점으로 BFS로 경로 탐색)
    route_list = find_routes(info_dict, count=4)

    # 사용자 지정 필터 조건
    csp_list = ['aws']

    rtt_limit = 1000
    cost_limit = 1000

    pareto_front, filtered_routes = nsga2_with_filtered_routes(route_list, csp_list, rtt_limit, cost_limit)
    best_route = select_weighted_best(pareto_front, filtered_routes)

    print(f"Best route: {best_route['route']}, Total RTT: {best_route['total_rtt']}, Total Cost: {best_route['total_cost']}")