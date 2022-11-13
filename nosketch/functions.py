#Useful functions

import numpy as np
import cv2
#import stanza

#text transformation

# The Omnia lemmatizer don't recognize V and J as well as common diptonga. Moreover, some other paratextual characters (optional) can be replaced in order to facilitate tagging

forggiven_characters=[("ę", "e"), ("æ", "e"), ("œ", "e"),("V", "U"), ("v", "u"), ("J", "I"), ("j", "i"), ("ᑕ", "C"), ("ᗞ", "D"), ("ᗅ", "A")]

#a one more complex set of corrections including pountuation and paratextual.
'''
forggiven_characters=[("ę", "e"), ("æ", "e"), ("œ", "e"), ("<", ""), ("(", ""), (")", ""), ("\xa0", ""),
                     (">", ""), ("*", ""), ("°", "_"), ("[", ""), ("]", ""), ("«", ""), ("»", ""), 
                     (",", " ,"), (".", " ."), (";", " ;"), ("  ", " "), (" | | ", " "), (" | |", ""), ("\n", ""), ("\t", ""),
                     ("V", "U"), ("v", "u"), ("J", "I"), ("j", "i")]
'''



def grafias(x):
    for grafia in forggiven_characters:
        x=str(x).replace(grafia[0], grafia[1])
        
        #x=x.lower()
        #x=x.split()
    return x
    

# The Omnia lemmatizer used and old unicode package which is not well recognized by many modern applications. In order to correct that, an utf-conversion must be applied
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



def Paris(s): #special case Par. and variations (the only abreviation case accepted during transcription)
  if s.lower().startswith("pa") and "." in s:
    return "Parisiensis"
  else:
    if "." in s and s[-1]!=".":
      return " . ".join(s.split("."))
    elif "." in s[:-1]:
      return " . ".join(s.split("."))
    else:
      return s



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
  
  
  
#Configuration parameters to apply stanza taggers (future)
config = {
        # Comma-separated list of processors to use
	'processors': 'lemma,pos',
        # Language code for the language to build the Pipeline in
        'lang': 'la',
        # Processor-specific arguments are set with keys "{processor_name}_{argument_name}"
        # You only need model paths if you have a specific model outside of stanza_resources
	'tokenize_model_path': '/home/magistermilitum/stanza/saved_modelsittb.pt',
	'lemma_model_path': '/home/magistermilitum/stanza/saved_models/la_test_lemmatizer.pt',
	'pos_model_path': '/home/magistermilitum/stanza/saved_models/la_test_tagger.pt',
	'pos_pretrain_path': '/home/magistermilitum/stanza/saved_models/fasttext_lat.pt',
        # Use pretokenized text as input and disable tokenization
	'tokenize_pretokenized': True,
  "download_method":None
}


#nlp = stanza.Pipeline(**config) #uncomment if stanza


#function to extract bio_conll format from the stanza tokenizers and Flair ner
def bio_conll(pr_sentence):
  tokenized_text=[token.text for token in pr_sentence]
  conll_text=["O"]*len(tokenized_text)
  for x in pr_sentence.get_spans('ner'):
      if len(x)==1:
        try:
          conll_text[x[0].idx-1]="B-"+x.tag
        except:
          print(x[0].idx, x)
      else:
        conll_text[x[0].idx-1]="B-"+x.tag
        for token in x[1:]:
          conll_text[token.idx-1]="I-"+x.tag
  
  doc = nlp([tokenized_text])
  lemmas=[word.lemma for sent in doc.sentences for word in sent.words]
  poses=[word.pos for sent in doc.sentences for word in sent.words]
  conll_bio=list([a,b,c,d] for a,b,c,d in zip(tokenized_text, lemmas, poses, conll_text))
  return conll_bio
  
  
#function to extract bio_conll format only from the flair ner tagger
def bio_conll_single(pr_sentence):
  tokenized_text=[token.text for token in pr_sentence]
  conll_text=["O"]*len(tokenized_text)
  for x in pr_sentence.get_spans('ner'):
      if len(x)==1:
        try:
          conll_text[x[0].idx-1]="B-"+x.tag
        except:
          print(x[0].idx, x)
      else:
        conll_text[x[0].idx-1]="B-"+x.tag
        for token in x[1:]:
          conll_text[token.idx-1]="I-"+x.tag
  
  return conll_text
