import os
import sys
import urllib.error
import http.client
import json
import ssl
import spacy

from spacy_help_functions import get_entities, create_entity_pairs
from spanbert import SpanBERT
from urllib.request import urlopen, Request
from bs4 import BeautifulSoup


from googleapiclient.discovery import build
from config import DEVELOPER_KEY, SEARCH_ENGINE_ID

def main():
    spanbert = SpanBERT("./pretrained_spanbert") 
    relation_map = {"1":"per:schools_attended", "2":"per:employee_of", "3":"per:cities_of_residence", "4":"org:top_members/employees"}
    entities_of_interest = ["ORGANIZATION", "PERSON", "LOCATION", "CITY", "STATE_OR_PROVINCE", "COUNTRY"]
    objects_map = {"1":["ORGANIZATION"], "2":["ORGANIZATION"], "3":["LOCATION", "CITY", "STATE_OR_PROVINCE", "COUNTRY"], "4":["PERSON"]}
    subjects_map = {"1":["PERSON"], "2":["PERSON"], "3":["PERSON"], "4":["ORGANIZATION"]}
    r = sys.argv[1]
    t = sys.argv[2]
    q = sys.argv[3]
    k = sys.argv[4]
    googleResults = googleQueryAPI(q)
    addContent(q, googleResults)
    extracted_relations = []
    for i in googleResults:
        print(i['url'])
        print("\n", i['content'])
        print("\n \n")
        nlp = spacy.load("en_core_web_lg")
        doc = nlp(i["content"])
        print("\n")
        count = 0
        for sentence in doc.sents:
            count = count + 1
            print("Tokenized sentence: {}".format([token.text for token in sentence]))
            #ents = get_entities(sentence, entities_of_interest)
            #print("spaCy extracted entities: {}".format(ents))
            candidate_pairs = []
            sentence_entity_pairs = create_entity_pairs(sentence, entities_of_interest)
            for ep in sentence_entity_pairs:
                # TODO: keep subject-object pairs of the right type for the target relation (e.g., Person:Organization for the "Work_For" relation
                if ep[1][1] in subjects_map.get(r) and ep[2][1] in objects_map.get(r):
                    candidate_pairs.append({"tokens": ep[0], "subj": ep[1], "obj": ep[2]})  # e1=Subject, e2=Object
                #candidate_pairs.append({"tokens": ep[0], "subj": ep[2], "obj": ep[1]})  # e1=Object, e2=Subject
            #candidate_pairs = [p for p in candidate_pairs if not p["subj"][1] in ["DATE", "LOCATION"]]  
            # ignore subject entities with date/location type
            #print("Candidate entity pairs:")
            #for p in candidate_pairs:
               # print("Subject: {}\tObject: {}".format(p["subj"][0:2], p["obj"][0:2]))
            if len(candidate_pairs) == 0:
                continue
    
            relation_preds = spanbert.predict(candidate_pairs)  # get predictions: list of (relation, confidence) pairs

            # Print Extracted Relations
            #print("\nExtracted relations:")
            for ex, pred in list(zip(candidate_pairs, relation_preds)):
                if pred[0] == relation_map.get(r):
                    print("\tSubject: {}\tObject: {}\tRelation: {}\tConfidence: {:.2f}".format(ex["subj"][0], ex["obj"][0], pred[0], pred[1]))      
        print("sentence count is:", count)
        print("\n")


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
                html_page = urlopen(url).read()
                textBeautify = BeautifulSoup(html_page, 'html.parser')
                #print(textBeautify)
                data = textBeautify.findAll('p')
                #data = textBeautify.prettify().splitlines()
                #data =  "".join(data[:20000])
                #[s.extract() for s in textBeautify(['style', 'script', '[document]', 'head', 'title'])]
                #visible_text = textBeautify.getText()
                data = [p.get_text().replace('\n', '').replace('\t','') for p in data]
                if data:
                    text = " ".join(data)
                    if len(text) > 20000:
                        text = text[:20000]
                else:
                    text = ""
            except (http.client.IncompleteRead, urllib.error.URLError, ssl.CertificateError):
                text = ""
            #print("\n", text)
            #print("\n")
        doc.update({'content': text})

       
if __name__ == '__main__':
    main()
