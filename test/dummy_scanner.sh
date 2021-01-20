#!/bin/bash
echo "Testing $1"
sleep 1
RND=$(( $RANDOM % 2 ))
if [[ $RND == 1 ]]; then
	echo "Vulnerable"
else
	echo "NOT vulnerable"
fi