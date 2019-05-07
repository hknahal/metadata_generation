#!/usr/bin/python
# Parses BAM header to generate YAML file

import os
import argparse
import json
import yaml
from io import BytesIO
import pycurl
import re
from collections import OrderedDict
import yamlordereddictloader
import copy
import uuid

#rootDir = "bam_headers"
rootDir = "bam_headers"
yamlsDir = "yamls"

parser = argparse.ArgumentParser()
parser.add_argument('-m', '-manifest', dest='manifest', required=True)
parser.add_argument('-p', '-project', dest='project', required=True)
args = parser.parse_args()
manifest = args.manifest
project = args.project

specimen_type_regex = re.compile("tumour", re.IGNORECASE)

log = open("sc_parse_yaml.log", "w")
out = open("summaries/%s_header_summary.tsv"%project, "w")
out.write("repo_code\tfile_id\tobject_id\tfile_format\tfile_name\tfile_size\tmd5_sum\tindex_object_id\tdonor_id/donor_count\tproject_id/project_count\tstudy\tbundle_id\tRead Group ID (RG)\tLibrary (LB)\tPlatform (PL)\tPlatform Model (PM)\tPlatform Unit (PU)\tPredicted Median Insert Size (PI)\tName of Sequencing Centre (CN)\tDate run was produced (DT)\n")

valid_platform_models = ["CAPILLARY", "LS454", "ILLUMINA" , "SOLID", "HELICOS", "IONTORRENT", "ONT", "PACBIO"]
# LB: Library
# SM: Sample
# PI: Predicted median insert size
# AS: Genome assembly identifier
# CN: Name of sequencing centre producing the read
# PL: Platform/technology userd to produce the reads
# PM: Platform Model
# PU: Platform unit
# DT: Date the run was produced
#flags = ['ID', 'CN', 'PL', 'PM', 'PU', 'LB', 'PI', 'DT', 'AS', 'SM']
#flag_conversions = {'ID': 'read_group_id', 'SM': 'sample', 'LB': 'library_name', 'PL': 'sequencing_platform', 'PM': 'platform_model', 'PU': 'platform_unit', 'PI': 'insert_size', 'CN': 'sequencing_centre', 'DT': 'sequencing_date', 'AS': 'genome_assembly'}
flags = ['ID', 'LB', 'PL', 'PM', 'PU', 'PI', 'CN', 'DT']
flag_conversions = {'ID': 'readGroupId', 'LB': 'libraryName', 'PL': 'sequencingPlatform', 'PM': 'platformModel', 'PU': 'platformUnit', 'PI': 'insertSize', 'CN': 'sequencingCenter', 'DT': 'sequencingDate'}

# parse header from BAM file
def parseHeader(bamFileName):
   header = []
   print("bamFileName=%s"%bamFileName)
   bamFile = open(bamFileName, "r")
   bam_contents = bamFile.readlines()
   for line in bam_contents:
      header_line = line.split("\t")
      tag = header_line.pop(0)
      if tag == '@RG':
         data = {}
         for col in header_line:
            temp = col.split(":", 1)
            flag = temp[0]
            if flag in flags:
               info = temp[1]
               info = info.rstrip("\n")
               data[flag] = info
         header.append(data)
   return header



# Fetch SONG analysis (contains file information)
def fetch_analysis(projectId, analysisId):
   outFile = open("song_jsons/%s.json"%analysisId, "w")
   api_endpoint = "https://song.cancercollaboratory.org/studies/%s/analysis/%s"%(projectId, analysisId)
   print("api_endpoint = %s"%api_endpoint)
   buf = BytesIO()
   c = pycurl.Curl()
   c.setopt(c.URL, api_endpoint)
   c.setopt(c.WRITEFUNCTION, buf.write)
   c.perform()
   output = buf.getvalue()
   file_data = json.loads(output)
   outFile.write(json.dumps(file_data, indent=4))
   return file_data


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


# Fetch control sample from most recent EGA/DCC audit
def get_control_sample(project_id, sample_id):
   audit_file = open("ega_audits/%s_Audit_ICGC28.tsv"%project_id, "r")
   contents = audit_file.readlines()
   contents.pop(0)
   for line in contents:
      data = line.split("\t")
      analyzed_sample_id = data[4]
      seqstrat = data[5]
      matched_sample_id = data[24]
      if seqstrat == "WGS" and analyzed_sample_id == sample_id and matched_sample_id is not None:
         return matched_sample_id

def getGender(donor_id, project):
   #api_endpoint = "https://dcc.icgc.org/api/v1/donors?field=gender&filters=%7B%22donor%22:%7B%22id%22:%7B%22is%22:%22DO50%22%7D%7D%7D&from=1&size=10&order=desc&facetsOnly=false"
   api_endpoint = "https://dcc.icgc.org/api/v1/donors?field=gender&filters=%7B%22donor%22:%7B%22id%22:%7B%22is%22:%22" + "%s"%donor_id + "%22%7D%7D%7D&from=1&size=10&order=desc&facetsOnly=false"
   buf = BytesIO()
   c = pycurl.Curl()
   c.setopt(c.URL, api_endpoint)
   c.setopt(c.WRITEFUNCTION, buf.write)
   c.perform()
   output = buf.getvalue()
   data = json.loads(output)
   if 'gender' in data['hits'][0]:
      return data['hits'][0]['gender']
   else:
      log.write("[MISSING GENDER]: %s %s\n"%(project, donor_id))
      return ''


# Generate YAML file
def createYamlFilePath(project_id, library_strategy, donor_id, sample_id, specimenType):
   library_path = "%s/%s"%(yamlsDir, library_strategy)
   project_path = "%s/%s/%s"%(yamlsDir, library_strategy, project_id)
   donor_path = "%s/%s/%s/%s"%(yamlsDir, library_strategy, project_id, donor_id)
   sample_path = "%s/%s/%s/%s/%s.%s"%(yamlsDir, library_strategy, project_id, donor_id, sample_id, specimenType)
   if not os.path.exists(library_path):
      os.mkdir(library_path)
   if not os.path.exists(project_path):
      os.mkdir(project_path)
   if not os.path.exists(donor_path):
      os.mkdir(donor_path)
   if not os.path.exists(sample_path):
      os.mkdir(sample_path)
   return sample_path

def get_uuid(project_id, submitter_sample_id):
   aliquot_id = str(uuid.uuid5(uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8"), "%s/%s" % (project_id, submitter_sample_id)))
   return aliquot_id

metadata = {}
sourceFile = open(manifest, "r")
contents = sourceFile.readlines()
contents.pop(0)
for line in contents:
   line = line.rstrip("\n")
   data = line.split("\t")
   project_id = data[9]
   if project_id == project:
      pass
   else:
      continue
   print("project_id = %s"%project_id)
   metadata['study'] = project_id
   file_id = data[1]
   object_id = data[2]
   analysis_id = getBundleId(project_id, object_id)
   #analysis_id = data[11]
   file_info = OrderedDict()
   file_data = fetch_analysis(project_id, analysis_id)
   print("analysisId = %s"%analysis_id)
   submitter_donor_id = file_data['sample'][0]['donor']['donorSubmitterId']
   dcc_donor_id = file_data['sample'][0]['donor']['donorId']
   submitter_specimen_id = file_data['sample'][0]['specimen']['specimenSubmitterId']
   dcc_specimen_type = file_data['sample'][0]['specimen']['specimenType']
   submitter_sample_id = file_data['sample'][0]['sampleSubmitterId']
   #aliquot_id = str(uuid.uuid5(uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8"), "%s/%s" % (project_id, submitter_sample_id)))
   aliquot_id = get_uuid(project_id, submitter_sample_id)
   gender = getGender(dcc_donor_id, project_id)
   for item in file_data['file']:
      if item['objectId'] == object_id:
         file_info['fileName'] = item['fileName']
         file_info['fileSize'] = item['fileSize']
         file_info['readGroupIdInFile'] = ''
         file_info['fileMd5sum'] = item['fileMd5sum']
         file_info['path'] = "song://collaboratory/%s/%s"%(analysis_id, object_id)
         file_info['referenceGenome'] = ''
         file_info['fileType'] = item['fileType']
   projectDir = "%s/%s/%s/%s"%(rootDir, project_id, dcc_donor_id, file_id) 
   for header_fileName in os.listdir(projectDir):
      print("fileName = %s"%header_fileName)
      if os.stat("%s/%s"%(projectDir, header_fileName)).st_size != 0:
         metadata = OrderedDict()
         metadata['study'] = project_id
         metadata['donorSubmitterId'] = submitter_donor_id
         metadata['specimenSubmitterId'] = submitter_specimen_id
         metadata['sampleSubmitterId'] = submitter_sample_id
         metadata['donorGender'] = gender
         metadata['aliquotId'] = aliquot_id
         metadata['specimenType'] = dcc_specimen_type
         metadata['libraryStrategy'] = 'WGS'
         metadata['useCntl'] = 'N/A'
         specimenType = "normal"
         if specimen_type_regex.search(dcc_specimen_type):
            control_sample = get_control_sample(project_id, submitter_sample_id)
            metadata['useCntl'] = get_uuid(project_id, control_sample)
            specimenType = "tumour"
         metadata['readGroups'] = []
         header = parseHeader("%s/%s"%(projectDir, header_fileName))
         #print("header = %s\n"%header)
         print("Number of elements in header for %s= %s"%(header_fileName, len(header)))
         for read_group in header:
            read_groups_info = OrderedDict()
            out.write("%s"%line)
            for flag in flags:
               value = read_group.get(flag, "")
               if flag == 'PI':
                  if value != '':
                     value = int(value)
                  else:
                     value = None
               if flag == 'PU' and value != '':
                  value = str(value)
               if flag == 'PL' and value != '':
                  if value == 'HiSeq':
                     value = 'ILLUMINA'
                  if value not in valid_platform_models:
                     log.write("[INCORRECT PLATFORM MODEL %s ] %s %s %s %s %s\n"%(value, project_id, header_fileName, submitter_donor_id, submitter_sample_id, specimenType))
               read_groups_info[flag_conversions[flag]] = value
               out.write("\t%s"%value)
            out.write("\n")
            read_groups_info['files'] = []
            new_file_info = copy.copy(file_info)
            print("read_group_id=%s"%read_groups_info['readGroupId'])
            read_group_id = read_groups_info['readGroupId']
            print("rg_id_in_file before update = %s"%new_file_info['readGroupIdInFile'])
            # make copy of file_info. For some reason, file_info acts as a reference, so any changes 
            # to rg_id_in_file key affects all other copies of file_info in read_groups_info['files'] array. 
            # To get around this, create a new copy of file_info each time
            new_file_info['readGroupIdInFile'] = read_group_id
            print("rg_id_in_file before appending file_info =%s"%new_file_info['readGroupIdInFile'])
            print("METADATA JSON BEFORE FILE_INFO APPENDED TO READ_GROUPS_INFO:\n%s\n"%json.dumps(metadata, indent=4)) 
            read_groups_info['files'].append(new_file_info)
            metadata['readGroups'].append(read_groups_info)
            print("METADATA JSON AFTER APPEND:\n%s\n"%json.dumps(metadata, indent=4))
         sample_path = createYamlFilePath(project_id, "WGS", submitter_donor_id, submitter_sample_id, specimenType)
         print("SAMPLE_PATH=%s"%sample_path)
         #print(json.dumps(metadata, indent=4)) 
         #print("\nYAML:\n")
         #print(yaml.dump(metadata, default_flow_style=False, Dumper=yamlordereddictloader.Dumper))
         yaml.Dumper.ignore_aliases = lambda *args : True
         print(yaml.dump(metadata, open("%s/metadata.yaml"%sample_path, "w"), default_flow_style=False, Dumper=yamlordereddictloader.Dumper))
out.close() 
