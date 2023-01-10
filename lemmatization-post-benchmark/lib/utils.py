# -*- coding: UTF-8 -*-
"""
utils.py

This module groups together I/O utils functions.
"""

import os
import shutil
import subprocess

from pie_extended.cli.utils import download
import spacy_udpipe

def extract_filename_without_extension(file: str) -> str:
        return os.path.splitext(os.path.basename(file))[0]
    
def init_taggers(arch: str = "osx") -> None:
        """Specific for tagger and their dependencies (models)"""
        #> Treetagger Omnia setup
        print(f"* Initialize Omnia tagger for arch: {arch}")
        if arch == "osx":
            treebank_omnia_pkg = "../nosketch/tools/treetagger/treetagger_OSX.zip"
        else:
            treebank_omnia_pkg = "../nosketch/tools/treetagger/treetagger.zip"
        if not os.path.exists("treetagger"):
            os.makedirs("treetagger")
        shutil.unpack_archive(treebank_omnia_pkg, "treetagger")
        subprocess.check_call(['chmod', '+x', "treetagger/treetagger/bin/tree-tagger"])
        print("* Omnia taggger is ready ✔️")
    
        #> NLP-Pie setup
        # model: Lasla
        print("* Initialize Lasla model for NLP Pie tagger")
        do_download = True
        if do_download:
            for dl in download("lasla"):
                x = 1
        print("* NLP-Pie Lasla tagger is ready ✔️")
    
        #> UDPipe via SpaCy setup
        # models: ITTB, PERSEUS, PROEIL
        print("* Initialize UDPipe tagger via SpaCy")
        models_udpipe = ['la-ittb','la-proiel','la-perseus']
        for model in models_udpipe:
            spacy_udpipe.download(model)
        print(f"* UDPipe tagger with models: {models_udpipe} is ready ✔️")
        print("* Other taggers: collatinus, CLTK are ready✔️")