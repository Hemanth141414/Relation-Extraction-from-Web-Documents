import os
import sys
import urllib.error
import http.client
import json
import ssl
import spacy
import requests
import re
import socket

from spacy_help_functions import get_entities, create_entity_pairs
from spanbert import SpanBERT

import urllib.request as client
from urllib.request import urlopen
from bs4 import BeautifulSoup


from googleapiclient.discovery import build
from config import DEVELOPER_KEY, SEARCH_ENGINE_ID

def main():
    spanbert = SpanBERT("./pretrained_spanbert") 
    #relations
    relation_map = {"1":"per:schools_attended", "2":"per:employee_of", "3":"per:cities_of_residence", "4":"org:top_members/employees"}
    #entities_of_interest = ["ORGANIZATION", "PERSON"]
    #Entities to extract
    objects_map = {"1":["ORGANIZATION"], "2":["ORGANIZATION"], "3":["LOCATION", "CITY", "STATE_OR_PROVINCE", "COUNTRY"], "4":["PERSON"]}
    subjects_map = {"1":["PERSON"], "2":["PERSON"], "3":["PERSON"], "4":["ORGANIZATION"]}
    r = sys.argv[1]
    t = sys.argv[2]
    q = sys.argv[3]
    k = sys.argv[4]
    print("______")
    print("Parameters: ")
    print("client key: " +DEVELOPER_KEY)
    print("Engine key: " + SEARCH_ENGINE_ID)
    print("relation: " + relation_map.get(r))
    print("Threahold: "+ t)
    print("Query: " + q)
    #Entities we want to extract
    entities_of_interest = []
    entities_of_interest = subjects_map.get(r) + objects_map.get(r)
    extracted_relations = []
    ext_rel_map = {}
    urls = []
    iter_count = 0
    while(len(ext_rel_map.keys())<float(k)):
        iter_count = iter_count + 1
        print("Current Iteration: ", iter_count)
        print("query being processed is : " + q)
        googleResults = googleQueryAPI(q)
        addContent(q, googleResults)
        u_count = 1
        for i in googleResults:
            if i['url'] in urls:
                print("Skipping this url as this appeared in previous iterations")
            print(str(u_count)+"."+i['url'])
            u_count = u_count + 1
            if len(i['content']) == i['text_size']:
                print("Webpage length (num characters):" + str(i['text_size']))
            else:
                print("Trimming webpage content from " + str(i['text_size']) + " to 20000 characters")
            
            urls.append(i['url'])
            #Load spacy model
            nlp = spacy.load("en_core_web_lg")
            #Apply Spacy to raw text
            doc = nlp(i["content"])
            count = 0
            print("Processing sentences \n")
            rel_count = 0
            for sentence in doc.sents:
                count = count + 1
                candidate_pairs = []
                #Create entity pairs
                sentence_entity_pairs = create_entity_pairs(sentence, entities_of_interest)
                for ep in sentence_entity_pairs:
                    candidate_pairs.append({"tokens": ep[0], "subj": ep[1], "obj": ep[2]})  # e1=Subject, e2=Object
                    candidate_pairs.append({"tokens": ep[0], "subj": ep[2], "obj": ep[1]})  # e1=Object, e2=Subject
                neith_sub = objects_map.get(r)
                neith_obj = subjects_map.get(r)
                #Classify Relations for all candidate entity pair for SpanBERT
                candidate_pairs = [p for p in candidate_pairs if not p["subj"][1] in neith_sub]
                candidate_pairs = [p for p in candidate_pairs if not p["obj"][1] in neith_obj]
                if len(candidate_pairs) == 0:
                    continue
                #Get predictions: list of(relation,confidence) pairs
                relation_preds = spanbert.predict(candidate_pairs)
                for ex, pred in list(zip(candidate_pairs, relation_preds)):
                    if pred[0] == relation_map.get(r) and pred[1] > float(t):
                        if ex["subj"][0]+"***"+ex["obj"][0] in ext_rel_map.keys():
                            if ext_rel_map[ex["subj"][0]+"***"+ex["obj"][0]] < pred[1]:
                                ext_rel_map[ex["subj"][0]+"***"+ex["obj"][0]] = pred[1]
                                print("Duplicate relation exists, replacing the one with higher confidence \n")
                                print("subject: " + ex["subj"][0] + "\t Object: " +ex["obj"][0]+ "\t confidence: " + str(pred[1]))
                        else:
                            #Extracted realtions and tokens
                            ext_rel_map[ex["subj"][0]+"***"+ex["obj"][0]] = pred[1]
                            rel_count = rel_count + 1
                            print("\t ===== Extracted Relation =====")
                            print(ex["tokens"])
                            print("subject: " + ex["subj"][0] + "\t Object: " +ex["obj"][0]+ "\t confidence: " +str(pred[1]))
                            print("\n")
                    
                    else:
                        print("\t ===== Extracted Relation =====")
                        print(ex["tokens"])
                        print("Confidence is lower than threshold. Ignoring this \n")

            print("total sentences processed:", count)
            print("Realtions extracted from this website: " + str(rel_count))
            print("\n" )
        dict(sorted(ext_rel_map.items(), key=lambda item: item[1], reverse=True))    
        ite = list(ext_rel_map.items())
        qps = ite[0][0].split("***") 
        q = qps[0] + " " + qps[1]
        if(len(ext_rel_map.keys())<float(k)):
            print("Preparing for second iteration as total relations are less than required.\n")
            print("total extracted relations: ", len(ext_rel_map.keys()))
            print("Required no. of tuples: ", float(k))
            print("\n")
    for i in ext_rel_map.keys():
        val = ext_rel_map[i]
        a = i.split("***")
        extracted_relations.append({'subject':a[0] , 'object':a[1] , 'confidence':val})
    extracted_relations.sort(reverse=True, key=myfunc)
    print("Final extracted relations are: \n")
    print("======================= All Relations for " +relation_map.get(r)+ ": " +str(len(extracted_relations)) +" ===============================")
    for i in extracted_relations:
        print(i)
    print("Total iterations = ", iter_count)    

def myfunc(e):
    return e["confidence"]

#Retriving google results for query
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
#Getting content of url       
def addContent(query, documents):
    for doc in documents:
        text = ""
        url = doc['url']
        if(url.find("pdf")==-1):
            txt_size = 0
            try:
                res = client.Request(url, data=None, headers = {'User-Agent' : "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.60 Safari/537.36"})
               
                html_page = client.urlopen(res, timeout=30).read()
                #page = requests.get(url=url)
                textBeautify = BeautifulSoup(html_page, 'html5lib')
                data = textBeautify.findAll('p')
                txt = ""
                for p in data:
                    txt = txt +  p.get_text().replace('\n', '').replace('\t','').replace("^", "").replace("[", "(").replace("]", ")") 
                txt = re.sub(r'\([^()]*\)', ' ', txt)
                txt.replace(". ", ".").replace(".", ". ")
                if txt:
                    #Return first 20000 characters of extracted web content
                    text = "".join(txt)
                    txt_size = len(text)
                    if len(text) > 20000:
                        text = text[:20000]
                else:
                    text = ""
            except (socket.timeout, http.client.RemoteDisconnected, http.client.IncompleteRead, urllib.error.URLError, ssl.CertificateError):
                text = ""
        doc.update({'text_size': txt_size})       
        doc.update({'content': text})

       
if __name__ == '__main__':
    main()
