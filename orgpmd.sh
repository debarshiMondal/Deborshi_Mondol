#!/bin/bash

#classes

rm PMDReport/orgpmdoutput/src/classes/*

for filename in `ls src/classes/*.cls `

do



sh /software/codedev/pmd/pmd-bin-6.36.0/bin/run.sh pmd -dir $filename -format text -R patrule.xml > $filename"_orgpmdtemp.txt"

cat $filename"_orgpmdtemp.txt" | sed 's/.*classes\///g' > PMDReport/orgpmdoutput/$filename"_orgpmd.txt"

rm $filename"_orgpmdtemp.txt"

done


#triggers

#!/bin/bash

rm PMDReport/orgpmdoutput/src/triggers/*

for filename in `ls src/triggers/*.trigger `

do



sh /software/codedev/pmd/pmd-bin-6.36.0/bin/run.sh pmd -dir $filename -format text -R patrule.xml > $filename"_orgpmdtemp.txt"

cat $filename"_orgpmdtemp.txt" | sed 's/.*triggers\///g' > PMDReport/orgpmdoutput/$filename"_orgpmd.txt"

rm $filename"_orgpmdtemp.txt"

done


