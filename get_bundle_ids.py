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

parser = argparse.ArgumentParser()
parser.add_argument('-m', '-manifest', dest='manifest', required=True)
parser.add_argument('-p', '-project', dest='project', required=True)
args = parser.parse_args()
manifest = args.manifest
project = args.project

manifestFile = open(manifest, "r")
new_manifest = "manifests_with_bundle_ids/manifest.%s.non-pcawg.collab_with_bundle_ids.tsv"%project
out = open(new_manifest, "w")

def getBundleId(projectId, objectId):
   api_endpoint = "https://song.cancercollaboratory.org/studies/%s/files/%s"%(projectId, objectId)
   buf = BytesIO()
   c = pycurl.Curl()
   c.setopt(c.URL, api_endpoint)
   c.setopt(c.WRITEFUNCTION, buf.write)
   c.perform()
   output = buf.getvalue()
   file_data = json.loads(output)
   return file_data['analysisId']

def process_manifest(manifestFile):
   file_contents = manifestFile.readlines()
   header = file_contents.pop(0)
   header = header.rstrip("\n")
   out.write("%s\t%s\n"%(header, "bundle_id"))
   for line in file_contents:
      line = line.rstrip("\n")
      data = line.split("\t")
      object_id = data[2]
      project = data[9]   
      bundle_id = getBundleId(project, object_id)
      out.write("%s\t%s\n"%(line, bundle_id))
      

process_manifest(manifestFile)

