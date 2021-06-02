#!/bin/bash


if [ $# -eq 0 ]; then
  echo "Wrong arguments"
  exit
fi

first_arg=$1
working_dir="./"
if [[ $first_arg != \./* ]];
then
    working_dir=$(dirname $first_arg)
fi
execute_name=$(basename $first_arg)



cd $working_dir
mkdir reports
cd reports
rm report*.qdrep
rm report*.sqlite
rm report*.csv
cd ..
for i in {1..10}; do
    nsys profile -o reports/report${i}_$execute_name -t cuda  "$@"
    cd reports
    nsys stats -f csv -o report${i}_$execute_name ./report${i}_$execute_name.qdrep
    cd ..
done