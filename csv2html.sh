#!/bin/bash
#Converts a delimited file to a HTML table

#usage function
f_Usage () {
echo "Usage: $(basename $0) -d <delimiter> -f <delimited-file>"
}

#command line args
while getopts d:f: OPTION
do
    case $OPTION in
        d)  DELIMITER=$OPTARG ;;
        f)  INFILE=$OPTARG ;;
    esac
done

#Less than 2 command line argument, throw Usage
[ "$#" -lt 2 ] && f_Usage && exit 5

DEFAULTDELIMITER=","
#If no delimiter is supplied, default delimiter is comma i.e. ,
SEPARATOR=${DELIMITER:-$DEFAULTDELIMITER}

if [ -f "${INFILE}" ]
        then
                printf "<table border=\"2\">\n"
                sed "s/$SEPARATOR/<\/td><td>/g" $INFILE | while read line
                        do
                                printf "<tr><td>${line}</td></tr>\n"
                done
                printf "</table>"
                echo
fi
