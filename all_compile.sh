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

  echo "PYTHON pdp11_compiler.py pdp11_tests/$dirname/${pdpfilename}"
  python ../pdp11_compiler.py ../pdp11_tests/$dirname/${pdpfilename}

  echo ""
  echo ""
done;

popd