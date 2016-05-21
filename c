#!/bin/sh


mkdir 1
mkdir 2
mkdir 3
mkdir 4

cp parampl.py 1/
cp parampl.py 2/
cp parampl.py 3/
cp parampl.py 4/

cp clear 1/
cp clear 2/
cp clear 3/
cp clear 4/


./clear griewanktest

cd 1
./clear griewanktest
cd ..

cd 2
./clear griewanktest
cd ..

cd 3
./clear griewanktest
cd ..

cd 4
./clear griewanktest
cd ..


