#Create PMD output


ENV=$1

rm /data/public/PMDOUTPUT/$ENV/*

rm PMDReport/htmlorg/*

rm /data/public/PMDOUTPUT/$ENV/index.html
index=/data/public/PMDOUTPUT/$ENV/index.html

echo "<!DOCTYPE html>" >> $index
echo "<HTML>" >> $index
echo "<BODY>" >> $index

#classes

echo "<tr><td><table style="width:30%" border="1"><tr><th bgcolor="Yellow">Class Name</th><th bgcolor="Yellow">Original Warning Count</th></tr>" >> $index


for filename in `ls PMDReport/orgpmdoutput/src/classes/*.txt`

do

htmlfilename=`echo $filename | sed 's/PMDReport\/orgpmdoutput\/src\/classes\///g' |sed s/.txt/.html/`


clsfilename=`echo $filename | sed 's/PMDReport\/orgpmdoutput\/src\/classes\///g' |sed s/.cls_orgpmd.txt/.cls/`


orgpmdfilename=`echo $filename | sed 's/PMDReport\/orgpmdoutput\/src\/classes\///g'`



echo "<html>" >PMDReport/htmlorg/$htmlfilename
echo "<body>" >>PMDReport/htmlorg/$htmlfilename

echo "<table border="1">" >>PMDReport/htmlorg/$htmlfilename


echo "<tr> <td colspan="2" bgcolor="IndianRed"><center><b>" >> PMDReport/htmlorg/$htmlfilename
echo " $clsfilename " >>PMDReport/htmlorg/$htmlfilename
echo "</center></b></td>" >>PMDReport/htmlorg/$htmlfilename
echo "</tr>" >>PMDReport/htmlorg/$htmlfilename

echo "<tr>" >>PMDReport/htmlorg/$htmlfilename

echo "<tr>" >>PMDReport/htmlorg/$htmlfilename
echo "<td><pre>" >>PMDReport/htmlorg/$htmlfilename


cat PMDReport/orgpmdoutput/src/classes/$orgpmdfilename >> PMDReport/htmlorg/$htmlfilename
echo "</pre></td>" >>PMDReport/htmlorg/$htmlfilename

echo "</table>" >>PMDReport/htmlorg/$htmlfilename
echo "</body>" >>PMDReport/htmlorg/$htmlfilename
echo "</html>" >>PMDReport/htmlorg/$htmlfilename


PMDcount=`cat PMDReport/orgpmdoutput/src/classes/$orgpmdfilename |wc -l` >> $index


echo "<tr><th style="text-align:left"><a href="$htmlfilename">$clsfilename</a></th><th style="text-align:right">${PMDcount}</th></tr>" >> $index

done

echo "</table></td></tr>" >> $index

#triggers




echo "<tr><td><table style="width:30%" border="1"><tr><th bgcolor="Yellow">Trigger Name</th><th bgcolor="Yellow">Original Warning Count</th></tr>" >> $index


for filename in `ls PMDReport/orgpmdoutput/src/triggers/*.txt`

do

htmlfilename=`echo $filename | sed 's/PMDReport\/orgpmdoutput\/src\/triggers\///g' |sed s/.txt/.html/`


clsfilename=`echo $filename | sed 's/PMDReport\/orgpmdoutput\/src\/triggers\///g' |sed s/.trigger_orgpmd.txt/.trigger/`


orgpmdfilename=`echo $filename | sed 's/PMDReport\/orgpmdoutput\/src\/triggers\///g'`



echo "<html>" >PMDReport/htmlorg/$htmlfilename
echo "<body>" >>PMDReport/htmlorg/$htmlfilename

echo "<table border="1">" >>PMDReport/htmlorg/$htmlfilename


echo "<tr> <td colspan="2" bgcolor="IndianRed"><center><b>" >> PMDReport/htmlorg/$htmlfilename
echo " $clsfilename " >>PMDReport/htmlorg/$htmlfilename
echo "</center></b></td>" >>PMDReport/htmlorg/$htmlfilename
echo "</tr>" >>PMDReport/htmlorg/$htmlfilename

echo "<tr>" >>PMDReport/htmlorg/$htmlfilename

echo "<tr>" >>PMDReport/htmlorg/$htmlfilename
echo "<td><pre>" >>PMDReport/htmlorg/$htmlfilename


cat PMDReport/orgpmdoutput/src/triggers/$orgpmdfilename >> PMDReport/htmlorg/$htmlfilename
echo "</pre></td>" >>PMDReport/htmlorg/$htmlfilename

echo "</table>" >>PMDReport/htmlorg/$htmlfilename
echo "</body>" >>PMDReport/htmlorg/$htmlfilename
echo "</html>" >>PMDReport/htmlorg/$htmlfilename


PMDcount=`cat PMDReport/orgpmdoutput/src/triggers/$orgpmdfilename |wc -l` >> $index


echo "<tr><th style="text-align:left"><a href="$htmlfilename">$clsfilename</a></th><th style="text-align:right">${PMDcount}</th></tr>" >> $index

done


echo "</table></td></tr>" >> $index
echo "</BODY></HTML>" >> $index

cp PMDReport/htmlorg/* /data/public/PMDOUTPUT/$ENV/
