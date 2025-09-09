FROM mcp_base:latest

RUN cd /app

# Copy agent sources into the container (build context is ./agent)
COPY . .

# Use the preinstalled virtualenv from mcp_base; no need to reinstall requirements
CMD ["python", "agent.py"]
