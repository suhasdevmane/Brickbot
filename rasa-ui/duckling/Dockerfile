# Use the official Haskell image
FROM haskell:8

# Install required libraries
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      libicu-dev libgmp-dev zlib1g-dev && \
    rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /usr/src/duckling

# Clone Duckling sources
RUN git clone https://github.com/facebook/duckling.git .

# Build Duckling
RUN stack setup && \
    stack build --copy-bins duckling-exe

# Expose port
EXPOSE 8000

# Run Duckling HTTP server
CMD ["duckling-exe", "--port", "8000", "--host", "0.0.0.0"]