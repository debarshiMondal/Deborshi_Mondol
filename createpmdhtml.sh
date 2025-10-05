#rm /data/public/pmd_test/index.html
#index=/data/public/pmd_test/index.html

#echo "<!DOCTYPE html>" >> $index
#echo "<HTML>" >> $index
#echo "<BODY>" >> $index

ENV=$1

rm /data/public/pmd_rule/$ENV/*

#Classes

for filename in `ls PMDReport/currentpmdoutput/changeSetDeploy/src/classes/*.txt`


do

htmlfilename=`echo $filename | sed 's/PMDReport\/currentpmdoutput\/changeSetDeploy\/src\/classes\///g' |sed s/.txt/.html/`

clsfilename=`echo $filename | sed 's/PMDReport\/currentpmdoutput\/changeSetDeploy\/src\/classes\///g' |sed s/.cls_currpmd.txt/.cls/`

currpmdfilename=`echo $filename | sed 's/PMDReport\/currentpmdoutput\/changeSetDeploy\/src\/classes\///g'`

orgpmdfilename=`echo $filename | sed 's/PMDReport\/currentpmdoutput\/changeSetDeploy\/src\/classes\///g' | sed s/currpmd/orgpmd/`

pattern="ApexUnitTestShouldNotUseSeeAllDataTrue\UnusedLocalVariable\|ClassNamingConventions\|FieldDeclarationsShouldBeAtStart\|FieldNamingConventions\|FormalParameterNamingConventions\|LocalVariableNamingConventions\|MethodNamingConventions\|PropertyNamingConventions\|ExcessiveClassLength\|ExcessiveParameterList\|ApexDoc\|ApexCSRF\|AvoidDirectAccessTriggerMap\|AvoidHardcodingId\|AvoidNonExistentAnnotations\|EmptyCatchBlock\|EmptyIfStmt\|EmptyStatementBlock\|EmptyTryOrFinallyBlock\|EmptyWhileStmt\|InaccessibleAuraEnabledGetter\|MethodWithSameNameAsEnclosingClass\|OverrideBothEqualsAndHashcode\|TestMethodsMustBeInTestClasses\|AvoidDmlStatementsInLoops\|AvoidSoqlInLoops\|AvoidSoslInLoops\|OperationWithLimitsInLoop\|ApexBadCrypto\|ApexDangerousMethods\|ApexInsecureEndpoint\|ApexOpenRedirect\|ApexSharingViolations\|ApexSOQLInjection\|ApexSuggestUsingNamedCred"

cat PMDReport/currentpmdoutput/changeSetDeploy/src/classes/$currpmdfilename |sed 's/^.*$/<tr><td>&<\/td><\/tr>/g'|sed  "/$pattern/ s/<td>/<td bgcolor=Tomato>/ p" > PMDReport/currentpmdoutput/changeSetDeploy/src/classes/"$currpmdfilename"_baked

sed -i '1s/^/<table>/' PMDReport/currentpmdoutput/changeSetDeploy/src/classes/"$currpmdfilename"_baked

echo "</table>" >> PMDReport/currentpmdoutput/changeSetDeploy/src/classes/"$currpmdfilename"_baked




cat PMDReport/orgpmdoutput/src/classes/$orgpmdfilename |sed 's/^.*$/<tr><td>&<\/td><\/tr>/g'|sed  "/$pattern/ s/<td>/<td bgcolor=Tomato>/ p" > PMDReport/orgpmdoutput/src/classes/"$orgpmdfilename"_baked

sed -i '1s/^/<table>/' PMDReport/orgpmdoutput/src/classes/"$orgpmdfilename"_baked

echo "</table>" >> PMDReport/orgpmdoutput/src/classes/"$orgpmdfilename"_baked




echo "<html>" >PMDReport/html/$htmlfilename
echo "<body>" >>PMDReport/html/$htmlfilename

echo "<table border="1">" >>PMDReport/html/$htmlfilename


echo "<tr> <td colspan="2" bgcolor="IndianRed"><center><b>" >>PMDReport/html/$htmlfilename
echo " $clsfilename " >>PMDReport/html/$htmlfilename
echo "</center></b></td>" >>PMDReport/html/$htmlfilename
echo "</tr>" >>PMDReport/html/$htmlfilename

echo "<tr>" >>PMDReport/html/$htmlfilename

echo "<td bgcolor="DarkSalmon"><b>" >>PMDReport/html/$htmlfilename
echo "Original PMD Warnings Total : " ` cat PMDReport/orgpmdoutput/src/classes/$orgpmdfilename |wc -l ` >>PMDReport/html/$htmlfilename
echo "</b></td>" >>PMDReport/html/$htmlfilename

echo "<td bgcolor="LightSalmon"><b>" >>PMDReport/html/$htmlfilename
echo "Current PMD Warnings Total : " ` cat PMDReport/currentpmdoutput/changeSetDeploy/src/classes/$currpmdfilename |wc -l ` >>PMDReport/html/$htmlfilename
echo "</b></td>" >>PMDReport/html/$htmlfilename


echo "</tr>" >>PMDReport/html/$htmlfilename

echo "<tr>" >>PMDReport/html/$htmlfilename
echo "<th style="vertical-align:top"><pre>" >>PMDReport/html/$htmlfilename

cat  PMDReport/orgpmdoutput/src/classes/"$orgpmdfilename"_baked >>PMDReport/html/$htmlfilename
echo "</pre></td>" >>PMDReport/html/$htmlfilename


echo "<th style="vertical-align:top"><pre>" >>PMDReport/html/$htmlfilename

cat PMDReport/currentpmdoutput/changeSetDeploy/src/classes/"$currpmdfilename"_baked >>PMDReport/html/$htmlfilename
echo "</pre></td>" >>PMDReport/html/$htmlfilename

echo "</tr>" >>PMDReport/html/$htmlfilename
echo "</table>" >>PMDReport/html/$htmlfilename
echo "</body>" >>PMDReport/html/$htmlfilename
echo "</html>" >>PMDReport/html/$htmlfilename



#echo "<a href="$htmlfilename">$htmlfilename</a><br>" >> $index 


done

#triggers

for filename in `ls PMDReport/currentpmdoutput/changeSetDeploy/src/triggers/*.txt`

do

htmlfilename=`echo $filename | sed 's/PMDReport\/currentpmdoutput\/changeSetDeploy\/src\/triggers\///g' |sed s/.txt/.html/`

clsfilename=`echo $filename | sed 's/PMDReport\/currentpmdoutput\/changeSetDeploy\/src\/triggers\///g' |sed s/.trigger_currpmd.txt/.trigger/`

currpmdfilename=`echo $filename | sed 's/PMDReport\/currentpmdoutput\/changeSetDeploy\/src\/triggers\///g'`

orgpmdfilename=`echo $filename | sed 's/PMDReport\/currentpmdoutput\/changeSetDeploy\/src\/triggers\///g' | sed s/currpmd/orgpmd/ `




echo "<html>" >PMDReport/html/$htmlfilename
echo "<body>" >>PMDReport/html/$htmlfilename

echo "<table border="1">" >>PMDReport/html/$htmlfilename


echo "<tr> <td colspan="2" bgcolor="IndianRed"><center><b>" >>PMDReport/html/$htmlfilename
echo " $clsfilename " >>PMDReport/html/$htmlfilename
echo "</center></b></td>" >>PMDReport/html/$htmlfilename
echo "</tr>" >>PMDReport/html/$htmlfilename

echo "<tr>" >>PMDReport/html/$htmlfilename

echo "<td bgcolor="DarkSalmon"><b>" >>PMDReport/html/$htmlfilename
echo "Original PMD Warnings Total : " ` cat PMDReport/orgpmdoutput/src/triggers/$orgpmdfilename |wc -l ` >>PMDReport/html/$htmlfilename
echo "</b></td>" >>PMDReport/html/$htmlfilename

echo "<td bgcolor="LightSalmon"><b>" >>PMDReport/html/$htmlfilename
echo "Current PMD Warnings Total : " ` cat PMDReport/currentpmdoutput/changeSetDeploy/src/triggers/$currpmdfilename |wc -l ` >>PMDReport/html/$htmlfilename
echo "</b></td>" >>PMDReport/html/$htmlfilename


echo "</tr>" >>PMDReport/html/$htmlfilename

echo "<tr>" >>PMDReport/html/$htmlfilename
echo "<td><pre>" >>PMDReport/html/$htmlfilename


cat  PMDReport/orgpmdoutput/src/triggers/$orgpmdfilename >>PMDReport/html/$htmlfilename
echo "</pre></td>" >>PMDReport/html/$htmlfilename


echo "<td><pre>" >>PMDReport/html/$htmlfilename

cat PMDReport/currentpmdoutput/changeSetDeploy/src/triggers/$currpmdfilename >>PMDReport/html/$htmlfilename

echo "</pre></td>" >>PMDReport/html/$htmlfilename
echo "</tr>" >>PMDReport/html/$htmlfilename
echo "</table>" >>PMDReport/html/$htmlfilename
echo "</body>" >>PMDReport/html/$htmlfilename
echo "</html>" >>PMDReport/html/$htmlfilename



#echo "<a href="$htmlfilename">$htmlfilename</a><br>" >> $index 


done


#echo "</BODY></HTML>" >> $index

#echo `pwd`

cp PMDReport/html/* /data/public/pmd_rule/$ENV
