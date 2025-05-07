# Use an official Rasa SDK image as a parent image
FROM rasa/rasa-sdk:3.6.2

# Set the working directory
WORKDIR /app

# Copy requirements and action files
COPY requirements.txt /app/actions/
COPY actions /app/actions
COPY actions/sensor_list.txt /app/actions/sensor_list.txt
COPY actions/actions.py /app/actions/actions.py
COPY actions/sensor_mappings.txt /app/actions/sensor_mappings.txt
# Copy static server script
COPY static_server.py /app/static_server.py

# Copy entrypoint script
COPY entrypoint.sh /app/entrypoint.sh

# Switch to root user to install dependencies
USER root

# Update pip to the latest version
RUN pip install --upgrade pip
RUN pip install -r /app/actions/requirements.txt
# Install mysql-connector-python explicitly if not in requirements.txt
RUN pip install mysql-connector-python

# Create static/attachments directory and set permissions
RUN mkdir -p /app/actions/static/attachments /app/actions/static/logs && \
    chown -R 1001:1001 /app/actions /app/static_server.py && \
    chmod -R 755 /app/actions/static/attachments /app/actions/static/logs && \
    chmod +x /app/entrypoint.sh

# Expose ports for Rasa Action Server (5055) and static file server (8000)
EXPOSE 5055 8000

# Switch back to the non-root user (1001) for runtime
USER 1001

# Use custom entrypoint to start both action server and static server
ENTRYPOINT ["/app/entrypoint.sh"]