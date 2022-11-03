import pandas as pd
import re
import xml.dom.minidom
import numpy as np
import xml.etree.ElementTree as ET
import cv2
import glob
import copy
import random
import json
import time
import shutil
import os
import subprocess
import sys
import logging
from tqdm import tqdm

from flair.models import SequenceTagger
from flair.data import Sentence

from itertools import groupby, chain
from matplotlib import pyplot as plt
from bs4 import BeautifulSoup

import nltk
nltk.download('punkt')
from nltk.tokenize import word_tokenize

from functions import *

current_path=os.path.abspath(os.getcwd())


#----------------------------------------------ARGPARSE ------------------------------------------------

import argparse
import os
import sys
import warnings

warnings.filterwarnings("ignore")

# Create the parser
parser = argparse.ArgumentParser(description='Script to generate vertical nosketch file from endp transcriptions')
parser.add_argument("-iiif", action="store_true", help="get the IIIF line-level images")
parser.add_argument("-ner", action="store_true", help="get ner tagging from Flair medieval latin model")
parser.add_argument("-mac", action="store_true", help="switch to the mac os version of treetagger")
#parser.add_argument("-stanza", action="store_true", help="switch to the Stanza lemmatizers / pos")
# Execute the parse_args() method
args = parser.parse_args()


#----------------------------------GENERATING METADATA-------------------------------


#Extracting correspondance btw file number (ex. FRAN_0393_04168_L) and volume (ex. LL_117). 
#the third element on the list is the scriptorium volume link. Get a dict as: 'LL105': [9060, 9728, escriptorium link]

with open("metadata/endp_volumes.txt") as f: metadata=f.readlines()
volumes={x.split(":")[0]:[int(x.split(":")[1].split(" - ")[0].split("_")[-2].lstrip("0")), int(x.split(":")[1].split(" - ")[1].split("_")[-2].lstrip("0"))+1, x.split(":", 1)[1].split(" - ")[-1].strip()] for x in metadata}
#liens=[x for x in metadata]

# Extracting the month date for each volume sector. We must read and transform an external xlsx written in two sheets.

month_a=[[x[2], int(x[12].split("_")[2].lstrip("0")), int(x[13].split("_")[2].lstrip("0"))] for x in pd.read_excel("metadata/e-NDP_recolement_lot1_2_LAMOP.xlsx", "Lot1",engine='openpyxl').values.tolist()[10:-1]]
month_b=[[x[2], int(x[12].split("_")[2].lstrip("0")), int(x[13].split("_")[2].lstrip("0"))] for x in pd.read_excel("metadata/e-NDP_recolement_lot1_2_LAMOP.xlsx", "Lot2",engine='openpyxl').values.tolist()[11:-1]]

months=month_a+month_b
month_year=[]

for x in months:
  if "-" not in x[0]: # if not separator
    if " " in x[0]: #capture year
      year=x[0].split()[1]
      month=x[0].split()[0]
      month_year.append([year, month, x[1], x[2]])
    else:
      month=x[0] #yield year
      month_year.append([year, month, x[1], x[2]])

unified_year_month={}
for x in month_year:
  if x[0]+"_"+x[1] in unified_year_month.keys():
    unified_year_month[x[0]+"_"+x[1]+"_b"]=[x[2], x[3]] #some doublons
  else:
    unified_year_month[x[0]+"_"+x[1]]=[x[2], x[3]]


#Extracting keywords from an external xlsx: three columns of data: category ---> french keyword ----> latin equivalent keyword
# generate a dict with category as key and the list of keywords as value

topics=pd.read_excel("metadata/eNDP Economie V1.xlsx", "Feuille2",engine='openpyxl')
topics.dropna(how="all", inplace=True)
topics.dropna(subset=["LATIN"], inplace=True) #keep only latin keywords
topics[topics["categories"]==""] = np.NaN # filling empty rows with null values
topics.fillna(method='ffill', inplace=True) # replace null values with the value from the previous row as categories are multi-row values

topics=[[x[0], x[3]] for x in topics.values.tolist()]
topics= [[k] +  [j[1] for j in list(v)] for k,v in groupby(sorted(topics, key=lambda x: x[0]), lambda x: x[0])]
topics={x[0]:list(chain(*[y.split(",") for y in x[1:]])) for x in topics}
topics={k:list(set([grafias(vv.strip()) for vv in v if len(vv)>1])) for k,v in topics.items()}


#Using the list of tuples with most common corrections for raw htr predictions

# Files with 600 corrected words (25k occurrences)
corrections=pd.read_excel("metadata/corrections_endp.xlsx",engine='openpyxl') #tuples: (wrong word, correction)
corrections={x[0]:x[1] for x in corrections[corrections.apply(lambda x: x["original"]!= x["corrected"], axis=1)].iloc[:, 1:3].values.tolist()}


#------------------------------EXTRACTING DATA FROM XML FILES--------------------------------------------


#dezipping the page xml folder contending all the automatic transcriptions
#zip_url="./endp_pages_all_V7.zip"

import pathlib as pl
import os.path

p=pl.Path(".")
zip_url=list(p.glob("**/endp_pages_all_V7.zip"))[0]

#create new folder
new_path_V7=os.path.join('xml_files')
#os.mkdir(new_path)

if os.path.exists(new_path_V7):
    shutil.rmtree(new_path_V7)
os.makedirs(new_path_V7)

#dezipping
shutil.unpack_archive(zip_url, new_path_V7)



#------------------------------EXTRACTING THE OMNIA LEMMATIZER-----------------------------------------------

#dezipping source
zip_url_b="tools/treetagger/treetagger.zip"

#create new folder
if not os.path.exists("treetagger"):
    os.makedirs("treetagger")

shutil.unpack_archive(zip_url_b, "treetagger")

#authorize executable file on linux environments
subprocess.check_call(['chmod', '+x', current_path+"/treetagger/treetagger/bin/tree-tagger"])

import treetaggerwrapper
import logging

#instantiating tagger object for medieval latin ("lat.par" in treetagger lib)
tagger=treetaggerwrapper.TreeTagger(TAGLANG="la", TAGDIR="treetagger/treetagger")


#------------------------------EXTRACTING THE FLAIR NER latin medieval model-----------------------------------

FLAT_model = SequenceTagger.load('tools/flair/best-model_flat_13_03_2022.pt')
#https://hal.archives-ouvertes.fr/hal-03703239/


#------------------------------EXTRACTING DATA FROM THE XML FILES------------------------------------------------


#Transforming and stocking data from XML files. This generates a dictionary with id, points and text content. It can take some minutes

dict_unicodes={} #only texts
dict_registres={} #id, points and text of each line
dict_regions={} #d, points and region type

#Iterating over the folder: Dont forget to load the correct spacename.
for filename in glob.glob(new_path_V7+"/raw_plus_manual/*.xml"): #14k files (automatic + manual transcriptions)
  nombre=filename.split("/")[-1].split(".")[0]
  tree=ET.parse(filename)
  root=tree.getroot()

  #Extracting and saving id, texts and regions
  ids=[elem.attrib["id"] for elem in tree.findall('.//{http://schema.primaresearch.org/PAGE/gts/pagecontent/2019-07-15}TextLine')]
  points=[point.attrib["points"] for point in tree.findall('.//{http://schema.primaresearch.org/PAGE/gts/pagecontent/2019-07-15}Baseline')]

  unicodes=[uni.text for uni in tree.findall('.//{http://schema.primaresearch.org/PAGE/gts/pagecontent/2019-07-15}Unicode')]
  unicodes=[" ".join([corrections[y] if y in corrections.keys() else Paris(y) for y in x.split() ]) for x in unicodes if x is not None] #introducting corrections

  ids_regions=[elem.attrib["id"] for elem in tree.findall('.//{http://schema.primaresearch.org/PAGE/gts/pagecontent/2019-07-15}TextRegion')]
  #points_regions=[point for point in tree.findall(".//{http://schema.primaresearch.org/PAGE/gts/pagecontent/2019-07-15}TextRegion")]

  points_regions=[]#coordenadas de cada region
  for point in tree.findall(".//{http://schema.primaresearch.org/PAGE/gts/pagecontent/2019-07-15}TextRegion"):
    for y in point:
      try:
        points_regions.append(y.attrib["points"])
      except:
        continue

# working on the automatic layout segmentation
  type_regions=[]
  for elem  in tree.findall('.//{http://schema.primaresearch.org/PAGE/gts/pagecontent/2019-07-15}TextRegion'):
    try:
      type_regions.append(elem.attrib["custom"])
    except:
      type_regions.append("-")

  #dict_unicodes[nombre]=[x for x in unicodes if x!=None]
  xml_content=list(zip(ids, points, unicodes))#tupla: ids, baseline, text
  xml_regions=list(zip(ids_regions, points_regions, type_regions))

  dict_registres[nombre]=[[x[0], square(x[1]), x[2]] for x in xml_content if type(x[2])==str] #line name, rectangular line coordinates and line text
  dict_regions[nombre]=[[x[0], square(x[1]), x[2]] for x in xml_regions if x[2]!="-" ] #region name, rectangular region coordinates and region type


dict_registres={k:dict_registres[k] for k in sorted(dict_registres.keys()) if len(dict_registres[k])>0}



#--------------------------------MAIN FUNCTION : transforming content to vertical format-------------------------------------

start_time = time.time()
registry="registry_files/registry"

pages_list=list(dict_registres.keys()) #list of id files
dict_omnia_endp={}
nosketch_vertical="" # the vertical file is a classical column/tab txt formatted file supporting html tags

with open('metadata/dict_omnia_endp_keywords.json', 'r') as json_file: dict_omnia_endp_keywords = json.load(json_file)

#random.shuffle(pages_list) #optional randomize

for i, k in enumerate(tqdm(pages_list)): #iterating over each transcribed page in xml format and displaying tqdm progress bar
  if "FRAN_0393" in k:
    keywords_c="Unclassed"
    a,b=transformation(k, dict_registres, dict_regions)
    c=copy.deepcopy(b) # deepcopy to avoid overwrite during iteration
    
    #------------------- Generate the header attributs ----------------------------------------------------

    page_id=int(k.split("_")[2].lstrip("0")) #page id: FRAN_0393_09136_L
    vol=[n for n,m in volumes.items() if page_id in range(m[0], m[1])][0] #volume
    data=[n.replace("_b", "") for n,m in unified_year_month.items() if page_id in range(m[0], m[1]+1)][0] #date: 1358_octobre
    formatted_data=data.split("_",1)[0]+","+data.split("_",1)[0]+"::"+data.split("_",1)[1] #data format to nosketch hierarchy 1358::1358_octobre,
    script_link=[str(m[2])+k+".jpg" for n,m in volumes.items() if page_id in range(m[0], m[1])][0] # link to the scriptorium page image
    AN_link="https://www.siv.archives-nationales.culture.gouv.fr/mm/media/download/"+str(k)+"-medium.jpg" #link to the archives nationales image
    id_nosketch=data.split("_",1)[0]+"_"+vol #nosketch doc.id to sorted results in nosketch concordance

    #------------------------------------------------------------------------------------------------------

    #-------------------- Generate the body content ------------------------------------------------------
    text_nosketch=""

    if args.iiif: #if processing on IIIF images (line-level information), otherwise processing AN images (zone-level information, faster)
      registry+="_iiif"
      # The Omnia treetagger tagging
      for kk,vv in c.items(): #iteration occurs inside the content of each detected page region (an c-item)
        coordinates=[[",".join([str(y) for y in cc[0]]),len(word_tokenize(cc[1]))] for cc in vv] #line sqaure coordinates
        phrase_text=""
        for sent in vv: #iterate over line sentences
        
          if len(sent[1])>1:
            tags_cap=tagger.tag_text(sent[1]) #keep the original text
            tags_cap=[x.split("\t")[0] for x in tags_cap]
            
            tags=tagger.tag_text(grafias(sent[1]).lower())# pass lowerized text to treetagger as that produce more accurate pos and lemma
            tags=[x.split("\t") for x in tags]

            if args.ner: #If we want display the NER tagging as a nosketch attribut of the text. This will increase the processing time to 2 hours.
              registry+="_entities"
              FLAT_sentence=Sentence(tags_cap)
              FLAT_model.predict(FLAT_sentence)
              entities=bio_conll_single(FLAT_sentence)

              tags=[[tags_cap[i], x[1], x[2].split("_", 1)[0], entities[i], kk] for i,x in enumerate(tags)] #combining treetagger and Flair results
              
            else:
              tags=[[tags_cap[i], x[1], x[2].split("_", 1)[0],  kk] for i,x in enumerate(tags)]

            tags="\n".join(["\t".join(x) for x in tags])

            converter= lambda x : [x[0], x[1]-120, x[2], x[3]+270 ] if x[1]-120>0 else [x[0], 0, x[2],x[3]+270]#adding context to graphical lines
            str_coord=",".join(map(str,converter(sent[0]))) #string version to indicate graphical section to the iiif api
            str_coord='<s img="https://iiif.chartes.psl.eu/images/endp/FRAN_0393_LL_{}/{}.jpg/{}/full/0/default.jpg">'.format(str(vol[2:]),k,str_coord)
          
            phrase_text+=str_coord+"\n"
            phrase_text+=tags+"\n</s>\n"

        text_nosketch+='<g zone="'+kk+'">\n'#Add the tokenized content of each region inside the <s> html tag
        text_nosketch+=phrase_text+"</g>\n" #closing
       

    else: #if not IIIF, results to page/zone level
      for kk,vv in c.items(): 
        vv=" ".join([t[1] for t in vv])
        if len(vv)>1:
          tags_cap=tagger.tag_text(vv) 
          tags_cap=[x.split("\t")[0] for x in tags_cap]
        
          tags=tagger.tag_text(grafias(vv).lower()) 
          tags=[x.split("\t") for x in tags]

          if args.ner: #if ner tagging
            registry+="_entities"
            
            FLAT_sentence=Sentence(tags_cap)
            FLAT_model.predict(FLAT_sentence)
            entities=bio_conll_single(FLAT_sentence)
            tags=[[tags_cap[i], x[1], x[2].split("_", 1)[0], entities[i], kk] for i,x in enumerate(tags)]

          else:
            tags=[[tags_cap[i], x[1], x[2].split("_", 1)[0],  kk] for i,x in enumerate(tags)]

          tags="\n".join(["\t".join(x) for x in tags])
          
          text_nosketch+='<s zone="'+kk+'">\n'+tags+"\n</s>\n" #Add the tokenized content of each region inside the <s> html tag
          text_nosketch_zones="<s zone"+kk+'<\n'
      
         #------------------------------------------------------------------------------------------------------------

  #--------------------------- Construction of the HTML classes and attributes for the vertical file ------------------

    # adding the topics using the topics json file

    try: #Some pages are not categorized
      keywords=[x[:2] for x in dict_omnia_endp_keywords[data+"_"+vol+"_"+k]]
      keywords=[[x[0], x[0]+"::"+x[1]] for x in keywords] #The :: token separates category from keywords in the vertical file
      keywords=",".join(list(set([x[0] for x in keywords]))+list(set([x[1] for x in keywords])))
    except:
      keywords="Unclassed"
      
    # adding the generated body data and metadata as tags, attributs and head of each doc on the vertical file
    nosketch_vertical+='<doc link="{}" id="{}" sujet="{}" volume="{}" folio="{}" date="{}" >\n{}</doc>\n'.format(AN_link, id_nosketch, keywords, vol, k, formatted_data, text_nosketch)

## Saving the final vertical file
os.makedirs("vertical")
with open("vertical/source", 'w', encoding="utf-8") as f:
        f.write(nosketch_vertical) #Saving the final vertical file
    
## Saving the the right registry file
source = registry
target = 'vertical/endp.txt'
shutil.copy(source, target)
