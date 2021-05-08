#!/bin/bash
for ip in $( cat $1 ); do
	echo $ip | tee -a $2.txt
done
