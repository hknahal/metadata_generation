#!/usr/bin/python
# Appends bundle_id (analysis_id) from SONG.
# Requires manifest file from Portal, specifically the project ID and object ID) to make SONG API call

import os
import json
import fnmatch
import re
#import xmltodict
import subprocess
from io import BytesIO
import sys
import pycurl
import argparse
import tarfile

#parser = argparse.ArgumentParser()
#parser.add_argument('-m', '-manifest', dest='manifest', required=True)
#parser.add_argument('-p', '-project', dest='project', required=True)
#args = parser.parse_args()
#manifest = args.manifest
#project = args.project


projects = ['PRAD-FR','BRCA-FR','RECA-EU','EOPC-DE','UTCA-FR','ESAD-UK','PRAD-UK','PEME-CA','CLLE-ES','LICA-FR','LUSC-FR','OV-AU','LAML-KR']

#manifestFile = open(manifest, "r")
#new_manifest = "manifests_with_bundle_ids/manifest.%s.non-pcawg.collab_with_bundle_ids.tsv"%project
#out = open(new_manifest, "w")

def getBundleId(projectId, objectId):
   api_endpoint = "https://song.cancercollaboratory.org/studies/%s/files/%s"%(projectId, objectId)
   print("api_endpoint = %s"%api_endpoint)
   buf = BytesIO()
   c = pycurl.Curl()
   c.setopt(c.URL, api_endpoint)
   c.setopt(c.WRITEFUNCTION, buf.write)
   c.perform()
   output = buf.getvalue()
   file_data = json.loads(output)
   return file_data['analysisId']



def getManifest(project):
   manifest_file = "manifests_from_portal/manifest_%s.tar.gz"%project
   out = open("manifests_with_bundle_ids/manifest.%s.bundle_ids.tsv"%project, "w")
   manifest_url = "https://dcc.icgc.org/api/v1/manifests?repos=collaboratory&format=tarball&filters=%7B%22file%22%3A%7B%22repoName%22%3A%7B%22is%22%3A%5B%22Collaboratory%20-%20Toronto%22%5D%7D%2C%22experimentalStrategy%22%3A%7B%22is%22%3A%5B%22WGS%22%5D%7D%2C%22study%22%3A%7B%22is%22%3A%5B%22_missing%22%5D%7D%2C%22fileFormat%22%3A%7B%22is%22%3A%5B%22BAM%22%5D%7D%2C%22donorStudy%22%3A%7B%22is%22%3A%5B%22_missing%22%5D%7D%2C%22projectCode%22%3A%7B%22is%22%3A%5B%22" + "%s"%project + "%22%5D%7D%7D%7D"
   buf = BytesIO()
   c = pycurl.Curl()
   c.setopt(c.URL, manifest_url)
   with open(manifest_file, "wb") as fp:
      c.setopt(c.WRITEDATA, fp)
      c.perform()
      fp.close()
   tar = tarfile.open(manifest_file, 'r:gz')
   for member in tar.getmembers():
      tsv_file = tar.extractfile(member)
      lines = [x.decode('utf8').strip() for x in tsv_file.readlines()]
      header = lines.pop(0)
      out.write("%s\tbundle_id\n"%header)
      for line in lines:
          out.write("%s\t"%line)
          line = line.rstrip("\n")
          data = line.split("\t")
          object_id = data[2]
          bundle_id = getBundleId(project, object_id)
          out.write("\t%s\n"%(bundle_id))
   out.close()

for project in projects:
   getManifest(project)
