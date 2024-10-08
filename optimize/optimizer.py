import random
from deap import base, creator, algorithms, tools
import pandas as pd


def filter_routes(route_list, csp_list, rtt_limit, cost_limit):
    filtered_routes = []

    for route in route_list:
        if all(csp.split('-')[0] in csp_list for csp in route['route']):
            # RTT 및 비용 상한을 넘지 않는 경로만 추가
            if route['total_rtt'] <= rtt_limit and route['total_cost'] <= cost_limit:
                filtered_routes.append(route)

    return filtered_routes


# 사용자가 제공한 데이터를 기반으로 최적화 정보를 구성
def make_info_dict():
    info_dict = dict()
    df = pd.read_excel('Combinations.xlsx')  # 엑셀 파일에서 데이터 로드
    start_region = df['start region']
    end_region = df['end region']

    set_start = set(start_region)
    set_end = set(end_region)

    print(len(set_start), len(set_end))
    for i in range(len(df)):
        row = df.iloc[i]

        start = f"{row['start csp']}-{row['start region']}"
        end = f"{row['end csp']}-{row['end region']}"
        rtt = row['rtt']
        cost = row['total cost']

        if start in info_dict.keys():
            info_dict[start].append((end, rtt, cost))
        else:
            info_dict[start] = [(end, rtt, cost)]

    return info_dict


# 경로 최적화를 위한 메모이제이션 및 경로 탐색 함수
def find_routes(info_dict, start, count, current_route, total_rtt, total_cost, visited, routes_list, cache, unique_routes):
    route_key = (start, tuple(current_route))  # 캐시를 위한 키 (시작 노드와 경로)

    if route_key in cache:
        # 메모이제이션: 캐시에 이미 있는 경로의 계산 결과를 사용
        cached_rtt, cached_cost = cache[route_key]
        total_rtt += cached_rtt
        total_cost += cached_cost
        if tuple(current_route) not in unique_routes:
            routes_list.append({
                'route': current_route,
                'total_rtt': total_rtt,
                'total_cost': total_cost
            })
            unique_routes.add(tuple(current_route))
            return

    if count == 0:
        # 경로가 완성되면 리스트에 저장
        if tuple(current_route) not in unique_routes:
            routes_list.append({
                'route': current_route,
                'total_rtt': total_rtt,
                'total_cost': total_cost
            })
            unique_routes.add(tuple(current_route))

        # 경로 결과를 캐시에 저장
        cache[route_key] = (total_rtt, total_cost)
        return

    if start not in info_dict:
        return

    visited.add(start)

    # 경로를 재귀적으로 계산
    for end, rtt, cost in info_dict[start]:
        if end not in visited:
            new_route = current_route + [end]
            find_routes(info_dict, end, count - 1, new_route, total_rtt + rtt, total_cost + cost, visited, routes_list,
                        cache, unique_routes)

    visited.remove(start)
    # 경로 결과를 캐시에 저장
    cache[route_key] = (total_rtt, total_cost)


# 가능한 경로 조합을 생성하는 함수
def make_combination(info_dict, count):
    routes_list = []
    unique_routes = set()
    cache = {}  # 메모이제이션을 위한 캐시

    for start in info_dict:
        find_routes(info_dict, count - 1, [start], 0, 0, set(), routes_list, cache, unique_routes)

    return routes_list


def nsga2_with_filtered_routes(route_list, csp_list, rtt_limit, cost_limit):

    # 사용자 입력에 의한 경로 필터링
    filtered_routes = filter_routes(route_list, csp_list, rtt_limit, cost_limit)

    if not filtered_routes:
        raise ValueError("사용자 조건에 맞는 경로가 없습니다.")


    creator.create("FitnessMulti", base.Fitness, weights=(-1.0, -1.0))  # 두 개의 목표, 둘 다 최소화
    creator.create("Individual", list, fitness=creator.FitnessMulti)

    toolbox = base.Toolbox()
    toolbox.register("attr_int", random.randint, 0, len(filtered_routes) - 1)  # 0부터 n-1까지의 랜덤 인덱스
    toolbox.register("individual", tools.initRepeat, creator.Individual, toolbox.attr_int, 1)  # 개체는 하나의 인덱스만 포함

    population_size = 500
    toolbox.register("population", tools.initRepeat, list, toolbox.individual, population_size)  # 10%의 개체로 초기 인구 생성

    # 평가 함수 등록
    toolbox.register("evaluate", eval_route, routes=filtered_routes)
    toolbox.register("mate", tools.cxUniform, indpb=0.5)  # 교차
    toolbox.register("mutate", tools.mutUniformInt, low=0, up=len(filtered_routes) - 1, indpb=0.5)  # 돌연변이
    toolbox.register("select", tools.selNSGA2)  # NSGA-II 선택

    # 유전 알고리즘 실행
    population = toolbox.population()  # 초기 인구 생성

    ngen = 200  # 세대 수
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

    return final_pareto_front


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