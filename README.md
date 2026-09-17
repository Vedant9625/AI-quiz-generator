# AI Interview Command Center

An enterprise-grade mock assessment and interview simulation platform using Python, Streamlit, and the Google Gemini API. 

## Overview
This Streamlit application is a dynamic, advanced interview preparation tool designed to help users crack technical and aptitude rounds. It leverages Google's Gemini 3.6 Flash model to generate unique, non-repeating questions. Users can practice solo, upload their own study materials for AI-based document parsing (RAG), or compete with peers in synchronized, real-time multiplayer challenge rooms.

---

## Implementation Details

**1. Importing Libraries and Initializing AI Client**
*   **Streamlit & Components (`streamlit`, `streamlit-autorefresh`):** Powers the web UI, session states, custom CSS (Glassmorphism), and auto-polling for live multiplayer lobbies.
*   **Google Generative AI (`google.generativeai`):** The core LLM engine responsible for generating structured JSON quiz data based on dynamic prompts.
*   **Document Parsing (`PyPDF2`, `python-docx`):** Extracts raw text from user-uploaded reference materials to feed into the AI context window.
*   **Plotly (`plotly.graph_objects`):** Renders interactive skill radar charts on the dashboard.

**2. Session State Initialization**
The app utilizes complex Streamlit session states (`st.session_state`) to manage user authentication, UI routing, live test timers, score tracking, and multiplayer room states without losing data on page refreshes.

**3. Database Architecture (`database.py`)**
A persistent SQLite3 database (`users.db`) handles user profiles, passwords, live challenge rooms, participant statuses, real-time leaderboards, and bookmarked questions.

**4. Generating the Quiz (`ai_engine.py`)**
The AI engine accepts domains, difficulty levels, and optional custom reference text. It strictly formats the prompt to return an exact JSON array containing questions, options, answers, and detailed explanations, handling rate limits safely.

**5. Main UI Application (`ui_pages.py` & `main.py`)**
Encapsulates all frontend logic. `main.py` handles the secure routing and sidebar navigation, while `ui_pages.py` renders the modular components (Dashboard, Challenge Lobby, Vault, Analytics).

---

## User Guide

### Solo Mock Assessments
1.  **Select Domains OR Upload Material:** Choose predefined technical topics, add custom topics, OR upload a PDF/Word Document (Syllabus/Notes) for the AI to base questions on.
2.  **Configure Test:** Set the difficulty level, time per question, and total number of questions.
3.  **Take the Test:** Answer questions against a live countdown timer. Earn speed bonuses for fast answers.
4.  **Review Results:** View detailed AI explanations for every question and bookmark difficult ones to your Vault.

### Multiplayer Challenge Arena
1.  **Host a Room:** Click "Host a Test" to generate a secure 6-digit room code. Wait in the lobby to approve joining participants.
2.  **Join a Room:** Click "Join a Test" and enter a friend's 6-digit code.
3.  **Synchronized Launch:** The host configures the domains and clicks Start. The AI generates the test once, and all participants are pulled into a synchronized live exam.
4.  **Live Leaderboard:** Upon finishing, view the real-time leaderboard updating as other participants complete their tests.

### Knowledge Vault & Analytics
*   **Skill Radar:** View your overall accuracy across different domains on the home dashboard.
*   **Bookmarks:** Revisit any questions you saved during solo assessments for quick revision.

---

## Installation and Setup

**1. Setting Up the Environment**
Ensure Python 3.9+ is installed on your machine.

**2. Install Dependencies**
Run the following command to install the required libraries:
```bash
pip install streamlit google-generativeai plotly streamlit-autorefresh PyPDF2 python-docx python-dotenv