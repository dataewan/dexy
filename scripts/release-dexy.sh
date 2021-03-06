#!/bin/bash -ev

TIMESTAMP=`date +%s`
TEST_DIR="/tmp/test-dexy/$TIMESTAMP"

echo "Running release script in $TEST_DIR"
mkdir -p $TEST_DIR
pushd $TEST_DIR

git clone ~/dev/dexy $TEST_DIR/dexy
cd dexy

python setup.py register sdist --formats=gztar,zip upload

# Copy .tgz .zip dexy packages to external dependencies directory
cp dist/* ~/dev/dexy-site/external-dependencies/

cd ..

# Now set up virtualenv and test install the new dexy.

mkdir test
cd test

virtualenv testenv
source testenv/bin/activate
pip install dexy
pip install dexy-templates
dexy version
dexy templates
