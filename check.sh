#!/bin/bash

testdir=pdp11_tests
pushd $testdir
echo
pwd
for dirname in `(ls)`; do
  echo "dirname=$dirname";
  pdpfilename=`ls $dirname/*.pdp`
  pdpfilename=`basename $pdpfilename`
  echo "pdpfilename=$pdpfilename"

  echo "DIFF $dirname/${pdpfilename}.o"
  diff $dirname/${pdpfilename}.o $dirname/exp_${pdpfilename}.o  --ignore-trailing-space
  echo "DIFF $dirname/${pdpfilename}.l"
  diff $dirname/${pdpfilename}.l $dirname/exp_${pdpfilename}.l  --ignore-trailing-space

  echo ""
  echo ""
done;

popd