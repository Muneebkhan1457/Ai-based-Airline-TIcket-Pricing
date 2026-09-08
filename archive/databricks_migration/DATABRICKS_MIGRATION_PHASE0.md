# Phase 0: Databricks Account & Workspace Setup

## Step 1: Create Databricks Account (Free Community Edition)

1. Go to: https://community.cloud.databricks.com/login.html
2. Click **"Sign up"** → Enter email, password, accept terms
3. Verify your email (check inbox)
4. Log in to your new workspace

**You now have:**
- Free Databricks workspace (Community Edition)
- Auto-assigned region (check after login)
- Pre-configured workspace with Compute, Data, SQL, ML sections

---

## Step 2: Verify Community Edition Features

Once logged in, check what's available:

1. **Left sidebar** → Look for:
   - ✅ **Compute** — cluster creation (you'll use this)
   - ✅ **Workspace** — notebook storage
   - ✅ **Data** — file upload & table management
   - ✅ **ML** → **Experiments** & **Models** — this is MLflow UI
   - ❓ **Jobs** — if greyed out or missing, note this (affects scheduler in Phase 5)

2. **Limitations to confirm:**
   - Single-node clusters only? (check Compute → Create Cluster)
   - No paid features or trial warnings? (Community Edition should be truly free)

---

## Step 3: Set Up Databricks CLI (For Local Integration)

You'll need this to let your local code authenticate with Databricks (used in Phase 7 when pricing_engine pulls the MLflow model).

### On Windows (Your System):

1. **Install Databricks CLI:**
   ```powershell
   pip install databricks-cli
   ```

2. **Generate Personal Access Token in Databricks:**
   - In Databricks UI, top-right corner → your profile icon → **User Settings**
   - Left menu → **Access tokens**
   - Click **Generate new token** → give it a name (e.g., "local-migration")
   - Copy the token (you'll need it in next step)

3. **Configure CLI locally:**
   ```powershell
   databricks configure --token
   ```
   When prompted:
   - **Hostname:** Copy from your Databricks workspace URL (e.g., `https://adb-1234567890.cloud.databricks.com`)
   - **Token:** Paste the token you just generated

4. **Verify it works:**
   ```powershell
   databricks workspace list /
   ```
   If you see folders listed, you're authenticated ✅

---

## Step 4: Create a Project Folder in Databricks Workspace

1. In Databricks UI, go to **Workspace** (left sidebar)
2. Click on your username folder (top-level)
3. Create new folder: right-click → **New** → **Folder** → name it `pia-pricing-migration`
4. This folder will hold all your notebooks

---

## Next: Go to Phase 1 (Cluster Setup)

Once you confirm all features in Step 2 and CLI is working, proceed to Phase 1.

**Checkpoint:** 
- [ ] Databricks account created
- [ ] Community Edition features verified
- [ ] Databricks CLI installed & authenticated
- [ ] Project folder `/Users/<your-email>/pia-pricing-migration` created
