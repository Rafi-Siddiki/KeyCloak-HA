# 1. Start with a tiny, clean version of Python
FROM python:3.11-slim

# 2. Create a folder inside the container to hold your app
WORKDIR /app

# 3. Copy only the 'shopping list' first
# This helps Docker build faster next time if your code changes but libraries don't
COPY requirements.txt .

# 4. Docker downloads the dependencies by itself here
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy your app code (Docker automatically skips what's in .dockerignore)
COPY . .

# 6. Tell Docker which port your app uses (Flask usually uses 5000)
EXPOSE 5000

# 7. Set the command to start the app automatically
CMD ["python", "app.py"]