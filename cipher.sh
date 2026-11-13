#!/bin/bash

echo "Word Given: $1" 

x=$(echo -n "$1" | base64)

echo $x
