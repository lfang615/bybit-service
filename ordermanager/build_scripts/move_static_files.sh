#!/bin/bash

# Move static files to the FastAPI service's static directory
cp -R ./frontend/dist/* ../static/app/static/

# Replace the references in index.html with FastAPI's templating syntax
sed -i "s|/css/app.954b07c5.css|{{ url_for('static', path='/css/app.954b07c5.css') }}|g" ../static/app/static/index.html
sed -i "s|/css/chunk-vendors.b7c0e0b0.css|{{ url_for('static', path='/css/chunk-vendors.b7c0e0b0.css') }}|g" ../static/app/static/index.html
sed -i "s|/js/app.ee3340b6.js|{{ url_for('static', path='/js/app.ee3340b6.js') }}|g" ../static/app/static/index.html
sed -i "s|/js/chunk-vendors.b9cb4583.js|{{ url_for('static', path='/js/chunk-vendors.b9cb4583.js') }}|g" ../static/app/static/index.html
