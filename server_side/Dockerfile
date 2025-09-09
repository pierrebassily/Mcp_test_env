FROM mcp_base:latest

RUN cd /app
# Copy server sources into the container (build context is ./server_side)
COPY . .

# Server runtime uses packages already installed in mcp_base
# (No additional pip install needed here)
CMD ["python", "server.py"]