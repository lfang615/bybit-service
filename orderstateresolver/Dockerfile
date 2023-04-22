FROM python:3.11.1

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose the port on which the application will run
EXPOSE 8000

# Start the application
CMD ["uvicorn", "orderstateresolver.app.main:app", "--host", "0.0.0.0", "--port", "5000"]


