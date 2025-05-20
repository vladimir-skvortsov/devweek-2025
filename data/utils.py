_quanjiao2b = ['……', '。。。', '。', '，', '；', '：', '？',
              '！', '“', '”', "‘", "’", "（", "）", '【', '】', '、']
_banjiao = ['...', '...', '.', ',', ';', ':', '?',
           '!', '"', '"', "'", "'", "(", ")", '[', ']', ',']


def _repl(data: str, fromjiao: list[str], tojiao: list[str]) -> str:
    assert len(fromjiao) == len(tojiao)
    for i, j in zip(fromjiao, tojiao):
        data = data.replace(i, j)
    return data


def _process(line: str) -> str:
    '''char Clean, from data preprocessing scripts'''
    new_line = line.replace('\n', ' ')  # remove \n
    puncs = [',', '.', ';', ':', '"', "'", "?", '!']
    p1 = [',', '.', ';', ':', "?", '!']
    p2 = ["'"]
    p3 = []
    # policy 1: xxx, xxx
    # policy 2: xxx'xxx
    # policy 3: 'xxx
    # p1 deal with: wrong space around pronounciation
    # first: clean all space, then add
    for _ in range(5):  # heuristic
        for p in p1:
            new_line = new_line.replace(' '+p+' ', p) # ' , ' -> ','
            new_line = new_line.replace(p+' ', p) # ', ' -> ',' 
            new_line = new_line.replace(' '+p, p) # ' ,' -> ','

    for p in p1:
        new_line = new_line.replace(p, p+' ') # ',' -> ', '
    # for ...:
    new_line = new_line.replace('. . . ', '... ')
    # p2 deal with: 's, 't
    wrong_samples = []
    for i in range(1, len(new_line)-2):
        if new_line[i] == "'" and new_line[i+1].isalpha() and new_line[i-1] == ' ' and new_line[i+2] == ' ':
            j = i-2
            while j >= 1 and new_line[j] == ' ':
                j -= 1

            wrong_samples.append(new_line[j:i+3])
    wrong_samples.sort(key=lambda x: len(x), reverse=True)
    for w in wrong_samples:
        new_line = new_line.replace(w, w[0]+w[-3:])
    new_line = new_line.replace(" n't", "n't")
    # remove extra spaces at the end
    for k in range(len(new_line)-1, -1, -1):
        if new_line[k] != ' ':
            new_line = new_line[:k+1]
            break
    return new_line


def clean(data: str) -> str:
    d = _repl(data, _quanjiao2b, _banjiao)
    d = _process(d)
    new_d = d.replace('  ', ' ')
    while new_d != d:
        d = new_d
        new_d = d.replace('  ', ' ')
    return new_d

