# KitaabSe API Documentation for Frontend

**Base URL:** `https://kiaatbse-backend.onrender.com`

**Last Updated:** November 4, 2025

---

## Table of Contents

1. [Authentication Flow](#authentication-flow)
2. [User APIs](#user-apis)
3. [Book Management APIs](#book-management-apis)
4. [Progress Tracking APIs](#progress-tracking-apis)
5. [Library Management APIs](#library-management-apis)
6. [Error Handling](#error-handling)
7. [Complete User Journey Examples](#complete-user-journey-examples)

---

## Authentication Flow

KitaabSe uses JWT (JSON Web Token) authentication with OTP verification.

### Flow Diagram:
```
1. User Signup → Receive OTP via email
2. Verify OTP + Set Password → Get JWT token
3. Login → Receive JWT token
4. Use Token in all authenticated requests
```

### Authentication Header Format:
```
Authorization: Bearer <token>
```

### APIs that DON'T require authentication:
- POST /api/users/signup/
- POST /api/users/verify/
- POST /api/users/login/

### APIs that REQUIRE authentication:
- All other endpoints require `Authorization: Bearer <token>` header

---

## User APIs

### 1. User Signup

**Endpoint:** `POST /api/users/signup/`

**Full URL:** `https://kiaatbse-backend.onrender.com/api/users/signup/`

**Description:** Register a new user account. An OTP will be sent to the provided email address for verification.

**Authentication:** ❌ Not required

**Request Body:**
```json
{
  "name": "John Doe",
  "email": "user@example.com"
}
```

**Request Fields:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| name | string | Yes | User's full name (2-100 characters) |
| email | string | Yes | Valid email address |

**Success Response (201 Created):**
```json
{
  "data": {
    "email": "user@example.com",
    "message": "OTP sent successfully"
  },
  "status": "PASS",
  "http_code": 201,
  "message": "User registered successfully. Please verify OTP sent to your email."
}
```

**Error Response (400 Bad Request):**
```json
{
  "data": null,
  "status": "FAIL",
  "http_code": 400,
  "message": "User already exists. Please login.",
  "errors": {}
}
```

**Notes:**
- Generates a 6-digit OTP and sends it to user's email
- User must verify OTP before they can login
- Check spam folder if email not received
- OTP expires in 10 minutes

**Next Step:** Call `/api/users/verify/` with the OTP received via email

---

### 2. Verify OTP

**Endpoint:** `POST /api/users/verify/`

**Full URL:** `https://kiaatbse-backend.onrender.com/api/users/verify/`

**Description:** Verify the OTP sent to user's email during signup and set password. Upon successful verification, the user account is activated and a JWT token is returned.

**Authentication:** ❌ Not required

**Request Body:**
```json
{
  "email": "user@example.com",
  "otp": "123456",
  "password": "securepassword123"
}
```

**Request Fields:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| email | string | Yes | User's email address |
| otp | string | Yes | 6-digit OTP received via email |
| password | string | Yes | User's password (8+ characters) |

**Success Response (200 OK):**
```json
{
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "user": {
      "id": 1,
      "name": "John Doe",
      "email": "user@example.com"
    }
  },
  "status": "PASS",
  "http_code": 200,
  "message": "User verified successfully. You can now login."
}
```

**Error Responses:**

*User Not Found (404 Not Found):*
```json
{
  "data": null,
  "status": "FAIL",
  "http_code": 404,
  "message": "User not found. Please signup first.",
  "errors": {}
}
```

*Already Verified (400 Bad Request):*
```json
{
  "data": null,
  "status": "FAIL",
  "http_code": 400,
  "message": "User already verified. Please login.",
  "errors": {}
}
```

*Invalid OTP (400 Bad Request):*
```json
{
  "data": null,
  "status": "FAIL",
  "http_code": 400,
  "message": "Invalid OTP. Please check and try again.",
  "errors": {}
}
```

*Expired OTP (400 Bad Request):*
```json
{
  "data": null,
  "status": "FAIL",
  "http_code": 400,
  "message": "OTP has expired. Please request a new one.",
  "errors": {}
}
```

**Notes:**
- Password is set during OTP verification
- JWT token is returned for immediate authentication
- OTP is cleared after successful verification
- Token expires in 30 days

**Next Step:** Store the token and use it for authenticated requests. You can also proceed to login with email/password.

---

### 3. User Login

**Endpoint:** `POST /api/users/login/`

**Full URL:** `https://kiaatbse-backend.onrender.com/api/users/login/`

**Description:** Authenticate user and receive JWT token. This token is required for all authenticated endpoints.

**Authentication:** ❌ Not required

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "securepassword123"
}
```

**Request Fields:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| email | string | Yes | User's email address |
| password | string | Yes | User's password |

**Success Response (200 OK):**
```json
{
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "user": {
      "id": 1,
      "name": "John Doe",
      "email": "user@example.com"
    }
  },
  "status": "PASS",
  "http_code": 200,
  "message": "Login successful"
}
```

**Response Fields:**
| Field | Type | Description |
|-------|------|-------------|
| token | string | JWT authentication token (expires in 30 days) |
| user.id | integer | User's unique ID |
| user.name | string | User's full name |
| user.email | string | User's email address |

**Error Responses:**

*User Not Found (404 Not Found):*
```json
{
  "data": null,
  "status": "FAIL",
  "http_code": 404,
  "message": "User not found. Please signup first.",
  "errors": {}
}
```

*User Not Verified (401 Unauthorized):*
```json
{
  "data": null,
  "status": "FAIL",
  "http_code": 401,
  "message": "User not verified. Please verify OTP first.",
  "errors": {}
}
```

*Invalid Password (401 Unauthorized):*
```json
{
  "data": null,
  "status": "FAIL",
  "http_code": 401,
  "message": "Invalid password. Please try again.",
  "errors": {}
}
```

**Notes:**
- User must be verified before they can login
- Returns JWT token valid for 30 days
- Token should be included in Authorization header for protected routes

**Next Step:** Store the token and use it in Authorization header: `Bearer <token>`

---

## Book Management APIs

### 4. Upload Book

**Endpoint:** `POST /api/books/upload/`

**Full URL:** `https://kiaatbse-backend.onrender.com/api/books/upload/`

**Description:** Upload a PDF book for audio conversion. The PDF will be processed using OCR to extract text (supports Hindi + English), then converted to audio using edge-tts. This is an asynchronous process - the API returns immediately and processing happens in the background.

**Authentication:** ✅ Required

**Headers:**
```
Authorization: Bearer <token>
Content-Type: multipart/form-data
```

**Request Body (multipart/form-data):**
```
title: "Premchand Ki Kahaniya"
author: "Munshi Premchand"
description: "Collection of famous Hindi stories"
language: "hindi"
genre: "literature"
pdf_file: <PDF file upload>
cover_image: <Image file upload> (optional)
is_public: true
```

**Request Fields:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| title | string | Yes | Book title (max 300 chars) |
| author | string | No | Author name (max 200 chars) |
| description | text | No | Book description |
| language | string | Yes | Book language (hindi, english, urdu, bengali, tamil, etc.) |
| genre | string | No | Book genre (literature, fiction, non_fiction, poetry, etc.) |
| pdf_file | file | Yes | PDF file (max 50MB) |
| cover_image | file | No | Book cover image (JPG/PNG, max 5MB) |
| is_public | boolean | No | Make book public (default: true) |

**Success Response (201 Created):**
```json
{
  "data": {
    "id": 1,
    "title": "Premchand Ki Kahaniya",
    "total_pages": 120,
    "processing_status": "processing",
    "message": "Book uploaded and text extracted. Audio generation started."
  },
  "status": "PASS",
  "http_code": 201,
  "message": "Book uploaded successfully. Processing 120 pages..."
}
```

**Processing Status Values:**
- `uploaded` - Book uploaded, not yet started processing
- `processing` - Currently extracting text and generating audio
- `completed` - All pages processed successfully
- `failed` - Processing failed
- `partial` - Some pages processed successfully

**Error Responses:**

*Unauthorized (401):*
```json
{
  "data": null,
  "status": "FAIL",
  "http_code": 401,
  "message": "Authentication required",
  "errors": {}
}
```

*Validation Error (400):*
```json
{
  "data": null,
  "status": "FAIL",
  "http_code": 400,
  "message": "Invalid input data",
  "errors": {
    "pdf_file": ["This field is required"],
    "title": ["This field is required"]
  }
}
```

*PDF Processing Failed (400):*
```json
{
  "data": null,
  "status": "FAIL",
  "http_code": 400,
  "message": "Failed to process PDF: Invalid PDF format",
  "errors": {}
}
```

**Notes:**
- PDF max size: 50MB
- Cover image max size: 5MB
- Text extraction uses OCR for better Hindi text extraction
- Audio generation happens in background using Celery tasks
- Each page is processed separately and audio is generated individually

**Next Steps:**
1. Poll `/api/books/<book_id>/` to check processing progress
2. When `processing_status` is `completed`, call `/api/books/<book_id>/pages/` to get audio files

---

### 5. Get All Books (Public Library)

**Endpoint:** `GET /api/books/books/`

**Full URL:** `https://kiaatbse-backend.onrender.com/api/books/books/`

**Description:** Get a list of all public books with pagination, filtering, and search capabilities.

**Authentication:** ❌ Not required (public endpoint)

**Headers:** None required

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| page | integer | No | Page number (default: 1) |
| search | string | No | Search in title, author, description |
| language | string | No | Filter by language (hindi, english, etc.) |
| genre | string | No | Filter by genre (literature, fiction, etc.) |
| status | string | No | Filter by processing_status (completed, processing, etc.) |

**Example Requests:**
```
GET /api/books/books/
GET /api/books/books/?page=2
GET /api/books/books/?search=premchand
GET /api/books/books/?language=hindi&status=completed
```

**Success Response (200 OK):**
```json
{
  "data": {
    "count": 150,
    "next": "https://kiaatbse-backend.onrender.com/api/books/books/?page=2",
    "previous": null,
    "results": [
      {
        "id": 1,
        "title": "Premchand Ki Kahaniya",
        "author": "Munshi Premchand",
        "description": "Collection of famous Hindi stories",
        "language": "hindi",
        "genre": "literature",
        "cover_image": "https://res.cloudinary.com/.../covers/book_1.jpg",
        "total_pages": 120,
        "processing_status": "completed",
        "is_public": true,
        "listen_count": 1523,
        "uploader": {
          "id": 1,
          "name": "John Doe"
        },
        "uploaded_at": "2025-11-02T12:00:00Z"
      }
    ]
  },
  "status": "PASS",
  "http_code": 200,
  "message": "Books retrieved successfully"
}
```

**Notes:**
- Returns only public and active books
- Paginated (20 books per page)
- Ordered by latest first
- No authentication required

---

### 6. Get My Uploaded Books

**Endpoint:** `GET /api/books/my/`

**Full URL:** `https://kiaatbse-backend.onrender.com/api/books/my/`

**Description:** Get all books uploaded by the authenticated user, including private books.

**Authentication:** ✅ Required

**Headers:**
```
Authorization: Bearer <token>
```

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| status | string | No | Filter by processing_status (completed, processing, failed) |

**Success Response (200 OK):**
```json
{
  "data": [
    {
      "id": 1,
      "title": "My Book",
      "author": "Author Name",
      "language": "hindi",
      "genre": "literature",
      "cover_image": "https://res.cloudinary.com/.../covers/book_1.jpg",
      "total_pages": 120,
      "processing_status": "completed",
      "processing_progress": 100,
      "is_public": true,
      "listen_count": 50,
      "uploaded_at": "2025-11-02T12:00:00Z"
    }
  ],
  "status": "PASS",
  "http_code": 200,
  "message": "Your books retrieved successfully"
}
```

**Error Response (401 Unauthorized):**
```json
{
  "data": null,
  "status": "FAIL",
  "http_code": 401,
  "message": "Authentication required",
  "errors": {}
}
```

---

### 7. Get Book Details

**Endpoint:** `GET /api/books/<book_id>/`

**Full URL:** `https://kiaatbse-backend.onrender.com/api/books/1/`

**Description:** Get detailed information about a specific book, including processing status and user's progress.

**Authentication:** ✅ Required for private books, ❌ Optional for public books

**Headers:**
```
Authorization: Bearer <token>  (required for private books)
```

**Path Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| book_id | integer | Yes | Book ID |

**Success Response (200 OK):**
```json
{
  "data": {
    "id": 1,
    "title": "Premchand Ki Kahaniya",
    "author": "Munshi Premchand",
    "description": "Collection of famous Hindi stories",
    "language": "hindi",
    "genre": "literature",
    "pdf_url": "https://res.cloudinary.com/.../pdfs/book_1.pdf",
    "cover_image": "https://res.cloudinary.com/.../covers/book_1.jpg",
    "total_pages": 120,
    "pages_count": 120,
    "processing_status": "completed",
    "processing_progress": 100,
    "is_public": true,
    "listen_count": 1523,
    "uploader": {
      "id": 1,
      "name": "John Doe",
      "email": "john@example.com"
    },
    "uploaded_at": "2025-11-02T12:00:00Z",
    "user_progress": {
      "current_page": 15,
      "completion_percentage": 12
    }
  },
  "status": "PASS",
  "http_code": 200,
  "message": "Book details retrieved successfully"
}
```

**Error Responses:**

*Book Not Found (404):*
```json
{
  "data": null,
  "status": "FAIL",
  "http_code": 404,
  "message": "Book not found",
  "errors": {}
}
```

*Private Book - Access Denied (403):*
```json
{
  "data": null,
  "status": "FAIL",
  "http_code": 403,
  "message": "This book is private",
  "errors": {}
}
```

---

### 8. Update Book

**Endpoint:** `PATCH /api/books/<book_id>/`

**Full URL:** `https://kiaatbse-backend.onrender.com/api/books/1/`

**Description:** Update book information. Only the book uploader can update the book.

**Authentication:** ✅ Required (must be book uploader)

**Headers:**
```
Authorization: Bearer <token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "title": "Updated Title",
  "author": "Updated Author",
  "description": "Updated description",
  "genre": "fiction",
  "is_public": false
}
```

**Allowed Fields:**
- title
- author
- description
- genre
- is_public

**Success Response (200 OK):**
```json
{
  "data": {
    "id": 1,
    "title": "Updated Title",
    "author": "Updated Author",
    "description": "Updated description",
    "genre": "fiction",
    "is_public": false
  },
  "status": "PASS",
  "http_code": 200,
  "message": "Book updated successfully"
}
```

**Error Responses:**

*Not Book Uploader (403):*
```json
{
  "data": null,
  "status": "FAIL",
  "http_code": 403,
  "message": "You can only update your own books",
  "errors": {}
}
```

---

### 9. Delete Book

**Endpoint:** `DELETE /api/books/<book_id>/`

**Full URL:** `https://kiaatbse-backend.onrender.com/api/books/1/`

**Description:** Delete a book (soft delete - marks as inactive). Only the book uploader can delete the book.

**Authentication:** ✅ Required (must be book uploader)

**Headers:**
```
Authorization: Bearer <token>
```

**Success Response (200 OK):**
```json
{
  "data": {
    "id": 1
  },
  "status": "PASS",
  "http_code": 200,
  "message": "Book deleted successfully"
}
```

**Error Responses:**

*Not Book Uploader (403):*
```json
{
  "data": null,
  "status": "FAIL",
  "http_code": 403,
  "message": "You can only delete your own books",
  "errors": {}
}
```

**Notes:**
- This is a soft delete - book is marked as inactive, not permanently deleted
- All associated data (pages, audio) remains but book becomes inaccessible

---

### 10. Get Book Pages with Audio

**Endpoint:** `GET /api/books/<book_id>/pages/`

**Full URL:** `https://kiaatbse-backend.onrender.com/api/books/1/pages/`

**Description:** Get all pages of a book with their audio files, text content, and metadata. Use this to get audio URLs for playback.

**Authentication:** ✅ Required for private books, ❌ Optional for public books

**Headers:**
```
Authorization: Bearer <token>  (required for private books)
```

**Path Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| book_id | integer | Yes | Book ID |

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| page | integer | No | Page number for pagination (optional) |

**Success Response (200 OK):**
```json
{
  "data": {
    "book": {
      "id": 1,
      "title": "Premchand Ki Kahaniya",
      "total_pages": 120,
      "processing_status": "completed"
    },
    "pages": [
      {
        "id": 1,
        "page_number": 1,
        "text_content": "पहला अध्याय\n\nयह कहानी एक छोटे से गाँव की है...",
        "audio_url": "https://res.cloudinary.com/.../audio/book_1/page_0001.mp3",
        "audio_duration": 290,
        "processing_status": "completed",
        "created_at": "2025-11-02T12:10:00Z"
      },
      {
        "id": 2,
        "page_number": 2,
        "text_content": "दूसरा अध्याय\n\nगाँव में एक बूढ़ा...",
        "audio_url": "https://res.cloudinary.com/.../audio/book_1/page_0002.mp3",
        "audio_duration": 315,
        "processing_status": "completed",
        "created_at": "2025-11-02T12:11:00Z"
      }
    ]
  },
  "status": "PASS",
  "http_code": 200,
  "message": "Book pages retrieved successfully"
}
```

**Notes:**
- Audio files are hosted on Cloudinary CDN
- Audio format: MP3
- `audio_duration` is in seconds
- Pages are ordered by page_number

---

## Progress Tracking APIs

### 11. Get User Progress for a Book

**Endpoint:** `GET /api/books/<book_id>/progress/`

**Full URL:** `https://kiaatbse-backend.onrender.com/api/books/1/progress/`

**Description:** Get current listening progress for a specific book.

**Authentication:** ✅ Required

**Headers:**
```
Authorization: Bearer <token>
```

**Success Response (200 OK):**
```json
{
  "data": {
    "current_page": 15,
    "current_position": 45,
    "completion_percentage": 12,
    "total_listened_time": 3600,
    "is_completed": false,
    "last_listened_at": "2025-11-02T14:30:00Z"
  },
  "status": "PASS",
  "http_code": 200,
  "message": "Progress retrieved successfully"
}
```

**Response Fields:**
| Field | Type | Description |
|-------|------|-------------|
| current_page | integer | Current page number (1-indexed) |
| current_position | integer | Position in seconds within the audio file |
| completion_percentage | integer | Overall completion percentage (0-100) |
| total_listened_time | integer | Total time listened in seconds |
| is_completed | boolean | Whether book is completed |
| last_listened_at | datetime | Last listening timestamp |

---

### 12. Update User Progress

**Endpoint:** `PUT /api/books/<book_id>/progress/`

**Full URL:** `https://kiaatbse-backend.onrender.com/api/books/1/progress/`

**Description:** Update user's listening progress for a book. Call this API when user finishes listening to a page or changes the current page.

**Authentication:** ✅ Required

**Headers:**
```
Authorization: Bearer <token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "page_number": 15,
  "position": 45,
  "listened_time": 290
}
```

**Request Fields:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| page_number | integer | Yes | Current page number (1-indexed) |
| position | integer | No | Position in seconds within the audio file (default: 0) |
| listened_time | integer | No | Time listened in this session in seconds |

**Success Response (200 OK):**
```json
{
  "data": {
    "current_page": 15,
    "current_position": 45,
    "completion_percentage": 12,
    "total_listened_time": 3890,
    "is_completed": false
  },
  "status": "PASS",
  "http_code": 200,
  "message": "Progress updated successfully"
}
```

**Error Responses:**

*Validation Error (400):*
```json
{
  "data": null,
  "status": "FAIL",
  "http_code": 400,
  "message": "Invalid input data",
  "errors": {
    "page_number": ["This field is required"]
  }
}
```

**Notes:**
- Automatically calculates completion percentage
- Increments book's listen count (only once per user)
- Updates last_listened_at timestamp
- Call this every 30 seconds or when user navigates to next page

---

### 13. Get All User Progress

**Endpoint:** `GET /api/books/progress/`

**Full URL:** `https://kiaatbse-backend.onrender.com/api/books/progress/`

**Description:** Get listening progress for all books the user has started listening to.

**Authentication:** ✅ Required

**Headers:**
```
Authorization: Bearer <token>
```

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| in_progress | boolean | No | Show only books in progress (true/false) |
| completed | boolean | No | Show only completed books (true/false) |

**Example Requests:**
```
GET /api/books/progress/
GET /api/books/progress/?in_progress=true
GET /api/books/progress/?completed=true
```

**Success Response (200 OK):**
```json
{
  "data": [
    {
      "id": 1,
      "book": {
        "id": 1,
        "title": "Premchand Ki Kahaniya",
        "author": "Munshi Premchand",
        "cover_image": "https://res.cloudinary.com/.../covers/book_1.jpg",
        "total_pages": 120
      },
      "current_page": 15,
      "current_position": 45,
      "completion_percentage": 12,
      "total_listened_time": 3600,
      "is_completed": false,
      "last_listened_at": "2025-11-02T14:30:00Z"
    }
  ],
  "status": "PASS",
  "http_code": 200,
  "message": "Progress retrieved successfully"
}
```

**Notes:**
- Ordered by last_listened_at (most recent first)
- Includes book details for easy display

---

## Library Management APIs

### 14. Get My Library

**Endpoint:** `GET /api/books/library/`

**Full URL:** `https://kiaatbse-backend.onrender.com/api/books/library/`

**Description:** Get all books in user's personal library (bookshelf).

**Authentication:** ✅ Required

**Headers:**
```
Authorization: Bearer <token>
```

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| favorites_only | boolean | No | Show only favorite books (true/false) |

**Example Requests:**
```
GET /api/books/library/
GET /api/books/library/?favorites_only=true
```

**Success Response (200 OK):**
```json
{
  "data": [
    {
      "id": 1,
      "book": {
        "id": 1,
        "title": "Premchand Ki Kahaniya",
        "author": "Munshi Premchand",
        "language": "hindi",
        "genre": "literature",
        "cover_image": "https://res.cloudinary.com/.../covers/book_1.jpg",
        "total_pages": 120,
        "processing_status": "completed"
      },
      "is_favorite": true,
      "added_at": "2025-11-01T08:00:00Z"
    }
  ],
  "status": "PASS",
  "http_code": 200,
  "message": "Library retrieved successfully"
}
```

**Notes:**
- Ordered by latest added first
- Includes full book details

---

### 15. Add Book to Library

**Endpoint:** `POST /api/books/library/add/`

**Full URL:** `https://kiaatbse-backend.onrender.com/api/books/library/add/`

**Description:** Add a book to user's personal library for easy access.

**Authentication:** ✅ Required

**Headers:**
```
Authorization: Bearer <token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "book_id": 1
}
```

**Success Response (201 Created):**
```json
{
  "data": {
    "message": "Book added to library"
  },
  "status": "PASS",
  "http_code": 201,
  "message": "Book added to library successfully"
}
```

**Error Responses:**

*Already in Library (400):*
```json
{
  "data": null,
  "status": "FAIL",
  "http_code": 400,
  "message": "Book already in library",
  "errors": {}
}
```

*Book ID Required (400):*
```json
{
  "data": null,
  "status": "FAIL",
  "http_code": 400,
  "message": "book_id is required",
  "errors": {
    "book_id": ["This field is required"]
  }
}
```

*Book Not Found (404):*
```json
{
  "data": null,
  "status": "FAIL",
  "http_code": 404,
  "message": "Book not found",
  "errors": {}
}
```

---

### 16. Remove Book from Library

**Endpoint:** `DELETE /api/books/library/<book_id>/`

**Full URL:** `https://kiaatbse-backend.onrender.com/api/books/library/1/`

**Description:** Remove a book from user's personal library.

**Authentication:** ✅ Required

**Headers:**
```
Authorization: Bearer <token>
```

**Path Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| book_id | integer | Yes | Book ID to remove |

**Success Response (200 OK):**
```json
{
  "data": {
    "message": "Book removed from library"
  },
  "status": "PASS",
  "http_code": 200,
  "message": "Book removed from library successfully"
}
```

**Error Responses:**

*Not in Library (404):*
```json
{
  "data": null,
  "status": "FAIL",
  "http_code": 404,
  "message": "Book not found in library",
  "errors": {}
}
```

---

### 17. Toggle Favorite Status

**Endpoint:** `POST /api/books/library/<book_id>/favorite/`

**Full URL:** `https://kiaatbse-backend.onrender.com/api/books/library/1/favorite/`

**Description:** Toggle favorite status for a book. If book is not in library, it will be added automatically.

**Authentication:** ✅ Required

**Headers:**
```
Authorization: Bearer <token>
```

**Path Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| book_id | integer | Yes | Book ID |

**Success Response (200 OK):**
```json
{
  "data": {
    "is_favorite": true,
    "message": "Book marked as favorite"
  },
  "status": "PASS",
  "http_code": 200,
  "message": "Favorite status updated successfully"
}
```

**Notes:**
- Automatically adds book to library if not already present
- Toggles between favorite and non-favorite status
- Response message changes based on current state:
  - "Book marked as favorite" when favorited
  - "Book removed from favorites" when unfavorited

---

## Error Handling

All API responses follow a consistent format.

### Standard Response Format:
```json
{
  "data": {},
  "status": "PASS" | "FAIL",
  "http_code": 200,
  "message": "Human readable message",
  "errors": {}
}
```

### Common HTTP Status Codes:

| Code | Meaning | When It Occurs |
|------|---------|----------------|
| 200 | OK | Request successful |
| 201 | Created | Resource created successfully |
| 400 | Bad Request | Invalid input data or validation error |
| 401 | Unauthorized | Missing or invalid authentication token |
| 403 | Forbidden | User doesn't have permission |
| 404 | Not Found | Resource doesn't exist |
| 500 | Internal Server Error | Server-side error |

### Authentication Errors:

**Missing Token (401):**
```json
{
  "data": null,
  "status": "FAIL",
  "http_code": 401,
  "message": "Authentication required",
  "errors": {}
}
```

**Invalid Token (401):**
```json
{
  "data": null,
  "status": "FAIL",
  "http_code": 401,
  "message": "Token is invalid or expired",
  "errors": {}
}
```

**Validation Errors (400):**
```json
{
  "data": null,
  "status": "FAIL",
  "http_code": 400,
  "message": "Invalid input data",
  "errors": {
    "email": ["This field is required"],
    "name": ["Ensure this field has at least 2 characters"]
  }
}
```

---

## Complete User Journey Examples

### Example 1: New User Registration and First Book Listen

```javascript
// Step 1: User Signup
const signupResponse = await fetch('https://kiaatbse-backend.onrender.com/api/users/signup/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    name: "Rahul Kumar",
    email: "rahul@example.com"
  })
});
// Response: { status: "PASS", message: "OTP sent to email" }

// Step 2: User checks email and enters OTP with password
const verifyResponse = await fetch('https://kiaatbse-backend.onrender.com/api/users/verify/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    email: "rahul@example.com",
    otp: "123456",
    password: "securepass123"
  })
});
// Response: {
//   data: {
//     token: "eyJhbGc...",
//     user: { id: 1, name: "Rahul Kumar", email: "rahul@example.com" }
//   }
// }
// Store token: localStorage.setItem('token', verifyResponse.data.token)

// Step 3: Browse books (no auth needed for public books)
const booksResponse = await fetch('https://kiaatbse-backend.onrender.com/api/books/books/?language=hindi');
// Response: List of Hindi books

// Step 4: User clicks on a book to see details
const bookResponse = await fetch('https://kiaatbse-backend.onrender.com/api/books/1/');
// Response: Full book details

// Step 5: Add book to library (requires auth)
const addResponse = await fetch('https://kiaatbse-backend.onrender.com/api/books/library/add/', {
  method: 'POST',
  headers: {
    'Authorization': 'Bearer ' + localStorage.getItem('token'),
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({ book_id: 1 })
});
// Response: { status: "PASS", message: "Added to library" }

// Step 6: Get book pages to start listening (requires auth for private books)
const pagesResponse = await fetch('https://kiaatbse-backend.onrender.com/api/books/1/pages/');
// Response: Array of pages with audio URLs

// Step 7: User starts listening to page 1
const audioPlayer = new Audio(pagesResponse.data.pages[0].audio_url);
audioPlayer.play();

// Step 8: Update progress (requires auth)
const progressResponse = await fetch('https://kiaatbse-backend.onrender.com/api/books/1/progress/', {
  method: 'PUT',
  headers: {
    'Authorization': 'Bearer ' + localStorage.getItem('token'),
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    page_number: 1,
    position: 290,
    listened_time: 290
  })
});
// Response: { status: "PASS", message: "Progress updated" }

// Step 9: Mark as favorite (requires auth)
const favoriteResponse = await fetch('https://kiaatbse-backend.onrender.com/api/books/library/1/favorite/', {
  method: 'POST',
  headers: {
    'Authorization': 'Bearer ' + localStorage.getItem('token')
  }
});
// Response: { data: { is_favorite: true } }
```

---

### Example 2: User Uploads a New Book

```javascript
// User is already logged in (has token)

// Create FormData for file upload
const formData = new FormData();
formData.append('title', 'Godan');
formData.append('author', 'Munshi Premchand');
formData.append('description', 'A classic Hindi novel');
formData.append('language', 'hindi');
formData.append('genre', 'literature');
formData.append('pdf_file', pdfFile); // File object from input
formData.append('cover_image', coverImage); // File object from input
formData.append('is_public', 'true');

// Upload book
const uploadResponse = await fetch('https://kiaatbse-backend.onrender.com/api/books/upload/', {
  method: 'POST',
  headers: {
    'Authorization': 'Bearer ' + localStorage.getItem('token')
  },
  body: formData
});
// Response: {
//   data: {
//     id: 2,
//     title: "Godan",
//     total_pages: 200,
//     processing_status: "processing"
//   }
// }

const bookId = uploadResponse.data.id;

// Poll for processing status (every 10 seconds)
const intervalId = setInterval(async () => {
  const statusResponse = await fetch(`https://kiaatbse-backend.onrender.com/api/books/${bookId}/`, {
    headers: {
      'Authorization': 'Bearer ' + localStorage.getItem('token')
    }
  });
  const data = await statusResponse.json();

  console.log('Processing:', data.data.processing_status);

  if (data.data.processing_status === 'completed') {
    console.log('Book processing completed!');
    clearInterval(intervalId);

    // Get pages with audio
    const pagesResponse = await fetch(`https://kiaatbse-backend.onrender.com/api/books/${bookId}/pages/`, {
      headers: {
        'Authorization': 'Bearer ' + localStorage.getItem('token')
      }
    });
    console.log('Audio files ready:', pagesResponse.data.pages);
  }
}, 10000);

// View my uploaded books
const myBooksResponse = await fetch('https://kiaatbse-backend.onrender.com/api/books/my/', {
  headers: {
    'Authorization': 'Bearer ' + localStorage.getItem('token')
  }
});
// Response: List of books uploaded by user
```

---

### Example 3: Resuming Listening from Last Position

```javascript
// User opens app, get their library
const libraryResponse = await fetch('https://kiaatbse-backend.onrender.com/api/books/library/', {
  headers: {
    'Authorization': 'Bearer ' + localStorage.getItem('token')
  }
});
// Response: List of books in library

// User selects a book they were listening to
const bookId = 1;

// Get current progress
const progressResponse = await fetch(`https://kiaatbse-backend.onrender.com/api/books/${bookId}/progress/`, {
  headers: {
    'Authorization': 'Bearer ' + localStorage.getItem('token')
  }
});
// Response: {
//   data: {
//     current_page: 15,
//     current_position: 45,
//     completion_percentage: 12
//   }
// }

const currentPage = progressResponse.data.current_page;
const currentPosition = progressResponse.data.current_position;

// Get book pages
const pagesResponse = await fetch(`https://kiaatbse-backend.onrender.com/api/books/${bookId}/pages/`, {
  headers: {
    'Authorization': 'Bearer ' + localStorage.getItem('token')
  }
});

// Find the current page (page_number is 1-indexed)
const currentPageData = pagesResponse.data.pages.find(p => p.page_number === currentPage);

// Resume playback from saved position
const audioPlayer = new Audio(currentPageData.audio_url);
audioPlayer.currentTime = currentPosition || 0;
audioPlayer.play();

// Update progress every 30 seconds
setInterval(async () => {
  await fetch(`https://kiaatbse-backend.onrender.com/api/books/${bookId}/progress/`, {
    method: 'PUT',
    headers: {
      'Authorization': 'Bearer ' + localStorage.getItem('token'),
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      page_number: currentPage,
      position: Math.floor(audioPlayer.currentTime),
      listened_time: 30
    })
  });
}, 30000);
```

---

## Important Notes for Frontend

### 1. Token Management:
- **Token expires after 30 days** - Store it in localStorage or sessionStorage
- Include token in all authenticated requests: `Authorization: Bearer <token>`
- Implement automatic re-login when you receive 401 errors

### 2. File Upload:
- Maximum PDF size: **50MB**
- Maximum cover image size: **5MB**
- Supported image formats: **JPG, PNG**
- Use `multipart/form-data` content type for file uploads

### 3. Polling for Processing Status:
- After uploading a book, poll `/api/books/<book_id>/` every **10-15 seconds**
- Check `processing_status` to show progress
- Stop polling when `processing_status` is `completed` or `failed`

### 4. Audio Playback:
- Audio files are hosted on Cloudinary CDN (fast, reliable)
- Audio format: **MP3**
- Use HTML5 `<audio>` element or any audio library
- Update progress every **30 seconds** or when user navigates to next page

### 5. Error Handling:
- Always check `response.data.status` field (`PASS` or `FAIL`)
- Display `response.data.message` to user for feedback
- Handle `401` errors by prompting user to login again
- Handle `404` errors by showing "Not Found" message

### 6. Search and Filters:
- Use query parameters for filtering books
- Implement debouncing for search input (wait 500ms after user stops typing)
- Store filter preferences in localStorage for better UX

### 7. Pagination:
- Default page size is 20 items
- Use `next` and `previous` URLs from response for navigation
- Show page numbers based on `count` field

---

## API Summary Table

| # | Endpoint | Method | Auth Required | Description |
|---|----------|--------|---------------|-------------|
| 1 | /api/users/signup/ | POST | ❌ No | Register new user |
| 2 | /api/users/verify/ | POST | ❌ No | Verify OTP and set password |
| 3 | /api/users/login/ | POST | ❌ No | Login and get token |
| 4 | /api/books/upload/ | POST | ✅ Yes | Upload book PDF |
| 5 | /api/books/books/ | GET | ❌ No | List all public books |
| 6 | /api/books/my/ | GET | ✅ Yes | List my uploaded books |
| 7 | /api/books/<id>/ | GET | ⚠️ For private | Get book details |
| 8 | /api/books/<id>/ | PATCH | ✅ Yes (uploader) | Update book |
| 9 | /api/books/<id>/ | DELETE | ✅ Yes (uploader) | Delete book |
| 10 | /api/books/<id>/pages/ | GET | ⚠️ For private | Get book pages with audio |
| 11 | /api/books/<id>/progress/ | GET | ✅ Yes | Get progress for book |
| 12 | /api/books/<id>/progress/ | PUT | ✅ Yes | Update progress |
| 13 | /api/books/progress/ | GET | ✅ Yes | Get all progress |
| 14 | /api/books/library/ | GET | ✅ Yes | Get my library |
| 15 | /api/books/library/add/ | POST | ✅ Yes | Add book to library |
| 16 | /api/books/library/<id>/ | DELETE | ✅ Yes | Remove from library |
| 17 | /api/books/library/<id>/favorite/ | POST | ✅ Yes | Toggle favorite |

---

## Testing the APIs

You can test these APIs using:

1. **Postman** - Import the endpoints and test with your tokens
2. **cURL** - Command line testing
3. **Browser DevTools** - For debugging AJAX requests

### Example cURL Commands:

```bash
# Signup
curl -X POST https://kiaatbse-backend.onrender.com/api/users/signup/ \
  -H "Content-Type: application/json" \
  -d '{"name":"Test User","email":"test@example.com"}'

# Verify OTP
curl -X POST https://kiaatbse-backend.onrender.com/api/users/verify/ \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","otp":"123456","password":"test123"}'

# Login
curl -X POST https://kiaatbse-backend.onrender.com/api/users/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test123"}'

# Get Books (with token)
curl -X GET https://kiaatbse-backend.onrender.com/api/books/books/ \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## Support

For any API issues or questions, contact the backend team.

**Backend Server:** https://kiaatbse-backend.onrender.com

**Admin Panel:** https://kiaatbse-backend.onrender.com/admin/

---

**End of Documentation**
