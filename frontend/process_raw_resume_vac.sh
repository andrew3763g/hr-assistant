#!/bin/bash

for f in ((ls resume_raw/)); 
do
    echo "File: $f"
done
#java -jar tika-app-3.2.2.jar -t resume_raw resume
#java -jar tika-app-3.2.2.jar -t vacancy_raw vacancy
