from flask import Blueprint, render_template
from flask_socketio import emit, join_room, leave_room
from ... import socketio

import pandas as pd
import numpy as np
import httpx
import time
import textdistance
import random

bp_index = Blueprint('app_index', __name__, url_prefix='/')


@bp_index.route("/", methods=['GET'])
def index():
    title = 'Pandora Fuzz'
    return render_template('index.html', title=title)

@socketio.on('process')
def handle_process_event(datas):
    MAX_POP = 10
    MAX_FETCH_CHROMOSOME = 5
    MAX_GENERATION = 3 ## 0 : ulti
    MAX_SCORE = 0.5
    TIMEOUT_SLEEP = 5

    APPROX_ALPHA = datas['approx'][0]
    APPROX_BETA = datas['approx'][1]
    APPROX_GAMMA = datas['approx'][2]
    APPROX_DELTA = datas['approx'][3]

    URL = datas['url']
    COOKIES = {
        'PHPSESSID' : 'm2antojk6adprf1t8q22g17221',
        'security' : 'low'
    }

    KNOWN_RESPONSE_ERROR = [
        'error in your SQL syntax'
    ]

    KNOWN_RESPONSE_TEXT = [
        '-MariaDB'
        '31333337'
    ]

    def mutation(query, options):
        result = []
        if options == 'change_case_types':
            for pl in query.split():
                temp = ''
                for i, p in enumerate(list(pl)):
                    if p.isalpha():
                        if random.randint(13, 37) % 2:
                            p = chr(ord(p) - 32) if ord('a') <= ord(p) <= ord('z') else chr(ord(p) + 32)

                    temp += p
                result.append(temp)

            result = ' '.join(result)
        elif options == 'repeat_query':
            for_replace = []
            for pl in query.split():
                for p in pl.replace(',', ' ').split():
                    if p not in for_replace:
                        for_replace.append(''.join(list(filter(str.isalpha, p))))

            result = query
            for fr in for_replace:
                prev = int(len(fr)/2) if len(fr) % 2 else int(len(fr)/2)+1
                result = result.replace(fr, fr[:prev] + fr + fr[prev:])
        elif options == 'replace_whitespace':
            result = query.replace(' ', '/**/')
        
        return result

    ## load public payload
    datas = pd.read_csv('etc/payload.csv')

    ## remove nan values
    for attr in datas:
        datas[attr] = datas[attr].fillna('')
    
    ## setup timeout when sleep function triggered
    datas['fu_3'] = datas['fu_3'].str.replace('TIMEOUT_SLEEP', TIMEOUT_SLEEP.__str__())

    NORMAL_RESPONSE = httpx.get(URL.replace('FUZZ', '999'), cookies=COOKIES).text

    timeout = time.perf_counter()
    httpx.get(URL.replace('FUZZ', '1'), cookies=COOKIES)
    NORMAL_TIMEOUT = time.perf_counter() - timeout

    ## intial generation
    GENERATION = [datas]

    while len(GENERATION)-1 < MAX_GENERATION if MAX_GENERATION else True:
        chrome = GENERATION[len(GENERATION)-1].copy(deep=True)
        score_error, score_reflected, score_blind, score_ld_response = [], [], [], []

        emit('logger', f'Generation: {len(GENERATION)} --> Start')
        for i in range(len(chrome)):
            start_time = time.perf_counter()
            response_text = httpx.get(URL.replace('FUZZ', ' '.join(chrome.iloc[i].tolist())), cookies=COOKIES, timeout=8).text
            end_time = time.perf_counter() - start_time

            emit('logger', f'Generation: {len(GENERATION)} - Chromosome: {i} --> KRE')
            _kre = 0
            for kre in KNOWN_RESPONSE_ERROR:
                if kre in response_text:
                    _kre = APPROX_ALPHA
                    break

            score_error.append(_kre)

            emit('logger', f'Generation: {len(GENERATION)} - Chromosome: {i} --> KRT')
            _krt = 0
            for krt in KNOWN_RESPONSE_TEXT:
                if krt in response_text:
                    _krt = APPROX_DELTA
                    break
            
            score_reflected.append(_krt)

            emit('logger', f'Generation: {len(GENERATION)} - Chromosome: {i} --> Blind')
            if end_time >= TIMEOUT_SLEEP:
                score_blind.append( APPROX_GAMMA )
            else:
                score_blind.append( ((NORMAL_TIMEOUT - end_time) / float(NORMAL_TIMEOUT)) * APPROX_GAMMA )

            emit('logger', f'Generation: {len(GENERATION)} - Chromosome: {i} --> Levenshtein distance')
            if APPROX_BETA:
                score_ld_response.append( (textdistance.levenshtein.distance(NORMAL_RESPONSE, response_text) / float(len(NORMAL_RESPONSE))) * APPROX_BETA )
            else:
                score_ld_response.append( APPROX_BETA )

        chrome['score_error'] = score_error
        chrome['score_reflected'] = score_reflected
        chrome['score_blind'] = score_blind
        chrome['score_ld_response'] = score_ld_response
        chrome['score_total'] = [sum(chrome.iloc[i,-4:]) for i in range(len(chrome))]

        ## sort by higher score
        chrome = chrome.sort_values(by=['score_total'], ascending=False).reset_index(drop=True)

        emit('result', chrome.values.tolist())

        GAP = MAX_POP - MAX_FETCH_CHROMOSOME
        GAP = GAP if not GAP % 2 else GAP + 1

        offspring = []
        while len(offspring) < GAP:
            initial_population = []
            for i in range(0, GAP, 2):
                TARGET_FU_CROSSOVER = random.choices(list(range(4)), [.2, .2, .5, .1]).pop()
                TARGET_MUTATION = random.choices(['change_case_types', 'repeat_query', 'replace_whitespace']).pop()
                
                prev = chrome.iloc[i,:4].tolist()
                next = chrome.iloc[i + 1,:4].tolist()
                
                prev[TARGET_FU_CROSSOVER], next[TARGET_FU_CROSSOVER] = mutation(next[TARGET_FU_CROSSOVER], TARGET_MUTATION), mutation(prev[TARGET_FU_CROSSOVER], TARGET_MUTATION)
                
                if '?'.join(prev) not in map(lambda x: '?'.join(x), initial_population):
                    initial_population.append(prev)

                if '?'.join(next) not in map(lambda x: '?'.join(x), initial_population):
                    initial_population.append(next)

            [offspring.append(pop) for pop in initial_population]
        
        candidate = pd.DataFrame(np.array(chrome.iloc[:MAX_POP - len(offspring), :4].values.tolist() + offspring), columns=chrome.columns.tolist()[:4])
        GENERATION.append(candidate)

        emit('logger', f'Generation: {len(GENERATION)-1} --> Finished')
        emit('logger', f'Generation: {len(GENERATION)-1} --> Avg: {sum(chrome.score_total) / len(chrome)}, Max: {max(chrome.score_total)}, Min: {min(chrome.score_total)}')

        if sum(chrome.score_total) / len(chrome) > MAX_SCORE:
            break

    emit('finished')
    