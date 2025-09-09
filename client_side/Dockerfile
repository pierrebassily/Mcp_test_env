



FROM mcp_base:latest

RUN cd /app

# Copy client sources into the container (build context is ./client_side)
COPY . .

CMD ["python", "client.py"]
