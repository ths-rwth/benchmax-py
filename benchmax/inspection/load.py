import logging
import xml.etree.ElementTree as ET
import pandas as pd

def process_run(run, file, timeout, statistics):
    solver = run.attrib["solver_id"]
    filename = file.attrib["name"]
    answer = None
    runtime = None
    mem = None
    for res in run.find('./results'):
        if res.get('name') == 'answer':
            answer = res.text
        elif res.get('name') == 'runtime':
            runtime = int(res.text) / 1000.0
        elif res.get('name') == 'peak_memory':
            mem = int(res.text)
        if answer != None and runtime != None and mem != None:
            break
    if answer == "memout":
        runtime = timeout + 5
    if answer == "timeout":
        runtime = timeout + 10

    result = [None for _ in range(3 + len(statistics))]
    result[0] = answer
    result[1] = runtime
    result[2] = mem

    if statistics != []:
        stats = run.find('./statistics')
        if stats is not None:
            for res in stats:
                if res.get('name') in statistics:
                    result[statistics.index(res.get('name'))+3] = res.text

    return filename,solver,tuple(result)

def xml_to_pandas(filename, solver_override = {}, statistics_filter = None):
    logging.info("Loading %s" % filename)
    tree = ET.parse(filename)
    root = tree.getroot()
    timeout = int(root.find("./information/info[@name='timeout']").get('value'))
    solvers = [s.get('solver_id') for s in root.findall("./solvers/solver")]
    statistics = [s.get('name') for s in root.findall("./statistics/stat")]
    if statistics_filter is not None:
        statistics = [value for value in statistics if value in statistics_filter]

    results = {}
    for file in root.findall('./benchmarks/*'):
        for run in file.findall('./*'):
            filename,solver,res = process_run(run, file, timeout = timeout, statistics = statistics)
            if not filename in results:
                results[filename] = {}
            results[filename][solver] = res

    data = []
    index = []
    empty = [None for _ in range(0,2+len(statistics))]
    for filename in results:
        index.append(filename)
        row = []
        for solver in solvers:
            if solver in results[filename].keys():
                row.extend(list(results[filename][solver]))
            else:
                row.extend(empty)
        data.append(tuple(row))

    def solver_name(s):
        if s in solver_override:
            return solver_override[s]
        else:
            return s
    
    df = pd.DataFrame(data, index, columns = pd.MultiIndex.from_product([map(solver_name, solvers), ["answer", "runtime", "peak_memory_kbytes"] + statistics]))
    return df

def xmls_to_pandas(params, statistics_filter = None):
    df = None
    for filename in params:
        if df is None:
            df = xml_to_pandas(filename, params[filename], statistics_filter)
        else:
            df = df.join(xml_to_pandas(filename, params[filename], statistics_filter))
    return df