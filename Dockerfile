FROM python:3.12-slim AS builder

# Update system packages and delete garbage
RUN apt-get update && \
    apt-get install -y graphviz curl && \
    rm -rf /var/lib/apt/lists/*

# Set up workdir
WORKDIR /app

# Copy requirements file tp workdir
COPY requirements.txt .

# Install python dependencies
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Download install yml2dot binary
RUN curl -L https://github.com/mikefarah/yq/releases/download/v4.48.1/yq_linux_amd64 \
    -o /usr/local/bin/yq && \
    chmod +x /usr/local/bin/yq

# Download install yml2dot binary and remove .tar.gz archive
RUN curl -L https://github.com/lucasepe/yml2dot/releases/download/v0.2.0/yml2dot_0.2.0_linux_64-bit.tar.gz \
    -o /tmp/yml2dot.tar.gz && \
    tar -xz -C /tmp -f /tmp/yml2dot.tar.gz && \
    mv /tmp/yml2dot /usr/local/bin/yml2dot && \
    chmod +x /usr/local/bin/yml2dot && \
    rm /tmp/yml2dot.tar.gz


# Runtime
FROM python:3.12-slim AS runtime

# Update system packages and delete garbage
RUN apt-get update && \
    apt-get install -y graphviz && \
    rm -rf /var/lib/apt/lists/*

# Copy already built dependencies from builder
COPY --from=builder /install /usr/local

# Coping yml2dot binary file from builder stage
COPY --from=builder /usr/local/bin/yml2dot /usr/local/bin/yml2dot

# Coping yq binary file from builder stage
COPY --from=builder /usr/local/bin/yq /usr/local/bin/yq

# Copy codebase
COPY . /app

# Set up workdir
WORKDIR /app

# Install project as editable package pip install --no-cache-dir setuptools && \
RUN pip install --no-cache-dir -e .

# Set entrypoint
ENTRYPOINT ["flowguard"]
