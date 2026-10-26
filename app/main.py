"""
Main FastAPI application.
Initializes app, middleware, routes, and exception handlers.
"""

from fastapi import FastAPI, Request, Response, status
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError
from app.config import settings
from app.api.v1 import api_router
from app.core.exceptions import AppException
from app.database import engine, AsyncSessionLocal
from app.services.admin_bootstrap import run_admin_startup
import logging
import time
from contextlib import asynccontextmanager

# Configure logging
logging.basicConfig(
    level=logging.INFO if settings.DEBUG else logging.WARNING,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("app.log") if not settings.DEBUG else logging.NullHandler()
    ]
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan events.
    Handles startup and shutdown.
    """
    # Startup
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Debug mode: {settings.DEBUG}")

    if settings.ENVIRONMENT != "test":
        async with AsyncSessionLocal() as session:
            try:
                await run_admin_startup(session)
                await session.commit()
            except Exception:
                await session.rollback()
                logger.exception("Admin startup failed")
                raise

    yield
    
    # Shutdown
    logger.info("Shutting down application")
    await engine.dispose()


# Create FastAPI app with comprehensive documentation
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
<div style="text-align: center; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border-radius: 10px; margin-bottom: 30px;">
  <h1 style="margin: 0; font-size: 2.5em;">🚀 Task Management API</h1>
  <p style="margin: 10px 0; font-size: 1.2em;">A production-ready REST API for task and project management with JWT authentication, advanced filtering, and comprehensive features.</p>
  <p style="margin: 5px 0;"> 
    <a href="/redoc" style="color: white;">Alternative Docs</a> | 
    <a href="https://github.com/ravigupta97/task_management_api" style="color: white;">GitHub</a>
  </p>
</div>

## 📊 API Features

### ✅ Task Management
- **Full CRUD**: Create, Read, Update, Delete tasks
- **Statuses**: TODO, IN_PROGRESS, COMPLETED, ARCHIVED
- **Priorities**: LOW, MEDIUM, HIGH, URGENT
- **Due Dates**: Track deadlines and overdue tasks
- **Categories**: Organize tasks with custom categories

### 🔍 Advanced Filtering
- Filter by status, priority, category
- Date range filtering (due_date_from, due_date_to)
- Full-text search in title and description
- Combine multiple filters

### 📄 Pagination
- Default: 10 items per page
- Max: 100 items per page
- Response includes: total count, page number, total pages

### 🏷️ Categories
- Create custom categories with colors
- Unique category names per user
- View task count per category
- Color-code your tasks

### 👤 User Management
- View and update profile
- Change password securely
- Delete account (with cascade deletion of tasks)
- Email verification system

---

## 🔐 Authentication & Security

### How Authentication Works

This API uses **JWT (JSON Web Tokens)** for authentication:

1. **Access Token** (15 min expiry):
   - Include in `Authorization: Bearer <token>` header
   - Used for all API requests
   - Short-lived for security

2. **Refresh Token** (7 days expiry):
   - Used to get new access tokens
   - Longer-lived for convenience
   - Use `POST /api/v1/auth/refresh` endpoint

### Token Refresh Flow

When your access token expires:

1. Find `POST /api/v1/auth/refresh`
2. Click **"Try it out"**
3. Paste your `refresh_token`:
```json
   {
     "refresh_token": "your_refresh_token_here"
   }
```
4. Click **"Execute"**
5. Copy the new `access_token`
6. Click **🔓 Authorize** and update the token

### Password Reset Flow

1. **Request Reset**:
   - Use `POST /api/v1/auth/password-reset/request`
   - Enter your email
   - Receive reset token (in response for testing, via email in production)

2. **Confirm Reset**:
   - Use `POST /api/v1/auth/password-reset/confirm`
   - Paste the reset token and new password
   - Your password is now updated

---

## 📋 Quick Start Guide - Test in 5 Minutes

Follow these steps to test all features of this API:

### Step 1️⃣: Register a New User

1. Scroll down to **Authentication** section
2. Find `POST /api/v1/auth/register`
3. Click **"Try it out"**
4. Replace the example with your data:
```json
   {
     "email": "yourname@example.com",
     "username": "yourusername",
     "password": "securepass123",
     "full_name": "Your Full Name"
   }
```
5. Click **"Execute"**
6. ✅ **Success**: You'll see a `201` response with your user details and a `verification_token`

> 💡 **Note**: In production, you would receive the verification token via email. For testing, copy it from the response.

---

### Step 2️⃣: Verify Your Email (Optional but Recommended)

1. Find `POST /api/v1/auth/verify-email`
2. Click **"Try it out"**
3. Paste the `verification_token` you received from registration:
```json
   {
     "token": "paste_your_verification_token_here"
   }
```
4. Click **"Execute"**
5. ✅ **Success**: You'll see `"Email verified successfully"`

---

### Step 3️⃣: Login to Get Access Token

1. Find `POST /api/v1/auth/login`
2. Click **"Try it out"**
3. Enter your credentials:
```json
   {
     "username": "yourusername",
     "password": "securepass123"
   }
```
4. Click **"Execute"**
5. ✅ **Success**: Copy the **`access_token`** from the response (it looks like: `eyJhbGciOiJIUzI1NiIs...`)

---

### Step 4️⃣: Authorize Swagger UI

1. Click the **🔓 Authorize** button at the top right of this page
2. In the popup, paste your `access_token` in the **Value** field
3. Click **"Authorize"**
4. Click **"Close"**

> 🎉 **You're now authenticated!** All protected endpoints will now work. You'll see 🔒 icons become locked.

---

### Step 5️⃣: Create a Category

1. Scroll to **Categories** section
2. Find `POST /api/v1/categories/`
3. Click **"Try it out"**
4. Enter category data:
```json
   {
     "name": "Work",
     "color": "#FF5733"
   }
```
5. Click **"Execute"**
6. ✅ **Success**: Copy the `id` from the response (you'll need it for tasks)

---

### Step 6️⃣: Create Your First Task

1. Scroll to **Tasks** section
2. Find `POST /api/v1/tasks/`
3. Click **"Try it out"**
4. Enter task data:
```json
   {
     "title": "Complete API documentation",
     "description": "Write comprehensive docs for the API",
     "status": "TODO",
     "priority": "HIGH",
     "due_date": "2024-12-31T23:59:59",
     "category_id": "paste_category_id_here"
   }
```
5. Click **"Execute"**
6. ✅ **Success**: Your first task is created!

---

### Step 7️⃣: Get All Your Tasks

1. Find `GET /api/v1/tasks/`
2. Click **"Try it out"**
3. Click **"Execute"** (no input needed)
4. ✅ **Success**: You'll see all your tasks with pagination info

---

### Step 8️⃣: Try Advanced Features

**🔍 Filter Tasks:**
1. In `GET /api/v1/tasks/`, try these parameters:
   - `status`: `TODO`
   - `priority`: `HIGH`
   - `limit`: `10`
2. Click **"Execute"**

**🔎 Search Tasks:**
1. In `GET /api/v1/tasks/`, use:
   - `search`: `documentation`
2. Click **"Execute"**

**📊 Get Statistics:**
1. Find `GET /api/v1/tasks/statistics`
2. Click **"Try it out"** → **"Execute"**
3. See your task breakdown by status

**✏️ Update a Task:**
1. Find `PUT /api/v1/tasks/{task_id}`
2. Enter your task ID (from Step 6)
3. Update fields:
```json
   {
     "status": "IN_PROGRESS",
     "priority": "URGENT"
   }
```
4. Click **"Execute"**

**🗑️ Delete a Task:**
1. Find `DELETE /api/v1/tasks/{task_id}`
2. Enter a task ID
3. Click **"Execute"**

---

## 📋 Response Format

### Success Response
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "title": "Complete API documentation",
  "status": "TODO",
  "created_at": "2024-02-14T10:00:00",
  ...
}
```

### Paginated Response
```json
{
  "items": [...],
  "total": 45,
  "page": 1,
  "page_size": 10,
  "total_pages": 5
}
```

### Error Response
```json
{
  "detail": "Error description",
  "errors": {
    "field": "Specific error message"
  }
}
```

## 💡 Pro Tips

### 1. Use Task Filters Efficiently
Combine multiple filters for precise results:
```
GET /api/v1/tasks/?status=TODO&priority=HIGH&category_id=xxx&limit=20
```

### 2. Search Across Tasks
Search works on both title and description:
```
GET /api/v1/tasks/?search=meeting
```

### 3. Track Overdue Tasks
Get all overdue tasks instantly:
```
GET /api/v1/tasks/overdue
```

### 4. Monitor Your Progress
Check task statistics:
```
GET /api/v1/tasks/statistics
```

### 5. Quick Status Updates
Use PATCH endpoints for faster updates:
```
PATCH /api/v1/tasks/{task_id}/status?new_status=COMPLETED
PATCH /api/v1/tasks/{task_id}/priority?new_priority=URGENT
```
---

## 🔧 Testing Different Scenarios

### Test 1: Create Multiple Tasks
Create 5-10 tasks with different:
- Statuses (TODO, IN_PROGRESS, COMPLETED)
- Priorities (LOW, MEDIUM, HIGH, URGENT)
- Categories (Work, Personal, Urgent)

### Test 2: Filter and Search
Try filtering by:
- Status only
- Priority only
- Category only
- Combination of all three
- Search term

### Test 3: Pagination
1. Create 25+ tasks
2. Use `GET /api/v1/tasks/?limit=10&skip=0` (page 1)
3. Then `skip=10` (page 2), `skip=20` (page 3)

### Test 4: Date Filtering
Create tasks with different due dates, then filter:
```
GET /api/v1/tasks/?due_date_from=2024-01-01&due_date_to=2024-12-31
```

### Test 5: Category Management
1. Create category "Work"
2. Assign tasks to it
3. View category stats
4. Delete category (tasks remain but category_id becomes null)

---

## 📖 Additional Resources

- **Health Check**: `GET /health` - Check API and database status
- **Metrics**: `GET /metrics` - View API performance metrics
- **Alternative Docs**: Visit `/redoc` for a different documentation interface

---

    """,
    docs_url="/docs",
    redoc_url=None,
    openapi_url="/openapi.json",
    lifespan=lifespan,
    responses={
        200: {
            "description": "Successful Response",
            "content": {
                "application/json": {
                    "example": {"message": "Operation successful"}
                }
            }
        },
        400: {
            "description": "Bad Request - Invalid input data"
        },
        401: {
            "description": "Unauthorized - Missing or invalid authentication token"
        },
        403: {
            "description": "Forbidden - Insufficient permissions"
        },
        404: {
            "description": "Not Found - Resource doesn't exist"
        },
        409: {
            "description": "Conflict - Resource already exists"
        },
        422: {
            "description": "Validation Error - Invalid request data",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Validation error",
                        "errors": [
                            {
                                "field": "email",
                                "message": "Invalid email format",
                                "type": "value_error"
                            }
                        ]
                    }
                }
            }
        },
        500: {
            "description": "Internal Server Error"
        },
        503: {
            "description": "Service Unavailable"
        }
    },
    contact={
        "name": "API Support",
        "email": "support@taskmanagement.com",
        "url": "https://github.com/ravigupta97/task_management_api"
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT"
    },
    swagger_ui_parameters={
        "syntaxHighlight.theme": "monokai",
        "tryItOutEnabled": True,
        "filter": True,
        "displayRequestDuration": True,
        "docExpansion": "none",  # Collapsed by default
        "defaultModelsExpandDepth": 2,
        "defaultModelExpandDepth": 2,
        "persistAuthorization": True  # Remember authorization between page refreshes
    }
)

# Custom OpenAPI schema to improve security documentation
def custom_openapi():
    """
    Customize OpenAPI schema to add better security descriptions.
    """
    if app.openapi_schema:
        return app.openapi_schema
    
    from fastapi.openapi.utils import get_openapi
    
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    
    # Enhanced security scheme with clear instructions
    openapi_schema["components"]["securitySchemes"] = {
        "HTTPBearer": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": (
                "JWT Authorization header using the Bearer scheme.\n\n"
                "**How to authorize:**\n"
                "1. Login via `/api/v1/auth/login` endpoint\n"
                "2. Copy the `access_token` from the response\n"
                "3. Paste it in the input field below (without 'Bearer' prefix)\n"
                "4. Click 'Authorize'\n\n"
                "Example token: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            )
        }
    }
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi


@app.get("/redoc", include_in_schema=False)
async def custom_redoc():
    """
    Custom ReDoc documentation endpoint.
    Returns HTML page with ReDoc embedded.
    """
    return HTMLResponse(
        content=f"""
        <!DOCTYPE html>
        <html>
          <head>
            <title>{settings.APP_NAME} - API Documentation</title>
            <meta charset="utf-8"/>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <link href="https://fonts.googleapis.com/css?family=Montserrat:300,400,700|Roboto:300,400,700" rel="stylesheet">
            <style>
              body {{
                margin: 0;
                padding: 0;
              }}
            </style>
          </head>
          <body>
            <redoc spec-url="/openapi.json"></redoc>
            <script src="https://cdn.jsdelivr.net/npm/redoc@latest/bundles/redoc.standalone.js"></script>
          </body>
        </html>
        """,
        status_code=200,
    )

# Custom exception handlers
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    """Handle custom application exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.message,
            "errors": exc.details
        }
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle Pydantic validation errors."""
    errors = []
    for error in exc.errors():
        errors.append({
            "field": " -> ".join(str(x) for x in error["loc"]),
            "message": error["msg"],
            "type": error["type"]
        })
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "Validation error",
            "errors": errors
        }
    )


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    """Handle database errors."""
    logger.error(f"Database error: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Database error occurred",
            "errors": {}
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected errors."""
    logger.error(f"Unexpected error: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Internal server error",
            "errors": {}
        }
    )

# CORS middleware (must be added BEFORE other middleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request logging and monitoring middleware
@app.middleware("http")
async def log_and_monitor_requests(request: Request, call_next):
    """
    Log all incoming requests, track performance, and add timing headers.
    """
    from app.core.monitoring import performance_monitor
    
    start_time = time.time()
    
    # Log request
    logger.info(f"Request: {request.method} {request.url.path}")
    
    try:
        # Process request
        response = await call_next(request)
        
        # Calculate processing time
        process_time = time.time() - start_time
        
        # Record metrics
        performance_monitor.record_request(
            endpoint=f"{request.method} {request.url.path}",
            duration=process_time,
            status_code=response.status_code
        )
        
        # Add headers
        response.headers["X-Process-Time"] = str(process_time)
        
        # Log response
        logger.info(
            f"Response: {request.method} {request.url.path} - "
            f"Status: {response.status_code} - "
            f"Time: {process_time:.4f}s"
        )
        
        # Warn on slow requests (> 1 second)
        if process_time > 1.0:
            logger.warning(
                f"Slow request detected: {request.method} {request.url.path} "
                f"took {process_time:.4f}s"
            )
        
        return response
    
    except Exception as e:
        process_time = time.time() - start_time
        logger.error(f"Error processing request: {str(e)}")
        
        # Record error
        performance_monitor.record_request(
            endpoint=f"{request.method} {request.url.path}",
            duration=process_time,
            status_code=500
        )
        
        raise

# Include API router
app.include_router(api_router, prefix="/api/v1")


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check(request: Request, response: Response,):
    """
    Health check endpoint with database connectivity test.
    Returns API status, version, and database status.
    """
    from sqlalchemy import text
    
    db_status = "healthy"
    try:
        # Test database connection
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"
        logger.error(f"Database health check failed: {str(e)}")
    
    return {
        "status": "healthy" if db_status == "healthy" else "degraded",
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "database": db_status
    }

# Metrics endpoint for monitoring
@app.get("/metrics", tags=["Monitoring"])
async def get_metrics(request: Request, response: Response,):
    """
    Get API performance metrics.
    
    Returns:
    - Uptime
    - Total requests processed
    - Total errors
    - Top 10 slowest endpoints with stats
    """
    from app.core.monitoring import performance_monitor
    
    stats = performance_monitor.get_stats()
    
    return {
        "uptime": f"{stats['uptime_seconds']:.2f} seconds",
        "total_requests": stats["total_requests"],
        "total_errors": stats["total_errors"],
        "slowest_endpoints": stats["endpoints"]
    }


# Reset metrics endpoint (admin only - in production, add authentication)
@app.post("/metrics/reset", tags=["Monitoring"])
async def reset_metrics(request: Request, response: Response,):
    """
    Reset performance metrics.
    
    ⚠️ In production, this should require admin authentication.
    """
    from app.core.monitoring import performance_monitor
    
    performance_monitor.reset()
    
    return {"message": "Metrics reset successfully"}


# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """
    Root endpoint with API information.
    """
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "health": "/health"
    }

