#!/bin/bash

testdir=pdp11_tests
pushd $testdir
pwd
for dirname in `(ls)`; do
  echo "dirname=$dirname";
  pdpfilename=`ls $dirname/*.pdp`
  pdpfilename=`basename $pdpfilename`
  echo "pdpfilename=$pdpfilename"

  echo "PYTHON pdp11_parser.py pdp11_tests/$dirname/${pdpfilename}"
  python ../pdp11_parser.py ../pdp11_tests/$dirname/${pdpfilename}

  echo ""
  echo ""
done;

popd