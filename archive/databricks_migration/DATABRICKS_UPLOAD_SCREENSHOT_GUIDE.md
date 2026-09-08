# Upload CSV to Databricks - Visual Guide

## Current Status (From Your Screenshot)
✅ You're already in Databricks Catalog view
✅ I can see the Volume: `pia_data` in the left sidebar
✅ Perfect position to upload!

---

## 🎯 EXACT STEPS TO UPLOAD

### Step 1: Navigate to the Volume Folder
1. In the left sidebar, find: **Volumes (1)**
2. Click on: **pia_data** 
   - Path: `/Volumes/airline_daw/pia_pricing/pia_data/`
3. You should see a folder view (may show flights.csv if already uploaded)

### Step 2: Upload File
1. In the main panel, look for **Upload** button (usually top-right area)
2. Or right-click in the folder → **Upload**
3. Select: `C:\Users\pc\Desktop\data\external_signals_export.csv`
4. Click **Open**

### Step 3: Wait for Upload
- File will upload (should be quick, ~3KB)
- You'll see it appear in the folder as: `external_signals_export.csv`

### Step 4: Verify Upload Complete
- The file should show in the volume
- Full path will be: `/Volumes/airline_daw/pia_pricing/pia_data/external_signals_export.csv`

---

## ✅ After Upload Complete

Tell me:
1. ✅ Upload finished successfully?
2. ✅ File appears in the pia_data volume?
3. ✅ Ready to proceed to STEP 4 (replace Phase 3)?

---

## Alternative: If Volume Upload Doesn't Work

If you can't find the upload button in the Volume view, try this alternative:

**Upload to Workspace (Temporary)**
1. Click **Workspace** in left sidebar
2. Click your home folder
3. Right-click → **Upload file**
4. Select: `C:\Users\pc\Desktop\data\external_signals_export.csv`
5. Note the path (will be `/Users/[your_email]/external_signals_export.csv`)
6. Then in Phase 3 cell, use this path instead

---

## 🚀 Next After Upload

Once uploaded, I'll guide you to:
- **STEP 4:** Open your PIA pricing notebook
- **STEP 4:** Replace Phase 3 cell with the fixed code
- Update the CSV path to match where you uploaded it
- Run Phase 3

**Total time remaining: ~30 minutes**
