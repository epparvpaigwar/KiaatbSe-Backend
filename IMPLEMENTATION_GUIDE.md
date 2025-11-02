# 🚀 KitaabSe Implementation Guide

## ✅ What Has Been Implemented

### 1. **Security Fixes** ✅
- ✅ Password hashing with Django's `make_password()` and `check_password()`
- ✅ OTP expiration (10 minutes) with `otp_created_at` field
- ✅ CORS restriction (configurable via environment variable)

### 2. **Database Models** ✅
- ✅ Enhanced User model with password hashing methods
- ✅ Book model (title, author, language, genre, PDF, cover, stats)
- ✅ BookPage model (page number, text, audio, status)
- ✅ ListeningProgress model (track user progress)
- ✅ UserLibrary model (favorites and library management)

### 3. **Services** ✅
- ✅ PDFProcessor - Extract text page by page from PDFs
- ✅ TTSGenerator - Generate audio using Edge-TTS (Hindi + 7 languages)
- ✅ Cloudinary integration for file storage
- ✅ Celery + Redis for background jobs

### 4. **Background Tasks** ✅
- ✅ `process_book_pdf` - Extract PDF pages and create BookPage records
- ✅ `generate_page_audio` - Generate audio for each page
- ✅ `update_book_progress` - Track processing progress
- ✅ `cleanup_failed_books` - Cleanup stuck jobs
- ✅ `retry_failed_pages` - Retry failed audio generation

### 5. **Serializers** ✅
- ✅ BookListSerializer - For book listings
- ✅ BookDetailSerializer - For detailed book view
- ✅ BookUploadSerializer - For PDF upload
- ✅ BookPageSerializer - For page data
- ✅ ListeningProgressSerializer - For progress tracking
- ✅ UserLibrarySerializer - For library management

---

## 📋 Next Steps - What YOU Need to Do

### **STEP 1: Install Dependencies**

```bash
cd /Users/apple/Desktop/temp/KiaatbSe-Backend
pip install -r requirements.txt
```

### **STEP 2: Set Up Environment Variables**

Update your `.env` file with these new variables:

```bash
# Existing variables
SECRET_KEY=your-secret-key
DEBUG=True
DATABASE_URL=your-postgresql-url
SENDGRID_API_KEY=your-sendgrid-key
DEFAULT_FROM_EMAIL=paigwarparv9@gmail.com

# NEW - Cloudinary Configuration
CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_api_key
CLOUDINARY_API_SECRET=your_api_secret

# NEW - Redis Configuration
REDIS_URL=redis://localhost:6379/0  # Local development
# For Render: Use the Redis URL from Render dashboard

# NEW - CORS Configuration
CORS_ALLOW_ALL=False  # Set to True only for development
```

### **STEP 3: Get Cloudinary Credentials**

1. Go to: https://cloudinary.com/
2. Sign up for free account
3. Go to Dashboard
4. Copy:
   - Cloud Name
   - API Key
   - API Secret
5. Add to `.env` file

### **STEP 4: Set Up Redis (Local Development)**

**Option A: Using Docker**
```bash
docker run -d -p 6379:6379 redis:alpine
```

**Option B: Using Homebrew (Mac)**
```bash
brew install redis
brew services start redis
```

**Option C: For Render Production**
- Go to Render Dashboard
- Create new Redis instance (free tier)
- Copy Redis URL
- Add to environment variables

### **STEP 5: Create Migrations**

```bash
python manage.py makemigrations users
python manage.py makemigrations audiobooks
python manage.py migrate
```

### **STEP 6: Create Superuser (Optional)**

```bash
python manage.py createsuperuser
```

### **STEP 7: Test Services**

```bash
# Test PDF processing
python manage.py shell
>>> from audiobooks.services import PDFProcessor, TTSGenerator
>>> TTSGenerator.test_tts()  # Should print success

# Test Celery
celery -A backend worker --loglevel=info
```

---

## 🎯 **TODO: Create Views and URLs**

I'll provide you with the complete views.py and urls.py in the next message. Here's what needs to be created:

### **Views to Create:**
1. ✅ BookUploadView - Upload PDF and start processing
2. ✅ BookListView - List all public books
3. ✅ MyBooksView - List user's uploaded books
4. ✅ BookDetailView - Get book details
5. ✅ BookPagesView - Get all pages of a book
6. ✅ UpdateProgressView - Update listening progress
7. ✅ LibraryView - Manage user library
8. ✅ SearchBooksView - Search books

---

## 🔧 Running the Application

### **Development Mode:**

**Terminal 1 - Django Server:**
```bash
python manage.py runserver
```

**Terminal 2 - Celery Worker:**
```bash
celery -A backend worker --loglevel=info
```

**Terminal 3 - Celery Beat (Optional - for periodic tasks):**
```bash
celery -A backend beat --loglevel=info
```

### **Production Mode (Render):**

1. **Web Service** - Already configured
2. **Redis** - Create free Redis instance on Render
3. **Celery Worker** - Create new Background Worker on Render:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `celery -A backend worker --loglevel=info`

---

## 📊 Database Schema

```
Users
├── id
├── name
├── email
├── password (hashed)
├── is_verified
├── otp
├── otp_created_at  ← NEW
└── timestamps

Books
├── id
├── title, author, description
├── language, genre
├── pdf_file (Cloudinary)
├── cover_image (Cloudinary)
├── uploader_id → Users
├── total_pages
├── total_duration
├── processing_status
├── processing_progress
├── is_public
├── stats (listen_count, favorite_count)
└── timestamps

BookPages
├── id
├── book_id → Books
├── page_number
├── text_content
├── audio_file (Cloudinary)
├── audio_duration
├── processing_status
└── timestamps

ListeningProgress
├── id
├── user_id → Users
├── book_id → Books
├── current_page
├── current_position
├── total_listened_time
├── completion_percentage
├── is_completed
└── timestamps

UserLibrary
├── id
├── user_id → Users
├── book_id → Books
├── is_favorite
├── notes
└── timestamps
```

---

## 🎬 Complete Workflow

### **1. User Uploads Book**
```
POST /api/books/upload/
- User uploads PDF
- Book record created (status: uploaded)
- Celery task triggered: process_book_pdf
```

### **2. Background Processing**
```
process_book_pdf task:
1. Downloads PDF from Cloudinary
2. Extracts text page by page
3. Creates BookPage records
4. Triggers generate_page_audio for each page

generate_page_audio tasks (parallel):
1. Gets page text
2. Generates audio using Edge-TTS
3. Uploads audio to Cloudinary
4. Updates BookPage status
5. Updates Book processing_progress
```

### **3. User Listens to Book**
```
GET /api/books/<id>/pages/
- Returns all pages with audio URLs

PUT /api/books/<id>/progress/
- Updates current page and position
- Calculates completion percentage
```

---

## 🚀 API Endpoints (To Be Created)

```
Authentication:
POST   /api/users/signup/       ✅ Already done
POST   /api/users/verify/       ✅ Already done
POST   /api/users/login/        ✅ Already done

Books:
POST   /api/books/upload/       → Upload PDF
GET    /api/books/              → List public books
GET    /api/books/my/           → My uploaded books
GET    /api/books/<id>/         → Book details
GET    /api/books/<id>/pages/   → Get all pages
DELETE /api/books/<id>/         → Delete book
PATCH  /api/books/<id>/         → Update book info

Playback:
PUT    /api/books/<id>/progress/    → Update progress
GET    /api/books/<id>/progress/    → Get progress

Library:
GET    /api/library/                 → My library
POST   /api/library/add/             → Add to library
DELETE /api/library/<book_id>/       → Remove from library
POST   /api/library/<book_id>/favorite/  → Toggle favorite

Search:
GET    /api/books/search/?q=query&language=hindi&genre=literature
```

---

## ⚠️ Important Notes

1. **Cloudinary Free Tier Limits:**
   - 25GB storage
   - 25GB bandwidth/month
   - Sufficient for MVP

2. **Redis Free Tier (Render):**
   - 25MB storage
   - Sufficient for task queue

3. **Edge-TTS:**
   - Completely free
   - No API limits
   - High quality Hindi voices

4. **Processing Time:**
   - PDF extraction: ~1 sec per page
   - Audio generation: ~2-5 sec per page
   - 100-page book: ~10-15 minutes total

5. **File Size Limits:**
   - PDF: Max 50MB
   - Cover Image: Max 5MB

---

## 🐛 Troubleshooting

### **Celery not processing tasks:**
```bash
# Check Redis is running
redis-cli ping  # Should return PONG

# Check Celery worker is running
celery -A backend worker --loglevel=debug
```

### **Edge-TTS not working:**
```bash
# Test manually
python manage.py shell
>>> from audiobooks.services import TTSGenerator
>>> TTSGenerator.test_tts("यह एक परीक्षण है")
```

### **Cloudinary upload fails:**
- Check credentials in .env
- Check internet connection
- Check file size limits

---

## 📞 What's Next?

Let me know and I'll provide:
1. ✅ Complete views.py with all APIs
2. ✅ Complete urls.py configuration
3. ✅ Frontend integration examples
4. ✅ Deployment guide for Render

Type "continue" and I'll provide the views and URLs!
