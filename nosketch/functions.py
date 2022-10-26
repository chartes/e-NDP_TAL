#Useful functions

import numpy as np
import cv2

#text transformation

# The Omnia lemmatizer don't recognize V and J as well as common diptonga. Moreover, some other paratextual characters (optional) can be replaced in order to facilitate tagging
forggiven_characters=[("ę", "e"), ("æ", "e"), ("œ", "e"), ("<", ""), ("(", ""), (")", ""), ("\xa0", ""),
                     (">", ""), ("*", ""), ("°", "_"), ("[", ""), ("]", ""), ("«", ""), ("»", ""), 
                     (",", " ,"), (".", " ."), (";", " ;"), ("  ", " "), (" | | ", " "), (" | |", ""), ("\n", ""), ("\t", ""),
                     ("V", "U"), ("v", "u"), ("J", "I"), ("j", "i")]


def grafias(x):
    for grafia in forggiven_characters:
        x=str(x).replace(grafia[0], grafia[1])
        
        #x=x.lower()
        #x=x.split()
    return x

# The Omnia lemmatizer used and old unicode package which is not well recognized by many modern application. In order to correct that, an utf-conversion must be applied
def transcription(x):
  try:
    lemma=x.split("_", 1)[0]
    tr=x.split("_", 1)[1]
    try:
      tr=bytes(tr, encoding="raw_unicode_escape").decode("utf-8")
      return lemma, tr
    except:
      return lemma, tr
  except:
    return bytes(x, encoding="raw_unicode_escape").decode("utf-8"), "-"



# XML conversion

#function to transform cloud point to rectangular coordinates
def square(h):
  h=list(map(int, h.replace(",", " ").split(" ")))
  h=list(zip(*[iter(h)]*2))
  h=np.array([h])
  h=cv2.boundingRect(h) #X coordinate, Y coordinate, width, height
  return h





# Function to transform XML extracted content to a single python dictionary
def transformation (filename, registres, regions):
  #print(filename)
  regions_list=["block", "Date", "liste", "entrée", "numérotation"] # the five trained regions

  dict_html={k:[] for k in regions_list} #dictionnary with regions as keys and list of text lines as values
  lista_html=[]

  for i, elem in enumerate(registres[filename]): 
    if len(elem)>1: #avoid empty pages: covers and first pages
      # FOR THE LINES
      longueur=elem[1][0]+elem[1][2] #width starting point + size
      hauteur=elem[1][1]+elem[1][3] #height starting point + size
      central_point=(elem[1][0]+(elem[1][2]/2), elem[1][1]+round((elem[1][3]/3)), elem[1][1]+round((elem[1][3]/3))+round((elem[1][3]/3))) # squared line central point
    
      # FOR THE REGIONS
      region_sorted=sorted(regions[filename], key=lambda l: l[1][2]-l[1][0])#some blocks are inside others
      for x in region_sorted:
        longueur_reg=x[1][0]+x[1][2] #width starting point + size
        hauteur_reg=x[1][1]+x[1][3] #height starting point + size
        central_point_reg=(x[1][0]+(x[1][2]/2), x[1][1]+(x[1][3]/2)) # squared region central point

      
        # Condition: We must find in wich region the central point of each line is localised
        if central_point[0]>x[1][0] and central_point[0]<x[1][0]+x[1][2] and central_point[1]>x[1][1] and central_point[1]<x[1][3]+x[1][1] and central_point[2]>x[1][1]:

        #if longueur<=longueur_reg and hauteur<=hauteur_reg:
          #print(x[2], "\n", elem, "\n\n" )
          #dict_html[x[2].split("type:")[1].split(";")[0]].append(elem[2])
          dict_html[x[2].split("type:")[1].split(";")[0]].append(elem[1:])
          lista_html.append([i, x[2].split("type:")[1].split(";")[0], elem[2]])
          break
  #dict_html={k:v for k,v in dict_html.items() if len(v)>1}

  return lista_html, dict_html



