#!/bin/bash



for i in {1..5}; do
    time ${@} &>> /dev/null
    # time ${@} 
done
