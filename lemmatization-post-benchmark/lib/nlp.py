# -*- coding: UTF-8 -*-
"""
nlp.py

This module contains a set of nlp engine like lemmatizer taggers.
"""

import os
import sys
from concurrent.futures import ThreadPoolExecutor
import unicodedata

from tqdm import tqdm

import pandas as pd

import treetaggerwrapper
from pie_extended.cli.utils import (get_tagger, 
                                    get_model)
from pie_extended.models.lasla.imports import get_iterator_and_processor
from cltk import NLP
from cltk.core.data_types import Process, Pipeline
from cltk.alphabet.processes import LatinNormalizeProcess
from cltk.dependency.processes import LatinStanzaProcess
import spacy_udpipe
from pycollatinus import Lemmatiseur

from lib.utils import extract_filename_without_extension


class LemmatizerBenchmarkEngine:
    def __init__(self, data: dict, output_tagged_corpus_path: str = "./out_lemmatized_corpus"):
        self.data = data
        self.output_tagged_corpus_path = output_tagged_corpus_path
            
        if not os.path.exists(self.output_tagged_corpus_path):
            os.makedirs(self.output_tagged_corpus_path)
            print(f"[INFO] *> New directory: {self.output_tagged_corpus_path} is created.")
        else:
            print(f"[INFO] *> Directory: {self.output_tagged_corpus_path} is already created.")
        
        self.bulk_data_list = {id_doc: {t_block: block_data} for id_doc, data in self.data.items() for t_block, block_data in data.items() if block_data != "EMPTY"}
        self.tasks = {}
        for id_doc, blocks in self.bulk_data_list.items():
            block_task = [block_data for _, block_data in blocks.items()]
            self.tasks[id_doc] = block_task
        
        self.out_paths_taggers = lambda type_corpus, id_doc : f"./{output_tagged_corpus_path}/{type_corpus}/{extract_filename_without_extension(id_doc)}_tagged.tsv"
        
    def preprocessing_data(self, sequence):
        forggiven_characters=[("ę", "e"), ("æ", "e"), ("œ", "e"),("V", "U"), ("v", "u"), ("J", "I"), ("j", "i"), ("ᑕ", "C"), ("ᗞ", "D"), ("ᗅ", "A"), ("ę", "e"), ("æ", "e"), ("œ", "e"), ("<", ""), ("(", ""), (")", ""), ("\xa0", ""),
                     (">", ""), ("*", ""), ("°", "_"), ("[", ""), ("]", ""), ("«", ""), ("»", ""), 
                     (",", " ,"), (".", " ."), (";", " ;"), ("  ", " "), (" | | ", " "), (" | |", ""), ("\n", ""), ("\t", ""),
                     ("V", "U"), ("v", "u"), ("J", "I"), ("j", "i")]
        for graphem in forggiven_characters:
            sequence=str(sequence).replace(graphem[0], graphem[1])
            #x=x.lower()
            #x=x.split()
            try:
                word = unicodedata.normalize(sequence)
            except:
                word = sequence
        return word
    
    def lemmatizer_rool(self, lem_process, name_tagger, tagger):
        for id_doc, blocks in (pbar := tqdm(self.tasks.items())):
            pbar.set_description(f"{name_tagger.upper()} tagger in progress with doc: {id_doc}")
            #result = [(form, lemma, str(pos)) for _, block_data in blocks.items() for form, lemma, pos in lem_process(self, tagger, block_data)]
            #result = [(form, lemma, str(pos)) for _, block_data in blocks.items() for form, lemma, pos in self.parallel_lemmatization(lem_process, tagger, block_data)]
            #data_list = [block_data for _, block_data in blocks.items()]
            result = [(form, lemma, str(pos)) for form, lemma, pos in self.parallel_lemmatization(lem_process, tagger, blocks)]
            # création de la dataframe et export
            self.generate_df_export(data_doc=result, type_tagger=name_tagger, id_doc=id_doc)
        
        
    def main_lemmatization_process(name, tagger_instance):
        def inter_wrap(lem_process):
            def wrapper(self):
                # afficher le type tagger utilisé
                print(f"[INFO] *> Initialize {name} tagger...")
                # print(f"*> Initialize {name} tagger...")
                # créer le nouveau répertoire de sortie
                if name != "ud_pipe":
                    self.create_dir(path_out=f"{self.output_tagged_corpus_path}/{name}")
                    # création des liste de toks, itère avec la pbar et passage dans la fonction assortie
                    # qui revoie un générateur
                    # tagger = self.taggers_available[name]
                    self.lemmatizer_rool(lem_process=lem_process, name_tagger=name, tagger=tagger_instance)
                else:
                    for type_model, model in tagger_instance.items():
                        self.create_dir(path_out=f"{self.output_tagged_corpus_path}/{type_model}")
                        #tagger = self.taggers_available[name][type_model]
                        self.lemmatizer_rool(lem_process=lem_process, name_tagger=type_model, tagger=model)
            return wrapper
        return inter_wrap
    
    def run_benchmark(self):
        print("[INFO] *> Run all lemmatization benchmark...")
        self.cltk_process()
        self.omnia_process()
        self.pie_lasla_process()
        self.ud_pipe_process()
        print("[INFO] *> Benchmark is over ✔️")
    
    @staticmethod
    def create_dir(path_out:str) -> None:
        if not os.path.exists(path_out):
            os.makedirs(path_out)
            print(f"[INFO] *> New directory: {path_out} is created.")
        else:
            print(f"[INFO] *> Directory: {path_out} is already created.")
    
    def parallel_lemmatization(self, l_process, tagger, data_list):
        with ThreadPoolExecutor(max_workers=24) as executor:
            # results = [executor.submit(l_process, self, tagger, data) for data in data_list]
            for future in [executor.submit(l_process, self, tagger, data) for data in data_list]:
                return future.result() 
        
    
    def generate_df_export(self, data_doc: dict, type_tagger: str, id_doc: str) -> None:
        df = pd.DataFrame(data_doc, columns=["form", "lemma", "POS morph"])
        df.to_csv(self.out_paths_taggers(type_tagger, id_doc), sep="\t", encoding="UTF-8", index=False)
        
    @main_lemmatization_process(name="cltk", 
                                tagger_instance=NLP(
                                    language="lat", 
                                    custom_pipeline=Pipeline(
                                        description="A custom pipeline", 
                                        processes=[LatinNormalizeProcess, LatinStanzaProcess], 
                                        language="lat"
                                    )
                                )
                               )
    def cltk_process(self, cltk_tagger, data):
        for token in cltk_tagger.analyze(data).words:
            yield (token.string, token.lemma, str(token.pos.name))
    
    @main_lemmatization_process(name="omnia", 
                                tagger_instance=treetaggerwrapper.TreeTagger(TAGLANG="la", 
                                                                             TAGDIR="treetagger/treetagger")
                               )
    def omnia_process(self, omnia_tagger, data):
        for word in omnia_tagger.tag_text(self.preprocessing_data(data).lower()):
            token = word.split("\t")
            yield (token[0], token[2], str(token[1]))
    
    @main_lemmatization_process(name="nlp_pie_lasla", 
                                tagger_instance=get_tagger(
                                    "lasla", 
                                    batch_size=256, 
                                    device="cpu", 
                                    model_path=None
                                )
                               )
    def pie_lasla_process(self, nlp_pie_tagger, data):
        iterator, processor = get_iterator_and_processor()
        for token in nlp_pie_tagger.tag_str(data, iterator=iterator, processor=processor):
            yield (token['form'], token['lemma'], token['pos'])
    
    @main_lemmatization_process(name="ud_pipe", 
                                tagger_instance={
                                    "ud_pipe_nlp_la_ittb": spacy_udpipe.load('la-ittb'),
                                    "ud_pipe_la-proiel": spacy_udpipe.load('la-proiel'),
                                    "ud_pipe_la-perseus": spacy_udpipe.load('la-perseus')
                                }
                               )
    def ud_pipe_process(self, up_pipe_tagger, data):
        for token in up_pipe_tagger(data):
            yield (token.text, token.lemma_, token.pos_)
    
    @main_lemmatization_process(name="collatinus", 
                                tagger_instance=Lemmatiseur())
    def collatinus_process(self, collatinus_tagger, data):
        # Only for test (not included in benchmark)
        r = collatinus_tagger.lemmatise_multiple(data, pos=True, get_lemma_object=False, as_list=True)
        print(r)
        sys.exit()