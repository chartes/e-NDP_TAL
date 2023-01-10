# -*- coding: UTF-8 -*-
"""
data_preprocessor.py

Data Loaders according to the project corpus
to pass HTR corpus to taggers.
"""


import sys
import os
import shutil
import glob
import json

from lxml import etree as ET

class endpDataLoader:
    """
    Specific data loader to prepare endp data
    to lemmatization process.
    """
    def __init__(self, 
                 filtered_layout_gt_list_path: str = "./data_in/ground-truth-layout_list.txt", 
                 in_gt_path: str = "./data_in/ground-truth-htr/",
                 out_gt_filtered_path: str = "./data_filtered/",
                 copy_images: bool = False,
                 verbose: bool = False) -> None:
        self.in_gt_files_path = in_gt_path
        self.filtered_gt_layout_list = [self.extract_filename_without_extension(file_path) for file_path in  open(filtered_layout_gt_list_path, mode="r", encoding="UTF-8").readlines()]
        self.out_gt_with_layout_path = out_gt_filtered_path
        self.verbose = verbose
        if not os.path.exists(self.out_gt_with_layout_path):
            os.makedirs(self.out_gt_with_layout_path)
            print(f"New directory: {self.out_gt_with_layout_path} is created.")
        else:
            res = input(f"The directory: {self.out_gt_with_layout_path} already exists, this action recreate your directory [Y/n]")
            if res.lower() == "y":
                shutil.rmtree(self.out_gt_with_layout_path)
                os.makedirs(self.out_gt_with_layout_path)
                print(f"New directory: {self.out_gt_with_layout_path} is re-created.")
            else:
                print("No action, data loader interrupted, bye !")
                sys.exit()
        self.extensions = ["xml", "jpg", "jpeg"]
        if copy_images:
            for extension in self.extensions:
                self.copy_layout(self.extract_filter_path(extension), extension)
        else:
            # only extract xml
            self.copy_layout(self.extract_filter_path(self.extensions[0]), self.extensions[0])
        print(f"✔️ data filtered and available: {self.out_gt_with_layout_path} and ready to lemmatize.")
        
        self.gt_xml_filtered = [gt_filtered for gt_filtered in glob.glob(f"{self.out_gt_with_layout_path}*.xml")]
        self.gt_structure_to_lemmatize = self.gt_filtered_to_blocks_structure()
    
    # TODO : get this from utils.py 
    @staticmethod
    def extract_filename_without_extension(file: str) -> str:
        return os.path.splitext(os.path.basename(file))[0]
    
    def extract_filter_path(self, extension) -> list:
        return [f for f in glob.glob(self.in_gt_files_path+f"/*{extension}") if self.extract_filename_without_extension(f) in self.filtered_gt_layout_list]
    
    def copy_layout(self, list_to_copy, extension) -> None:
        # sanity check : check if filtered and extracted list of GT path corresponding to the length of the original layout gt files list
        if extension == "xml":
            assert len(self.filtered_gt_layout_list) == len(list_to_copy)
        
        for file_name in list_to_copy:
            source = self.extract_filename_without_extension(file_name)
            destination = f"{self.out_gt_with_layout_path}{source}.{extension}"
            if os.path.isfile(file_name):
                shutil.copy(file_name, destination)
                if self.verbose :
                    print(f"* copy {source} to {destination}")
    
    def gt_filtered_to_blocks_structure(self) -> dict:
        """Retrieve text blocks structure by parsing gt filtered XML
        to lematize.
        template out example:
            {
             "filename_1": {
                 "type_bloc_list_1": "",
                 "type_bloc_commentaire": "defeffeefeffef",
                 ...
 
             } ...

            }
        """
        data_structure = {}
        for file in self.gt_xml_filtered:
            count = 0
            tree = ET.parse(file)
            root = tree.getroot()
            data_structure[file] = {}
            #print(file)
            for elem in tree.findall('.//{http://schema.primaresearch.org/PAGE/gts/pagecontent/2019-07-15}TextRegion'):
                count += 1
                id_region = elem.attrib["id"]
                try:
                    type_region = elem.attrib["custom"]+f"_{count}"
                except KeyError:
                    type_region = "dummyblock"+f"_{count}"
                text = " ".join((" ".join([t for t in elem.itertext()])).split())
                #print(type_region, " ".join((" ".join([t for t in elem.getparent().itertext()])).split()))
                data_structure[file][type_region] = text if text != "" else "EMPTY"
                
        with open('gt_filtered_struct_to_lemmatize.json', 'w') as fp:
            json.dump(data_structure, fp)
        print(f"* Inspect your texts blocks to lemmatize in file: gt_filtered_struct_to_lemmatize.json")
        return data_structure