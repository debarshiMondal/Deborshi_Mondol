#!/bin/bash

#classes

rm PMDReport/currentpmdoutput/changeSetDeploy/src/classes/*

for filename in `ls changeSetDeploy/src/classes/*.cls`

do


sh /software/codedev/pmd/pmd-bin-6.36.0/bin/run.sh pmd -dir $filename -format text -R patrule.xml > $filename"_currpmdtemp.txt"

cat $filename"_currpmdtemp.txt" | sed 's/.*classes\///g' > PMDReport/currentpmdoutput/$filename"_currpmd.txt"


rm $filename"_currpmdtemp.txt"

done

#triggers

rm PMDReport/currentpmdoutput/changeSetDeploy/src/triggers/*

for filename in `ls changeSetDeploy/src/triggers/*.trigger`

do


sh /software/codedev/pmd/pmd-bin-6.36.0/bin/run.sh pmd -dir $filename -format text -R patrule.xml > $filename"_currpmdtemp.txt"

cat $filename"_currpmdtemp.txt" | sed 's/.*triggers\///g' > PMDReport/currentpmdoutput/$filename"_currpmd.txt"


rm $filename"_currpmdtemp.txt"

done

