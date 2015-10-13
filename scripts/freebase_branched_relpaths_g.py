#!/usr/bin/python -u
#
# Generates dataset of branched (T-shaped) fbpaths from freebase mids of question concepts and from
# simple relpaths (containing one or two relations)
#
# Usage: freebase_branched_relpaths_g.py mids.json relpaths.json [apikey]
#
# File mids.json contains array of objects with qId and freebaseMids fields and could be generated by freebase_mids.py script.
# File relpaths.json contains array of objects with qId and relPaths fields.
# Apikey is the key for google freebase api and can be obtained here: https://console.developers.google.com/
# The freebase response is stored into fbconcepts directory into the file named <mid>.json.
# If the apikey is not provided then the script tries to read existing JSON freebase data dumps from the directory fbconcepts/.

from __future__ import print_function
import sys, json
from urllib2 import urlopen
import copy, os

def walk_node(node, pathprefix, labels):
    relpaths = []
    for name, val in node['property'].items():
        for value in val['values']:
            if value['text'] in labels:
                relpaths.append(tuple(pathprefix + [name]))
            if 'property' in value:
                relpaths += walk_node(value, pathprefix + [name], labels)
    return relpaths

def remove_duplicate_paths(array):
    tmp = [(tuple(x[0]), x[1]) for x in array]
    tmp = list(set(tmp))
    res = [[list(x[0]), x[1]] for x in tmp]
    return res

def json_array_to_map(array, key):
    res = {}
    for line in array:
        res[line[key]] = line
    return res 

def find_branch_of_path(key, relpath_map, concept_paths):
    paths = list(set([tuple(path[0]) for path in relpath_map[key]['relPaths']]))
    concept_path = list(set(concept_paths))
    new_paths = []
    for p in paths:        
        if (len(p) < 2):
            continue
        for path in concept_path:            
            if len(path) < 2:
                continue
            flag = False
            for node in path:
                if node in p:
                    flag = True            
            if flag:                 
                new_paths.append(path) 
    return new_paths  

def merge_paths(key, relpaths_map, new_paths):
    line = relpaths_map[key]
    for new in new_paths:
        for i, p in enumerate(line['relPaths']):
            if new[0] in p[0]: 
                if (len(line['relPaths'][i][0]) == 2):
                    line['relPaths'][i][0].append(new[1])
                elif (len(line['relPaths'][i][0]) == 3):
                    tmp = copy.deepcopy(line['relPaths'][i])
                    if (tmp[0][2] != new[1]):
                        tmp[0][2] = new[1]
                        line['relPaths'].append(tmp)
    line['relPaths'] = remove_duplicate_paths(line['relPaths'])
    return line

    
with open(sys.argv[1]) as f:
    keys = json.load(f)

with open(sys.argv[2]) as f:
    relPaths = json.load(f)

if (len(sys.argv) > 3):
    apikey = sys.argv[3]
else:
    apikey = None

if not os.path.exists(os.path.dirname("fbconcepts/")):
    os.makedirs(os.path.dirname("fbconcepts/"))
relpath_map = json_array_to_map(relPaths, 'qId')

print ("[")
for i, line in enumerate(keys):
    id = line['qId']
    concepts = [key['concept'] for key in keys[i]['freebaseMids']]
    key_list = [key['mid'] for key in keys[i]['freebaseMids'] if key['mid'] != ""]
    concept_paths = [] 
    for k in key_list:
        if apikey:
            url = 'https://www.googleapis.com/freebase/v1/topic/m/' + k.split(".")[1]
            urlresp = urlopen(url + '?key=' + apikey)
            resp = json.loads(urlresp.read().decode('utf-8'))
            with open('fbconcepts/' + k + '.json', 'w') as f:
                print(json.dumps(resp, indent=4), file=f)
        else:
            with open('fbconcepts/' + k + '.json') as f:
                resp = json.load(f)
        concept_paths.extend(walk_node(resp, [], concepts))
    concept_paths = list(set(concept_paths))  
    new = find_branch_of_path(id, relpath_map, concept_paths)
    merged = merge_paths(id, relpath_map, new)
    if (i+1 != len(keys)):
        print(' ' + json.dumps(merged, sort_keys=True) + ",")
    else:
        print(' ' + json.dumps(merged, sort_keys=True))
print("]")
