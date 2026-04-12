# SQL Investigation Environment - Deployment Guide

## ✅ Pre-Deployment Checklist (ALL PASSED)

- ✅ Health Check: Server online
- ✅ Load Tasks: 3 tasks loaded
- ✅ Reset Environment: Works correctly
- ✅ Quick Test (Correct): Scores 1.0 ✓
- ✅ Quick Test (Incorrect): Scores 0.0 ✓
- ✅ Grader Endpoint: Functional
- ✅ UI Serving: Renders correctly

---

## 🚀 Deployment to Hugging Face Spaces

### Step 1: Create Hugging Face Space

1. Go to [huggingface.co/spaces](https://huggingface.co/spaces)
2. Click **"Create new Space"**
3. Fill in details:
   - **Space name**: `sql-investigation-env`
   - **License**: `openrail` (or your choice)
   - **SDK**: **Docker** ⚠️ (IMPORTANT - not Gradio)
   - **Visibility**: Public
4. Click **"Create Space"**

### Step 2: Clone Space Repository

```bash
git clone https://huggingface.co/spaces/YOUR_USERNAME/sql-investigation-env
cd sql-investigation-env
```

### Step 3: Copy Project Files

Copy all files from this project to the cloned directory:

```bash
# Copy all Python files
cp /path/to/sql-investigation-env/*.py .
cp /path/to/sql-investigation-env/requirements.txt .
cp /path/to/sql-investigation-env/Dockerfile .
cp /path/to/sql-investigation-env/.dockerignore .
cp /path/to/sql-investigation-env/README.md .

# Copy server directory
cp -r /path/to/sql-investigation-env/server ./

# Copy all other necessary directories
cp -r /path/to/sql-investigation-env/*.yaml .
```

### Step 4: Ensure Key Files Exist

The following files MUST be present:

```
Dockerfile          ← Container configuration
requirements.txt    ← Python dependencies
app.py             ← Root-level entry point
server/app.py      ← FastAPI application
server/static/     ← UI files (index.html)
db.py, grader.py, models.py, etc.
```

### Step 5: Push to Hugging Face

```bash
git add .
git commit -m "Initial deployment - SQL Evaluation Layer"
git push
```

### Step 6: Wait for Build

- Go to your Space on HF
- Wait 3-5 minutes for Docker build to complete
- Status changes from "Building" → "Running"

### Step 7: Access Your Space

Once running, your app will be available at:

```
https://huggingface.co/spaces/YOUR_USERNAME/sql-investigation-env
```

---

## 🧪 Testing Your Deployment

After deployment, test these features in the live UI:

### Test 1: Load Sample Query ✓
- Click **"Load Sample"** button
- Click **"Run Quick Test"**
- Expected: **Score: 1.0** (green)

### Test 2: Load Incorrect Query ✓
- Click **"Load Incorrect"** button
- Click **"Run Quick Test"**
- Expected: **Score: 0.0** (red)

### Test 3: Try Your Schema ✓
- Click **"Try Your Schema"** button
- Fields should clear with placeholders
- Paste your own SQL
- Click **"Run Quick Test"**

### Test 4: Select Task & Submit ✓
- Click any of the 3 tasks
- Enter a SQL query in the editor
- Click **"Submit Query"**
- Should show results

### Test 5: Run Grader ✓
- Enter a query
- Click **"Run Grader"**
- Should show score and feedback

### Test 6: Check Console ✓
- Open browser DevTools (F12)
- Check Console tab
- Should show no errors

---

## 📋 Project Structure

```
sql-investigation-env/
├── Dockerfile           # Container configuration
├── requirements.txt     # Python dependencies
├── app.py              # Root entry point
├── db.py               # Database manager
├── grader.py           # SQL grader logic
├── models.py           # Pydantic models
├── environment.py      # RL environment
├── tasks.py            # Task definitions
├── quick_test_local.py # Local test script
├── test_deployment.py  # Deployment test suite
├── server/
│   ├── app.py          # FastAPI app
│   └── static/
│       └── index.html  # Web UI
└── README.md           # This file
```

---

## 🔧 Troubleshooting

### Issue: Build fails with "port already in use"
**Solution**: Rebuild is automatic; wait 5 minutes

### Issue: UI doesn't load
**Solution**: 
- Check if `/static/index.html` is copied
- Verify `server/app.py` has StaticFiles mounting

### Issue: Quick Test returns errors
**Solution**:
- Verify `db.py` has `reset_with_schema()` method
- Verify `grader.py` has `evaluate_query()` function

### Issue: Grader returns invalid scores
**Solution**:
- Ensure all scores are between 0.01-0.99
- Check score clamping in `app.py`

---

## 📊 Performance Notes

- All tasks run in in-memory SQLite (fast)
- No database persistence needed
- Single container handles all users
- Auto-scaling available on HF Pro

---

## 🎯 Key Features

✅ **Dynamic Schema Testing**: Create custom tests  
✅ **3 Built-in Tasks**: Easy to Hard difficulty  
✅ **Query Evaluation**: Binary pass/fail grading  
✅ **Live Feedback**: Immediate results  
✅ **API + UI**: Both available  
✅ **Interactive Demo**: No setup required  

---

## 📝 API Endpoints

- `GET /health` - Health check
- `POST /reset` - Reset environment
- `POST /step` - Execute query
- `POST /grader` - Grade a query
- `POST /quick_test` - Test custom schema
- `GET /tasks` - List all tasks
- `POST /baseline` - Benchmark all tasks
- `GET /` - Serve UI

---

## ✨ UI Features

### Quick Schema Test Section
- **Load Sample**: Pre-filled correct query
- **Load Incorrect**: Shows failing query  
- **Try Your Schema**: Clear fields for custom testing
- **Run Quick Test**: Validate instantly

### Task Section
- 3 tasks (Easy, Medium, Hard)
- Click to select and load
- See schema and business question
- Submit SQL queries
- Get feedback and scores

---

## 📞 Support

For issues or questions:
1. Check test output: `python test_deployment.py`
2. Review API logs in HF Space
3. Verify all files are copied correctly

---

**Ready to deploy? Follow steps 1-7 above!** 🚀
