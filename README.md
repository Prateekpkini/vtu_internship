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

## ☁️ Step 4: Deploying 24/7 for Free on Render

Render's Free Tier allows deploying this monitor as a **Web Service** (using the built-in lightweight Flask server that binds to Render's port) or as a **Background Worker**.

### Deploying as a Web Service (Recommended for Free Tier)

1. **Push your code to GitHub**:
   ```bash
   git add .
   git commit -m "Add Flask server for Render Web Service deployment"
   git push origin main
   ```

2. **Create Web Service on Render**:
   - Go to your [Render Dashboard](https://dashboard.render.com).
   - Click **New +** > **Web Service**.
   - Connect your GitHub repository (`vtu_internship`).
   - Configure settings:
     - **Name**: `vtu-internship-monitor`
     - **Runtime**: `Python 3`
     - **Build Command**: `pip install -r requirements.txt`
     - **Start Command**: `python monitor.py`
     - **Instance Type**: `Free`
   - In **Environment Variables**, add:
     - `SENDER_EMAIL` = `your_actual_gmail@gmail.com`
     - `SENDER_PASSWORD` = `your_16_character_app_password`
     - `RECIPIENT_EMAIL` = `prateekpkini2005@gmail.com`
     - `CHECK_INTERVAL_SECONDS` = `60`
   - Click **Deploy Web Service**.

Render will build the project, bind to the port, and keep the monitor running. You can visit the public URL assigned by Render to view your live monitoring status and health dashboard!

