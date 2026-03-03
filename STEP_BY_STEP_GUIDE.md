# Complete Deployment Guide — DualMind
### For complete beginners. No experience needed.

---

## What you're building

A chatbot that runs on the internet, accessible by anyone with the link.
Your files live on GitHub. Your app runs on Railway. Redis stores chat history.

```
You (your computer)
    → GitHub (stores your code)
        → Railway (runs your app on the internet)
            → Redis (stores user chat sessions)
```

---

## PART 1 — Set up your computer

### Step 1: Find your Terminal

This is the black window where you type commands.

- **Windows**: Press the Windows key, type `cmd`, press Enter. Or search for "Command Prompt".
- **Mac**: Press Cmd + Space, type `terminal`, press Enter.
- **Linux**: Press Ctrl + Alt + T.

You'll see a blinking cursor. This is where you'll type all commands in this guide.

---

### Step 2: Install Git

Git is a tool that saves your code and sends it to GitHub.

**On Windows:**
1. Go to https://git-scm.com/download/windows in your browser
2. Click the download button — it downloads a .exe file
3. Double-click the .exe file to install it
4. Click "Next" on every screen — the defaults are all fine
5. When it finishes, close and reopen your terminal
6. Now type this to check it worked:
```
git --version
```
You should see something like: `git version 2.43.0`

**On Mac:**
1. Open your terminal
2. Type this and press Enter:
```
git --version
```
3. If Git isn't installed, a popup will appear asking to install it — click Install
4. Wait for it to finish, then type `git --version` again to confirm

**On Linux:**
```
sudo apt update && sudo apt install git
```

---

### Step 3: Configure Git with your name

This is a one-time setup. Copy these two commands into your terminal one at a time.
Replace the name and email with your own:

```
git config --global user.name "John Smith"
```
```
git config --global user.email "john@example.com"
```

No output means it worked.

---

## PART 2 — Create a GitHub account and repository

GitHub is a website that stores your code online.

### Step 4: Create a GitHub account

1. Go to https://github.com
2. Click "Sign up"
3. Enter your email, create a password, choose a username
4. Verify your email address

---

### Step 5: Create a new repository

A repository (repo) is like a folder for your project on GitHub.

1. Once logged in to GitHub, click the **+** button in the top right corner
2. Click **"New repository"**
3. Fill in:
   - Repository name: `dualmind`
   - Keep it **Public**
   - Do NOT tick "Add a README file"
4. Click **"Create repository"**
5. You'll see a page with setup instructions — leave this open, you'll need it in a moment

---

## PART 3 — Set up your project folder

### Step 6: Create a folder for your project

In your terminal, type these commands one at a time:

**On Windows:**
```
cd Desktop
mkdir dualmind
cd dualmind
```

**On Mac/Linux:**
```
cd ~/Desktop
mkdir dualmind
cd dualmind
```

You are now inside a folder called `dualmind` on your Desktop.

---

### Step 7: Copy all the project files into this folder

Take these 5 files (which you downloaded from this chat) and copy them into your `dualmind` folder on the Desktop:

```
dualmind/
├── backend.py
├── frontend.html
├── requirements.txt
├── Dockerfile
└── railway.toml
```

To check they're all there, type:
```
ls
```
(On Windows use `dir` instead of `ls`)

You should see all 5 filenames listed.

---

## PART 4 — Push your code to GitHub

### Step 8: Initialise Git in your folder

Make sure you're inside the dualmind folder (you should be from Step 6), then type:

```
git init
```

You'll see: `Initialized empty Git repository in .../dualmind/.git/`

---

### Step 9: Add all your files to Git

```
git add .
```

The dot means "add everything". No output means it worked.

---

### Step 10: Save your files in Git (called a "commit")

```
git commit -m "initial commit"
```

You'll see a list of your files being saved.

---

### Step 11: Connect your folder to GitHub

Go back to the GitHub page from Step 5. You'll see a section called
**"…or push an existing repository from the command line"**.

Copy the three commands shown there. They'll look like this
(but with YOUR username instead of YOUR_USERNAME):

```
git remote add origin https://github.com/YOUR_USERNAME/dualmind.git
git branch -M main
git push -u origin main
```

Type each one and press Enter. When you run the last command,
it may ask for your GitHub username and password.

> **Note on password**: GitHub no longer accepts your regular password here.
> You need a Personal Access Token instead. Here's how to get one:
> 1. Go to https://github.com/settings/tokens
> 2. Click "Generate new token (classic)"
> 3. Give it a name like "dualmind"
> 4. Tick the "repo" checkbox
> 5. Click "Generate token" at the bottom
> 6. Copy the token (starts with `ghp_...`) — use this as your password

After the push, go to https://github.com/YOUR_USERNAME/dualmind
and you should see all your files there.

---

## PART 5 — Deploy on Railway

Railway is the service that runs your app on the internet.

### Step 12: Create a Railway account

1. Go to https://railway.app
2. Click "Login" → "Login with GitHub"
3. Authorise Railway to access your GitHub
4. You're in

---

### Step 13: Create a new project

1. Once logged in, click **"New Project"**
2. Click **"Deploy from GitHub repo"**
3. If it asks to configure GitHub access, click "Configure GitHub App" and allow access to your `dualmind` repo
4. Select the `dualmind` repository from the list
5. Railway will immediately start building your app — you'll see build logs streaming

Wait about 2-3 minutes for the build to finish.

---

### Step 14: Add Redis database

Your app needs Redis to store chat history. Here's how to add it:

1. In your Railway project dashboard, click **"+ New"** (top right)
2. Click **"Database"**
3. Click **"Add Redis"**
4. Railway creates a Redis instance and automatically connects it to your app
5. The `REDIS_URL` environment variable is injected automatically — you don't need to do anything else

---

### Step 15: Add your API keys

1. In your Railway dashboard, click on your **app service** (the one that's not Redis — it'll have your repo name)
2. Click the **"Variables"** tab
3. Click **"New Variable"** and add these one at a time:

| Variable Name | Value |
|---|---|
| `OPENAI_API_KEY` | Your OpenAI key starting with `sk-...` |
| `ANTHROPIC_API_KEY` | Your Anthropic key starting with `sk-ant-...` |

4. After adding both, Railway will automatically redeploy your app

> Don't have your API keys yet? See the "Getting API Keys" section at the bottom of this guide.

---

### Step 16: Generate your public URL

1. Click on your app service in Railway
2. Click the **"Settings"** tab
3. Scroll down to **"Networking"**
4. Click **"Generate Domain"**
5. You'll get a URL like: `https://dualmind-production.railway.app`

**Test it's working** by opening this URL in your browser:
```
https://your-app.railway.app/health
```

You should see:
```json
{"status":"ok","redis":"ok","models":{"openai":"gpt-4o","anthropic":"claude-opus-4-5"}}
```

If you see that — your backend is live. 

---

## PART 6 — Set up the frontend

The frontend is the chat interface that users see. It's just an HTML file that anyone can open in their browser.

### Step 17: Update the API URL in the frontend

Right now the frontend is pointed at `localhost:8000` (your computer).
You need to point it at your Railway URL instead.

1. Open `frontend.html` in a text editor
   - **Windows**: Right-click the file → "Open with" → Notepad
   - **Mac**: Right-click → "Open with" → TextEdit (then Format → Make Plain Text)
2. Press Ctrl+F (or Cmd+F on Mac) to open Find
3. Search for: `localhost:8000`
4. Replace it with your Railway URL, for example: `https://dualmind-production.railway.app`
5. Save the file

---

### Step 18: Share the frontend with users

Your `frontend.html` file is now ready to share. Users just open it in their browser.

Options for sharing it:
- **Email it** as an attachment — recipients open it locally in their browser
- **Host it on GitHub Pages** (free) — gives you a public URL for the frontend
- **Put it on Netlify** (free, drag and drop) — go to https://netlify.com, drag the HTML file in

---

## PART 7 — Getting API Keys

### OpenAI (GPT-4o)

1. Go to https://platform.openai.com
2. Sign up or log in
3. Click your profile icon (top right) → **"API keys"**
4. Click **"Create new secret key"**
5. Give it a name (e.g. "dualmind")
6. Copy the key — it starts with `sk-` — save it somewhere safe, you only see it once
7. Go to **"Billing"** → add a payment method and add at least $10 credit

### Anthropic (Claude)

1. Go to https://console.anthropic.com
2. Sign up or log in
3. Click **"API Keys"** in the left sidebar
4. Click **"Create Key"**
5. Give it a name and copy the key — starts with `sk-ant-`
6. Go to **"Billing"** → add at least $5 credit

---

## Troubleshooting

**Build fails on Railway**
- Check the build logs in Railway for the error message
- Most common cause: a file is missing from your GitHub repo
- Go back to Step 9 and make sure all 5 files were added

**Health check returns error**
- Make sure you added both API keys in Step 15
- Make sure Redis was added in Step 14
- Try redeploying: in Railway, click your service → "..." menu → "Redeploy"

**Frontend can't connect to backend**
- Double-check you updated `localhost:8000` to your Railway URL in Step 17
- Make sure your Railway URL doesn't have a trailing slash

**Git asks for password and rejects it**
- Use a Personal Access Token, not your GitHub password (see Step 11 note)

---

## Summary of what you've built

```
frontend.html (runs in user's browser)
      ↓  sends messages to
Railway (your FastAPI backend — always online)
      ↓  parallel calls to
OpenAI API + Anthropic API
      ↓  debate loop → final answer
Redis (stores chat history per user session)
      ↓  final answer back to
frontend.html (displays result)
```

**Monthly cost:** ~$5 (Railway Hobby plan). API costs depend on usage (~$0.05–0.15 per message).
