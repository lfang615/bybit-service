# Build stage for Vue.js frontend
FROM node:16 AS frontend-build

WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Build stage for FastAPI service
FROM python:3.11.1

WORKDIR /app

# Copy frontend build output from the previous stage
COPY --from=frontend-build /app/frontend/dist frontend/dist

# Install FastAPI dependencies
COPY ordermanager/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY ordermanager .

# Run the script to move the static files and replace the references in index.html
RUN ./build_scripts/move_static_files.sh

# Delete the /frontend/dist directory
RUN rm -rf frontend/dist

# Expose the port on which the application will run
EXPOSE 5000

# Start the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "5000"]
