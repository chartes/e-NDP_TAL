endp_nosketch
===


## Install

Convertir une collection de fichiers PAGE (HTR) au format vertical de NoSketch: [https://www.sketchengine.eu/my_keywords/vertical/](https://www.sketchengine.eu/my_keywords/vertical/)

```sh
python3.8 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python endp_nosketch.py
```

- input: placer `endp_pages_all_V7.zip` (cf release) in `./data/endp_pages_all_V7.zip`
- output: `./vertical_nosketch/source`


## `metadata`

`e-NDP_récolement_lot1_2_LAMOP.xlsx`: métadonnées chronologiques et archivistiques de chaque image. Liste fournie par les AN à l’issue des campagnes de numérisation. Facettes de date (année > mois).

`eNDP Economie V1.xlsx`, Feuille2: liste établie manuellement par Darwin Smith des indices lexicaux (latin et français) des topics (comptabilité, chapitre et réunions, personnes, offices, écritures, droit et justice) utilisés comme facettes.

`dict_omnia_endp_keywords.json` : liste précédente au format JSON contenant des varations pour chaque indice lexical.

`endp_volumes.txt` : tableau de concordances volumes / images des folios / collections eScriptorium. Utilisé pour permettre l’affichage de l’image d’une concordance dans noSketch.



## Installation de NoSketch

[https://github.com/ELTE-DH/NoSketch-Engine-Docker](https://github.com/ELTE-DH/NoSketch-Engine-Docker)

```
cd /srv/webapp
git clone https://github.com/ELTE-DH/NoSketch-Engine-Docker.git
sudo systemctl start docker.service
make pull
make run
```

## Chargement du corpus


Le dossier d'installation doit être comme suit:

```
NoSketch-Engine-Docker/
├─ corpora/
│  ├─ endp/
│  │  ├─ vertical/
│  │  │  ├─ source (fichier source à dezipper : https://github.com/chartes/e-NDP_HTR/raw/main/No_Sketch_Engine/endp/vertical/source.zip wget/unzip ou tar)
│  │  ├─ subcorpora/
│  │  │  ├─ subcorps (fichier pour former les sous corpora : https://github.com/chartes/e-NDP_HTR/raw/main/No_Sketch_Engine/endp/subcorpora/subcorps )
│  ├─ registry/
│  │  ├─ endp (fichier contenant les ordres de compilation : https://github.com/chartes/e-NDP_HTR/raw/main/No_Sketch_Engine/registry/endp )
```

PUIS

```
make all
```

OU

```
make pull
make compile
make run
```

Par default le port de déploiement en local c'est 10070, il faudra le changer dans le fichier makefile. 


Après dépôt du corpus, on recompile pour indexer

```
make compile
make run
```



## TODO

- OS conf ?
- revoir conf pour autre lemmatiseur que OMNIA
- param pour la gestion IIIF
- CLI ?

