# CyVox-Server

## Overview

CyVox-Server is the backend server for CyVox, a voice authentication and voice recognition platform designed for Law Enforcement Agencies (LEAs). It provides secure APIs for user enrollment, voiceprint management, and authentication workflows.

## Features

- RESTful API for voice enrollment and verification
- Secure user management and authentication
- Integration with voice recognition and anti-spoofing models
- Logging and audit trails for compliance
- Scalable and modular architecture

## Getting Started

### Prerequisites

- Python (3.10+)
- MongoDB
- FastAPI
- SpeechBrain

### Installation

```bash
git clone https://github.com/CodingPirates70/CyVox-Server.git
cd CyVox-Server
pip install -r requirements.txt
```

### Configuration

Copy `.env.example` to `.env` and update environment variables as needed.

### Running the Server

```bash
uvicorn main:app --reload
```

## API Endpoints

- `POST /auth/register` — Enroll a new user and its voice
- `POST /complaint/register` — Registers a user's complaints with nessecary Metadata
- `GET /user/:id` — Retrieve user details
- `GET /complaint/:id` — Retrieve complaint details

See API Documentation at `/docs` after running the server for full details.

## Security

- All endpoints require authentication (JWT)
- Voice data is encrypted at rest and in transit
- Role-based access control for LEA personnel

## License

This project is licensed under the MIT License.