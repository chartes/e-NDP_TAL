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



from itertools import groupby, chain
from matplotlib import pyplot as plt
from bs4 import BeautifulSoup

import nltk
nltk.download('punkt')
from nltk.tokenize import word_tokenize

from functions import *

current_path=os.path.abspath(os.getcwd())


#----------------------------------GENERATING METADATA-------------------------------


#Extracting correspondance btw number of file and number of volume. Third element is the scriptorium document link. Get a dict as: 'LL105': [9060, 9728, link]

with open("metadata/endp_volumes.txt") as f: metadata=f.readlines()
volumes={x.split(":")[0]:[int(x.split(":")[1].split(" - ")[0].split("_")[-2].lstrip("0")), int(x.split(":")[1].split(" - ")[1].split("_")[-2].lstrip("0"))+1, x.split(":", 1)[1].split(" - ")[-1].strip()] for x in metadata}
#liens=[x for x in metadata]


# Extracting the month date for each volume sector. We must read and transform an external xlsx

month_a=[[x[2], int(x[12].split("_")[2].lstrip("0")), int(x[13].split("_")[2].lstrip("0"))] for x in pd.read_excel("metadata/e-NDP_récolement_lot1_2_LAMOP.xlsx", "Lot1").values.tolist()[10:-1]]
month_b=[[x[2], int(x[12].split("_")[2].lstrip("0")), int(x[13].split("_")[2].lstrip("0"))] for x in pd.read_excel("metadata/e-NDP_récolement_lot1_2_LAMOP.xlsx", "Lot2").values.tolist()[11:-1]]


months=month_a+month_b
month_year=[]
año=""

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
# generate dict with category as key and the list of keywords as value

topics=pd.read_excel("metadata/eNDP Economie V1.xlsx", "Feuille2")
topics.dropna(how="all", inplace=True)
topics.dropna(subset=["LATIN"], inplace=True) #keep only latin keywords
topics[topics["categories"]==""] = np.NaN
topics.fillna(method='ffill', inplace=True) # replace null  values with the value from the previous row

topics=[[x[0], x[3]] for x in topics.values.tolist()]
topics= [[k] +  [j[1] for j in list(v)] for k,v in groupby(sorted(topics, key=lambda x: x[0]), lambda x: x[0])]
topics={x[0]:list(chain(*[y.split(",") for y in x[1:]])) for x in topics}
topics={k:list(set([grafias(vv.strip()) for vv in v if len(vv)>1])) for k,v in topics.items()}





#------------------------------EXTRACTING DATA FROM XML FILES------------------------------------


#dezipping the page xml folder contending all the automatic transcriptions
zip_url="data/endp_pages_all_V7.zip"

import os.path
new_path=os.path.join('xml_files')
#os.mkdir(new_path)

if os.path.exists(new_path):
    shutil.rmtree(new_path)
os.makedirs(new_path)

#dezipping
shutil.unpack_archive(zip_url, new_path)


#------------------------------EXTRACTING THE OMNIA LEMMATIZER-------------------------------
import shutup; shutup.please()
#dezip source
zip_url_b="data/treetagger.zip"

if not os.path.exists("treetagger"):
    os.makedirs("treetagger")

shutil.unpack_archive(zip_url_b, "treetagger")

#authorize executable file
subprocess.check_call(['chmod', '+x', current_path+"/treetagger/treetagger/bin/tree-tagger"])


import treetaggerwrapper
import logging


tagger=treetaggerwrapper.TreeTagger(TAGLANG="la", TAGDIR="treetagger/treetagger")



#------------------------------EXTRACTING DATA FROM THE XML FILES-------------------


#Transforming and stocking data from XML files. this generates a dictionary with id, points and text content. It can take some minutes
nnn=[]
dict_unicodes={} #only texts


dict_registres={} #id, points and text of each line
dict_regions={} #d, points and region type

#Iterating over the folder: Dont forget to load the correct spacename
for filename in glob.glob(new_path+"/raw_plus_manual/*.xml"):
  nombre=filename.split("/")[-1].split(".")[0]
  tree=ET.parse(filename)
  root=tree.getroot()

  ids=[elem.attrib["id"] for elem in tree.findall('.//{http://schema.primaresearch.org/PAGE/gts/pagecontent/2019-07-15}TextLine')]
  points=[point.attrib["points"] for point in tree.findall('.//{http://schema.primaresearch.org/PAGE/gts/pagecontent/2019-07-15}Baseline')]
  nnn.append(points)

  unicodes=[uni.text for uni in tree.findall('.//{http://schema.primaresearch.org/PAGE/gts/pagecontent/2019-07-15}Unicode')]

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

  if "5705" in filename: #testing
    print(xml_content)

  dict_registres[nombre]=[[x[0], square(x[1]), x[2]] for x in xml_content if type(x[2])==str] #line name, rectangular line coordinates and line text
  dict_regions[nombre]=[[x[0], square(x[1]), x[2]] for x in xml_regions if x[2]!="-" ] #region name, rectangular region coordinates and region type

ordenada=sorted(dict_registres.keys())[35:]+sorted(dict_registres.keys())[:35]

dict_registres={k:dict_registres[k] for k in ordenada}
dict_registres={k:v for k,v in dict_registres.items() if len(v)>0}




#--------------------------------MAIN FUNCTION : transforming content to vertical format---------------------------


start_time = time.time()


pages_list=list(dict_registres.keys())
dict_omnia_endp={}
nosketch_vertical="" # the vertical file is a classical column txt/not formatted file but supporting html tags

with open('metadata/dict_omnia_endp_keywords.json', 'r') as json_file: dict_omnia_endp_keywords = json.load(json_file)

random.shuffle(pages_list) #optional

for i, k in enumerate(pages_list): #iterating over each page transcription in xml format
  if "FRAN_0393" in k:
    keywords_c="Unclassed"
    a,b=transformation(k, registres=dict_registres, regions=dict_regions)
    c=copy.deepcopy(b)
    #texto=" ".join(c["block"])
    
    page_id=int(k.split("_")[2].lstrip("0")) #page id: FRAN_0393_09136_L
    #print(numero, k)

    vol=[n for n,m in volumes.items() if page_id in range(m[0], m[1])][0] #volume
    data=[n.replace("_b", "") for n,m in unified_year_month.items() if page_id in range(m[0], m[1]+1)][0] #date: 1358_octobre
    formatted_data=data.split("_",1)[0]+","+data.split("_",1)[0]+"::"+data.split("_",1)[1]
    script_link=[str(m[2])+k+".jpg" for n,m in volumes.items() if page_id in range(m[0], m[1])][0] # link to the scriptorium page image
    dict_omnia_endp[data+"_"+vol+"_"+k]=[]
    id_nosketch=data.split("_",1)[0]+"_"+vol #nosketch doc.id to sorted results

    text=""
    text_nosketch=""

    # The Omnia treetagger tagging
    for kk,vv in c.items(): #iteration occurs inside the content of each detected page region (a c item)
      coordinates=[[",".join([str(y) for y in cc[0]]),len(word_tokenize(cc[1]))] for cc in vv]
      phrase_text=""
      for sent in vv:
      
        if len(sent[1])>1:

          tags_cap=tagger.tag_text(grafias(sent[1])) #keep the original text
          tags_cap=[x.split("\t") for x in tags_cap]
          tags_cap=[x[0] for x in tags_cap]

          tags=tagger.tag_text(grafias(sent[1]).lower()) # pass lowerized text as that produce better pos and lemma
          tags=[x.split("\t") for x in tags]
          tags=[[tags_cap[i], x[1], x[2].split("_", 1)[0],  kk] for i,x in enumerate(tags)]
          dict_omnia_endp[data+"_"+vol+"_"+k].extend(tags)
          tags="\n".join(["\t".join(x) for x in tags])

          converter= lambda x : [x[0], x[1]-120, x[2], x[3]+270 ] if x[1]-120>0 else [x[0], 0, x[2],x[3]+270]
          new_coord=",".join(map(str,converter(sent[0])))
          new_coord='<s img="'+"https://iiif.chartes.psl.eu/images/endp/FRAN_0393_LL_117/"+k+".jpg/"+new_coord+"/full/0/default.jpg"+'">'
          
          phrase_text+=new_coord+"\n"
          phrase_text+=tags+"\n</s>\n"

      text_nosketch+='<g zone="'+kk+'">\n'#Add the tokenized content of each region inside the <s> html tag

         
      text_nosketch+=phrase_text+"</g>\n"
        
    
    text="\n".join(text.split("\n")[1:])

    #Construction of the HTML classes and attributes for the vertical file

    try: #Some pages are not categorized
      keywords=[x[:2] for x in dict_omnia_endp_keywords[data+"_"+vol+"_"+k]]
      keywords=[[x[0], x[0]+"::"+x[1]] for x in keywords] #The :: token separates category from keywords in the vertical file
      keywords_a=list(set([x[0] for x in keywords]))
      keywords_b=list(set([x[1] for x in keywords]))
      keywords_c=",".join(keywords_a+keywords_b)
    except:
      keywords_c="Unclassed"


    #nosketch_vertical+='<doc '+'link="'+script_link+'"'+' id="'+id_nosketch+'"'+' sujet="'+keywords_c+'" '+'volume="'+vol+'" folio="'+k+'" date="'+data.split("_",1)[0]+","+data.split("_",1)[0]+"::"+data.split("_",1)[1]+'">\n'+text_nosketch+"</doc>\n"
    #we just add metadata as tags and attributs
    #"My name is {}, I'm {}".format("John",36) 
    nosketch_vertical+='<doc link="{}" id="{}" sujet="{}" volume="{}" folio="{}" date="{}" >\n{}</doc>\n'.format(script_link, id_nosketch, keywords_c, vol, k, formatted_data, text_nosketch)

  if i%1000==0:
    print(i)
    print("--- %s seconds ---" % (time.time() - start_time))


# saving the vertifcal single file
final_path="vertical_nosketch"
if os.path.exists(final_path):
    shutil.rmtree(final_path)
os.makedirs(final_path)


with open(final_path+"/source", 'w', encoding="utf-8") as f:
        f.write(nosketch_vertical) #Saving the final vertical file