#!/bin/bash
npm --prefix chainforge/react-server run build
python setup.py sdist  
pip install dist/chainforge-0.3.7.0.tar.gz

echo "Local build and installation complete."