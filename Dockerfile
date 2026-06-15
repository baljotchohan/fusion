FROM python:3.11-slim

WORKDIR /app

# Install deps first for layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the backend
COPY . .

# Hugging Face Spaces routes traffic to port 7860
ENV PORT=7860
ENV BAND_MOCK=true
EXPOSE 7860

CMD ["python", "run.py"]
