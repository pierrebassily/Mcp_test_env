# mcp_experimental

## Setup Instructions

### 1. Create a Virtual Environment

Open PowerShell and run:
```powershell
python -m venv venv
```

### 2. Activate the Virtual Environment

On Windows PowerShell:
```powershell
.\venv\Scripts\Activate.ps1
```

### 3. Install Requirements

```powershell
pip install -r requirements.txt
```

### 4. Set Up Your Environment Variables

Create a file named `.env` in the project root with the following content:
```env
AWS_ACCESS_KEY_ID=your-access-key-id
AWS_SECRET_ACCESS_KEY=your-secret-access-key
AWS_SESSION_TOKEN=your-session-token
```

### 5. Run the Server and Agent

#### Run the server:
```powershell
python server_side/server.py
```

#### Open a new terminal, activate the virtual environment again, and run the agent:
```powershell
.\venv\Scripts\Activate.ps1
python agent/agent.py
```

