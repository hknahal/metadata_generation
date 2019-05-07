#!/bin/bash
# This script will run samtools to extract BAM header information
# Uses manifest file from Portal as input to create directory structure and to access mounted files

MANIFEST=""
SCORE_CLIENT_PATH="/home/hnahal/score-client-1.6.1/bin"
while getopts "m:" OPTION;
do
   case "$OPTION" in
      m)
         MANIFEST=${OPTARG?}
      ;;
      :)
         echo "Option -$OPTION requires the name of the manifest file" >&2
         exit 1
         ;;
   esac
done

OUT="completed_ids.tsv"
{
read
#while IFS=$'\t' read -r -a data
sed 's/\t/;/g'  | while IFS=';' read -r -a data
do
   file_id=${data[1]}
   object_id=${data[2]}
   donor_id=${data[8]}
   project_id=${data[9]}
   filename=${data[4]}
   # create directory structure to store bam header information
   if [[ ! -e "score-client_bam_headers/$project_id" ]]; then
      mkdir "score-client_bam_headers/$project_id"
   fi
   if [[ ! -e "score-client_bam_headers/$project_id/$donor_id" ]];  then
      mkdir "score-client_bam_headers/$project_id/$donor_id"
   fi
   if [[ ! -e "score-client_bam_headers/$project_id/$donor_id/$file_id" ]]; then
      mkdir "score-client_bam_headers/$project_id/$donor_id/$file_id"
   fi
   output="score-client_bam_headers/${project_id}/${donor_id}/${file_id}/${object_id}.header"
   echo "file_id = ${file_id}"
   echo "donor_id = ${donor_id}" 
   echo "project_id = ${project_id}"
   echo "object_id = ${object_id}"
   echo "" >> stderr.log
   echo "file_id = ${file_id}" >> stderr.log
   echo "donor_id = ${donor_id}" >> stderr.log
   echo "project_id = ${project_id}" >> stderr.log
   echo "object_id = ${object_id}" >> stderr.log
   echo "" >> stderr.log
   echo "${SCORE_CLIENT_PATH}/score-client --profile collab view --header-only --object-id ${object_id}" >>stderr.log
   echo "" >> stderr.log
   echo `${SCORE_CLIENT_PATH}/score-client --profile collab view --header-only --object-id ${object_id} 1>${output} 2>>stderr.log`
   #echo `samtools view -H /mnt/${bundle_id}/${filename} 1>${output} 2>>stderr.log`
   #echo "samtools view -H /mnt/${bundle_id}/${filename} 1>${output} 2>>stderr.log"
   #echo "${project_id}	${donor_id}	${object_id}	${bundle_id}	${filename}	${file_id}"
   #echo "${project_id}	${donor_id}	${object_id}	${bundle_id}	${filename}	${file_id}" >> ${OUT}
done } < ${MANIFEST}
