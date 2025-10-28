FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY config.py overseerr_api.py bot.py ./

# Create non-root user for security
RUN useradd -m -u 1000 hermesbot && \
    chown -R hermesbot:hermesbot /app

# Switch to non-root user
USER hermesbot

# Run the bot
CMD ["python", "bot.py"]
