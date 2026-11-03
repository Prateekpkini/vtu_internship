# VTU Internship Instant Email Alert Monitor 🚨

Automated Python service that continuously monitors the **VTU Portal (Internyet)** for new **Free & Remote** internships and sends immediate, rich email notifications with direct application links to **`prateekpkini2005@gmail.com`**.

---

## ⚡ Architecture & Improvements

The VTU Internyet portal is a client-side Single Page Application (React/Vite). Plain HTML scraping of `vtu.internyet.in` returns only an empty `<div id="root"></div>`, which would cause standard CSS selectors to always fail.

This monitor connects directly to the underlying official VTU REST API:
- **API Endpoint:** `https://vtuapi.internyet.in/api/v1/internships`
- **Filters:**
  - `sort_by=latest`
  - `category_ids[]=1, 2, 9`
  - `internship_type=Free`
  - `internship_mode=Remote`

### Key Features
- **Accurate Real-Time Detection:** Tracks unique internship IDs to guarantee zero false alerts while instantly detecting any newly dropped listing.
- **Rich Email Alerts:** Formatted with role title, hiring company, duration, positions available, deadline, short description, and direct application links (`https://vtu.internyet.in/internships/{slug}`).
- **Secure Credentials:** Reads Gmail credentials from `.env` or system environment variables to prevent accidental credential leakage in public repositories.
- **Testing Flags:** Includes `--once` for diagnostic runs and `--test-email` to verify Gmail SMTP configuration without waiting for a new listing.

---

## 🛠️ Step 1: Set Up Gmail App Password

Standard Gmail passwords cannot be used for automated SMTP scripts. You need an **App Password**:

1. Go to your **Google Account**: [https://myaccount.google.com/security](https://myaccount.google.com/security)
2. Ensure **2-Step Verification** is turned **ON**.
3. Go to **App Passwords**: [https://myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
   *(Or search for "App passwords" in the top search bar if not directly visible).*
4. Create a new App Password:
   - App name: `VTU Internship Monitor`
   - Click **Create**.
5. Copy the generated **16-character password** (e.g., `abcd efgh ijkl mnop`).

---

## ⚙️ Step 2: Configure Environment

Open `.env` in the project directory and fill in your details:

```env
SENDER_EMAIL=your_actual_gmail@gmail.com
SENDER_PASSWORD=your_16_character_app_password
RECIPIENT_EMAIL=prateekpkini2005@gmail.com
CHECK_INTERVAL_SECONDS=60
```

---

## 🧪 Step 3: Test and Run Locally

### 1. Test Gmail SMTP Configuration
Verify that emails send properly:
```bash
python monitor.py --test-email
```
Check your inbox (`prateekpkini2005@gmail.com`) for a confirmation email.

### 2. Run a Single Sync Test
```bash
python monitor.py --once
```

### 3. Run the Continuous 24/7 Monitor Locally
```bash
python monitor.py
```
*(Press `Ctrl + C` anytime to stop).*

---

## ☁️ Step 4: Deploying 24/7 for Free

### Option A: Render (Recommended Background Worker)

1. **Push to GitHub**:
   ```bash
   git init
   git add .
   git commit -m "Initial commit for VTU Internship Monitor"
   # Create a repo on github.com and link it:
   git remote add origin https://github.com/<your-username>/vtu-internship-monitor.git
   git push -u origin main
   ```
   *(Note: `.env` is ignored by `.gitignore` so your passwords stay private).*

2. **Set up on Render**:
   - Go to [Render.com](https://render.com) and sign in.
   - Click **New +** > **Background Worker**.
   - Connect your GitHub repository.
   - Configure the worker:
     - **Name**: `vtu-internship-monitor`
     - **Runtime**: `Python 3`
     - **Build Command**: `pip install -r requirements.txt`
     - **Start Command**: `python monitor.py`
   - In the **Environment Variables** section, add:
     - `SENDER_EMAIL` = `your_actual_gmail@gmail.com`
     - `SENDER_PASSWORD` = `your_16_character_app_password`
     - `RECIPIENT_EMAIL` = `prateekpkini2005@gmail.com`
     - `CHECK_INTERVAL_SECONDS` = `60`
   - Click **Create Background Worker**.

Render will now keep the script running in the background 24/7. Whenever a new internship drops, an alert will hit your inbox immediately!
