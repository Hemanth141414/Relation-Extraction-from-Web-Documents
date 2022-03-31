import os
import sys
import urllib.error
import http.client
import json
import ssl
import spacy
import requests
import re

from spacy_help_functions import get_entities, create_entity_pairs
from spanbert import SpanBERT

import urllib.request as client
from urllib.request import urlopen
from bs4 import BeautifulSoup


from googleapiclient.discovery import build
from config import DEVELOPER_KEY, SEARCH_ENGINE_ID

def main():
    spanbert = SpanBERT("./pretrained_spanbert") 
    relation_map = {"1":"per:schools_attended", "2":"per:employee_of", "3":"per:cities_of_residence", "4":"org:top_members/employees"}
    entities_of_interest = ["ORGANIZATION", "PERSON"]
    objects_map = {"1":["ORGANIZATION"], "2":["ORGANIZATION"], "3":["LOCATION", "CITY", "STATE_OR_PROVINCE", "COUNTRY"], "4":["PERSON"]}
    subjects_map = {"1":["PERSON"], "2":["PERSON"], "3":["PERSON"], "4":["ORGANIZATION"]}
    r = sys.argv[1]
    t = sys.argv[2]
    q = sys.argv[3]
    k = sys.argv[4]
    googleResults = googleQueryAPI(q)
    addContent(q, googleResults)
    extracted_relations = []
    ext_rel_map = {}
    for i in googleResults:
        print(i['url'])
        nlp = spacy.load("en_core_web_lg")
        doc = nlp(i["content"])
        print("\n")
        count = 0
        for sentence in doc.sents:
            count = count + 1
            candidate_pairs = []
            sentence_entity_pairs = create_entity_pairs(sentence, entities_of_interest)
            for ep in sentence_entity_pairs:
                candidate_pairs.append({"tokens": ep[0], "subj": ep[1], "obj": ep[2]})  # e1=Subject, e2=Object
                candidate_pairs.append({"tokens": ep[0], "subj": ep[2], "obj": ep[1]})  # e1=Object, e2=Subject
            candidate_pairs = [p for p in candidate_pairs if not p["subj"][1] in ["DATE", "LOCATION", "ORGANIZATION"]]
            candidate_pairs = [p for p in candidate_pairs if not p["obj"][1] in ["DATE", "LOCATION", "PERSON"]]
            if len(candidate_pairs) == 0:
                continue
            relation_preds = spanbert.predict(candidate_pairs)
            for ex, pred in list(zip(candidate_pairs, relation_preds)):
                if pred[0] == relation_map.get(r) and pred[1] > float(t):
                    if ex["subj"][0]+ex["obj"][0] in ext_rel_map.keys():
                        if ext_rel_map[ex["subj"][0]+ex["obj"][0]] < pred[1]:
                            ext_rel_map[ex["subj"][0]+ex["obj"][0]] = pred[1]
                            extracted_relations.remove({'subj':ex["subj"][0] , 'obj':ex["obj"][0] , 'confidence':pred[1]}pred[1])
                            extracted_relations.append({'subj':ex["subj"][0] , 'obj':ex["obj"][0] , 'confidence':pred[1]})
                    else:
                        ext_rel_map[ex["subj"][0]+ex["obj"][0]] = pred[1]
                        extracted_relations.append({'subj':ex["subj"][0] , 'obj':ex["obj"][0] , 'confidence':pred[1]})

        print("sentence count is:", count)
        print("\n" )
    extracted_relations.sort(key=myfunc)
    print(ext_rel_map)
    for i in extracted_relations:
        print(i)
        print("\n")

def myfunc(e):
    return e["confidence"]


def googleQueryAPI(query):
    service = build("customsearch", "v1", developerKey=DEVELOPER_KEY)
    res = service.cse().list(
        q=query,
        cx=SEARCH_ENGINE_ID,
    ).execute()   
    if 'items' in res.keys():
        results = res['items']
        rfmat = [{'id': idx, 'title': result['title'], 'url': result['link'], 'summary': result['snippet']} for idx, result in enumerate(results)]
        return rfmat
    else:
        return []
       
def addContent(query, documents):
    for doc in documents:
        text = ""
        url = doc['url']
        if(url.find("pdf")==-1):
            try:
                res = client.Request(url, data=None, headers = {'User-Agent' : "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.60 Safari/537.36"})
               
                html_page = client.urlopen(res, timeout=50).read()
                #page = requests.get(url=url)
                textBeautify = BeautifulSoup(html_page, 'html5lib')
                data = textBeautify.findAll('p')
                txt = ""
                for p in data:
                    txt = txt +  p.get_text().replace('\n', '').replace('\t','').replace("^", "").replace("[", "(").replace("]", ")") 
                txt = re.sub(r'\([^()]*\)', ' ', txt)
                txt.replace(". ", ".").replace(".", ". ")
                if txt:
                    text = "".join(txt)
                    if len(text) > 20000:
                        text = text[:20000]
                else:
                    text = ""
            except (http.client.IncompleteRead, urllib.error.URLError, ssl.CertificateError):
                text = ""
        doc.update({'content': text})

       
if __name__ == '__main__':
    main()
