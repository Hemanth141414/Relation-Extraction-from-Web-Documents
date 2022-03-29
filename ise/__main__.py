import os
import sys
import urllib.error
import http.client
import json
import ssl

from urllib.request import urlopen, Request
from bs4 import BeautifulSoup


from googleapiclient.discovery import build
from config import DEVELOPER_KEY, SEARCH_ENGINE_ID

def main():
    r = sys.argv[1]
    t = sys.argv[2]
    q = sys.argv[3]
    k = sys.argv[4]
    googleResults = googleQueryAPI(q)
    addContent(q, googleResults)
    print("Query results are: \n \n \n")
    for i in googleResults:
        print(i)
        print("*********************************************************************************** \n")
	
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
                textBeautify = BeautifulSoup(html_page, 'html5lib')
                data = textBeautify.findAll('p')
                #data = textBeautify.prettify().splitlines()
                #data =  "".join(data[:20000])
                data = [p.get_text().replace('\n', '').replace('\t','') for p in data]
                if data:
                    text = " ".join(data)
                    if len(text) > 20000:
                        text = text[:20000]
                else:
                    text = ""
            except (http.client.IncompleteRead, http.client.RemoteDisconnected, urllib.error.URLError, ssl.CertificateError):
                text = ""
        doc.update({'content': text})

       
if __name__ == '__main__':
    main()
