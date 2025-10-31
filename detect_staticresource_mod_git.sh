#!/bin/bash

###########################################################
# This script detects the added/modified static resources #
###########################################################


main()
{
        SRdir           #pack staticresources folder into zip
        SRresource      #copy .resource and associated meta
        SRxml           #collect staticresources checking meta, if not already collected
        SRcopy          #generate chageSetDeploy/src/staticResource
}

#define variable ##
MyDir=`pwd`
ENV=$3
Dpath=/tmp/${ENV}.StaticResource
Tpath=
commit1=$1
commit2=$2
rm -rf ${Dpath}
mkdir ${Dpath}


#zip#
ZIP()
{
        echo "::: compressing $1 :::"
        cd $1/
        zip -r ../$1.zip * 1>/dev/null
        cd ../
        rm -r $1
}

#copy staticresources folder & associated .xml
###############################################
SRdir()
{

if [ "$commit1" == "FD" ]
then
        find changeSetDeploy/src/staticresources/ -maxdepth 1 -mindepth 1 -type d | \
        cut -d "/" -f 4 > ${Dpath}/foldername
        cat ${Dpath}/foldername

elif [ "$commit1" != "FD" ]
then
        git diff --name-only $commit1 $commit2 src | grep staticresources | cut -d "/" -f3 | uniq | egrep -v -e ".xml|.resource" > ${Dpath}/foldername

fi

        if [ -s ${Dpath}/foldername ]
        then
         for i in `cat ${Dpath}/foldername`
         do 
         echo "::: copying $i.resource-meta.xml :::"
         cp -r src/staticresources/$i  src/staticresources/$i.resource-meta.xml  ${Dpath}/
         cd ${Dpath}
         ZIP $i  
         cd ${MyDir}
         done
        fi

}

#copy resource , associated .xml
################################
SRresource()
{

        git diff --name-only $commit1 $commit2 src | grep staticresources | cut -d "/" -f3 | uniq | grep \.resource| egrep -v -e ".xml"  > ${Dpath}/resourcename


        for i in `cat ${Dpath}/resourcename`
        do
        echo "::: Copying $i & $i-meta.xml :::"
        cp src/staticresources/$i src/staticresources/$i-meta.xml ${Dpath}/
        done
}

#identify meta.xml if not in dir  and resource #
#and prepare the resource ######################
################################################
SRxml()
{

git diff --name-only $commit1 $commit2 src | grep staticresources | cut -d "/" -f3 | uniq | grep meta.xml$ > ${Dpath}/metaxml


        for i in `cat ${Dpath}/metaxml`
        do
                echo "checking resource file/folder for $i"
                RES=`echo $i|xargs basename -s .resource-meta.xml`
                if [ -d src/staticresources/$RES ] && [ -f src/staticresources/$RES.resource ]
                then
                        echo "error: both $RES & $RES.resource available at src/staticresources"
                        exit 1
                elif [ -d ${Dpath}/$RES.zip ] && [ -f ${Dpath}/$RES.resource ]
                then
                        echo "error: both $RES & $RES.resource available at ${Dpath}"
                        exit 1
                fi

                if [ -f ${Dpath}/$RES.zip ] || [ -f ${Dpath}/$RES.resource ]
                then
                        echo "resource $RES is available at ${Dpath}"
                else
                        if [ -d src/staticresources/$RES ]
                        then
                                cp -r src/staticresources/$RES* ${Dpath}/
                                cd ${Dpath}
                                ZIP $RES $RES 
                                cd ${MyDir}
                        else
                                cp src/staticresources/$RES.resource ${Dpath}/
                        fi
                fi
        done
}


SRcopy()
{
        mkdir -p changeSetDeploy/src/staticresources
        rm -f ${Dpath}/metaxml ${Dpath}/resourcename ${Dpath}/foldername
        cp ${Dpath}/*  changeSetDeploy/src/staticresources/
        cd changeSetDeploy/src/staticresources/
        rename  .zip .resource *.zip
        cd ${MyDir}
}



main "$@"
