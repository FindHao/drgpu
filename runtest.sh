#!/bin/bash
for line in `cat reportlist.txt`
do
    python3 entry.py -i $line -m ncu
done