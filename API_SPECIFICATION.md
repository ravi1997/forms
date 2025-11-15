# API Specification

## Authentication Endpoints

### Register User
- **Endpoint**: `POST /auth/register`
- **Description**: Register a new user account
- **Request Body**:
  ```json
  {
    "username": "string (required, 3-80 chars)",
    "email": "string (required, valid email)",
    "password": "string (required, min 8 chars)",
    "first_name": "string (optional)",
    "last_name": "string (optional)"
  }
  ```
- **Responses**:
  - `201 Created`: User successfully registered
  - `400 Bad Request`: Validation errors
  - `409 Conflict`: Username or email already exists

### Login User
- **Endpoint**: `POST /auth/login`
- **Description**: Authenticate user and return JWT tokens
- **Request Body**:
  ```json
  {
    "username": "string (required)",
    "password": "string (required)"
  }
  ```
- **Responses**:
  - `200 OK`: Authentication successful, returns tokens
  - `401 Unauthorized`: Invalid credentials

### Logout User
- **Endpoint**: `POST /auth/logout`
- **Description**: Invalidate user session
- **Headers**: `Authorization: Bearer <access_token>`
- **Responses**:
  - `200 OK`: Successfully logged out

### Refresh Token
- **Endpoint**: `POST /auth/refresh`
- **Description**: Get new access token using refresh token
- **Headers**: `Authorization: Bearer <refresh_token>`
- **Responses**:
  - `200 OK`: New access token returned

## User Management Endpoints

### Get Current User Profile
- **Endpoint**: `GET /api/users/profile`
- **Description**: Get current user's profile information
- **Headers**: `Authorization: Bearer <access_token>`
- **Responses**:
  - `200 OK`: User profile data
  - `401 Unauthorized`: Invalid or expired token

### Update User Profile
- **Endpoint**: `PUT /api/users/profile`
- **Description**: Update current user's profile information
- **Headers**: `Authorization: Bearer <access_token>`
- **Request Body**:
  ```json
  {
    "first_name": "string (optional)",
    "last_name": "string (optional)",
    "email": "string (optional, valid email)",
    "preferences": "object (optional)"
  }
  ```
- **Responses**:
  - `200 OK`: Profile updated successfully
  - `400 Bad Request`: Validation errors

## Form Management Endpoints

### Get All Forms
- **Endpoint**: `GET /api/forms`
- **Description**: Get all forms created by the current user
- **Headers**: `Authorization: Bearer <access_token>`
- **Query Parameters**:
  - `page` (optional): Page number for pagination
  - `limit` (optional): Number of forms per page (default 10)
  - `status` (optional): Filter by status (published, draft, archived)
- **Responses**:
  - `200 OK`: List of forms with pagination info
  - `401 Unauthorized`: Invalid or expired token

### Create Form
- **Endpoint**: `POST /api/forms`
- **Description**: Create a new form
- **Headers**: `Authorization: Bearer <access_token>`
- **Request Body**:
  ```json
  {
    "title": "string (required, max 200 chars)",
    "description": "string (optional)",
    "settings": {
      "expires_at": "ISO date string (optional)",
      "response_limit": "integer (optional)",
      "require_login": "boolean (optional)",
      "collect_ip": "boolean (optional)"
    }
  }
  ```
- **Responses**:
  - `201 Created`: Form created successfully
  - `400 Bad Request`: Validation errors
  - `401 Unauthorized`: Invalid or expired token

### Get Form Details
- **Endpoint**: `GET /api/forms/<form_id>`
- **Description**: Get detailed information about a specific form
- **Headers**: `Authorization: Bearer <access_token>`
- **Responses**:
  - `200 OK`: Form details
  - `401 Unauthorized`: Invalid or expired token
  - `403 Forbidden`: User doesn't have access to this form
  - `404 Not Found`: Form doesn't exist

### Update Form
- **Endpoint**: `PUT /api/forms/<form_id>`
- **Description**: Update form information
- **Headers**: `Authorization: Bearer <access_token>`
- **Request Body**: Same as create form
- **Responses**:
  - `200 OK`: Form updated successfully
  - `400 Bad Request`: Validation errors
  - `401 Unauthorized`: Invalid or expired token
  - `403 Forbidden`: User doesn't have permission to update this form
  - `404 Not Found`: Form doesn't exist

### Delete Form
- **Endpoint**: `DELETE /api/forms/<form_id>`
- **Description**: Delete a form
- **Headers**: `Authorization: Bearer <access_token>`
- **Responses**:
  - `204 No Content`: Form deleted successfully
  - `401 Unauthorized`: Invalid or expired token
  - `403 Forbidden`: User doesn't have permission to delete this form
  - `404 Not Found`: Form doesn't exist

### Publish Form
- **Endpoint**: `POST /api/forms/<form_id>/publish`
- **Description**: Publish a form to make it available for responses
- **Headers**: `Authorization: Bearer <access_token>`
- **Responses**:
  - `200 OK`: Form published successfully
  - `401 Unauthorized`: Invalid or expired token
  - `403 Forbidden`: User doesn't have permission to publish this form
  - `404 Not Found`: Form doesn't exist

### Unpublish Form
- **Endpoint**: `POST /api/forms/<form_id>/unpublish`
- **Description**: Unpublish a form to stop accepting responses
- **Headers**: `Authorization: Bearer <access_token>`
- **Responses**:
  - `200 OK`: Form unpublished successfully
  - `401 Unauthorized`: Invalid or expired token
  - `403 Forbidden`: User doesn't have permission to unpublish this form
  - `404 Not Found`: Form doesn't exist

## Form Building Endpoints

### Get Form Sections
- **Endpoint**: `GET /api/forms/<form_id>/sections`
- **Description**: Get all sections of a form
- **Headers**: `Authorization: Bearer <access_token>`
- **Responses**:
  - `200 OK`: List of sections
  - `401 Unauthorized`: Invalid or expired token
  - `403 Forbidden`: User doesn't have access to this form
  - `404 Not Found`: Form doesn't exist

### Create Section
- **Endpoint**: `POST /api/forms/<form_id>/sections`
- **Description**: Create a new section in a form
- **Headers**: `Authorization: Bearer <access_token>`
- **Request Body**:
  ```json
  {
    "title": "string (optional, max 200 chars)",
    "description": "string (optional)",
    "order": "integer (optional, default 0)"
  }
  ```
- **Responses**:
  - `201 Created`: Section created successfully
 - `400 Bad Request`: Validation errors
  - `401 Unauthorized`: Invalid or expired token
  - `403 Forbidden`: User doesn't have permission to modify this form
 - `404 Not Found`: Form doesn't exist

### Update Section
- **Endpoint**: `PUT /api/sections/<section_id>`
- **Description**: Update a section
- **Headers**: `Authorization: Bearer <access_token>`
- **Request Body**:
  ```json
  {
    "title": "string (optional)",
    "description": "string (optional)",
    "order": "integer (optional)"
  }
  ```
- **Responses**:
  - `200 OK`: Section updated successfully
 - `400 Bad Request`: Validation errors
  - `401 Unauthorized`: Invalid or expired token
  - `403 Forbidden`: User doesn't have permission to modify this section
  - `404 Not Found`: Section doesn't exist

### Delete Section
- **Endpoint**: `DELETE /api/sections/<section_id>`
- **Description**: Delete a section (and all its questions)
- **Headers**: `Authorization: Bearer <access_token>`
- **Responses**:
  - `204 No Content`: Section deleted successfully
 - `401 Unauthorized`: Invalid or expired token
  - `403 Forbidden`: User doesn't have permission to delete this section
  - `404 Not Found`: Section doesn't exist

### Get Section Questions
- **Endpoint**: `GET /api/sections/<section_id>/questions`
- **Description**: Get all questions in a section
- **Headers**: `Authorization: Bearer <access_token>`
- **Responses**:
  - `200 OK`: List of questions
  - `401 Unauthorized`: Invalid or expired token
  - `403 Forbidden`: User doesn't have access to this section
  - `404 Not Found`: Section doesn't exist

### Create Question
- **Endpoint**: `POST /api/sections/<section_id>/questions`
- **Description**: Create a new question in a section
- **Headers**: `Authorization: Bearer <access_token>`
- **Request Body**:
  ```json
  {
    "question_type": "enum (required: text, long_text, multiple_choice, checkbox, dropdown, rating, file_upload, date, email, number)",
    "question_text": "string (required)",
    "is_required": "boolean (optional, default false)",
    "order": "integer (optional, default 0)",
    "validation_rules": "object (optional)",
    "options": "array (optional, for multiple_choice, checkbox, dropdown)"
  }
  ```
- **Responses**:
  - `201 Created`: Question created successfully
  - `400 Bad Request`: Validation errors
  - `401 Unauthorized`: Invalid or expired token
  - `403 Forbidden`: User doesn't have permission to modify this section
  - `404 Not Found`: Section doesn't exist

### Update Question
- **Endpoint**: `PUT /api/questions/<question_id>`
- **Description**: Update a question
- **Headers**: `Authorization: Bearer <access_token>`
- **Request Body**: Same as create question
- **Responses**:
  - `200 OK`: Question updated successfully
  - `400 Bad Request`: Validation errors
  - `401 Unauthorized`: Invalid or expired token
  - `403 Forbidden`: User doesn't have permission to modify this question
  - `404 Not Found`: Question doesn't exist

### Delete Question
- **Endpoint**: `DELETE /api/questions/<question_id>`
- **Description**: Delete a question
- **Headers**: `Authorization: Bearer <access_token>`
- **Responses**:
  - `204 No Content`: Question deleted successfully
  - `401 Unauthorized`: Invalid or expired token
  - `403 Forbidden`: User doesn't have permission to delete this question
  - `404 Not Found`: Question doesn't exist

## Response Management Endpoints

### Submit Form Response
- **Endpoint**: `POST /api/forms/<form_id>/responses`
- **Description**: Submit a response to a form
- **Request Body**:
  ```json
  {
    "answers": [
      {
        "question_id": "integer (required)",
        "answer_text": "string (for text answers)",
        "answer_value": "mixed (for complex answers like checkboxes)"
      }
    ]
  }
  ```
- **Responses**:
  - `201 Created`: Response submitted successfully
  - `400 Bad Request`: Validation errors or invalid answers
  - `404 Not Found`: Form doesn't exist or is not published
  - `429 Too Many Requests`: Response limit reached

### Get Form Responses
- **Endpoint**: `GET /api/forms/<form_id>/responses`
- **Description**: Get all responses for a form
- **Headers**: `Authorization: Bearer <access_token>`
- **Query Parameters**:
  - `page` (optional): Page number for pagination
  - `limit` (optional): Number of responses per page (default 10)
- **Responses**:
  - `200 OK`: List of responses with pagination info
  - `401 Unauthorized`: Invalid or expired token
  - `403 Forbidden`: User doesn't have permission to view responses
  - `404 Not Found`: Form doesn't exist

### Get Specific Response
- **Endpoint**: `GET /api/responses/<response_id>`
- **Description**: Get details of a specific response
- **Headers**: `Authorization: Bearer <access_token>`
- **Responses**:
  - `200 OK`: Response details
  - `401 Unauthorized`: Invalid or expired token
  - `403 Forbidden`: User doesn't have permission to view this response
  - `404 Not Found`: Response doesn't exist

### Export Form Responses
- **Endpoint**: `GET /api/forms/<form_id>/responses/export`
- **Description**: Export form responses in specified format
- **Headers**: `Authorization: Bearer <access_token>`
- **Query Parameters**:
  - `format` (required): Export format (csv, json, excel)
- **Responses**:
  - `200 OK`: File download with specified format
  - `401 Unauthorized`: Invalid or expired token
  - `403 Forbidden`: User doesn't have permission to export responses
  - `404 Not Found`: Form doesn't exist

## Analytics Endpoints

### Get Form Analytics
- **Endpoint**: `GET /api/forms/<form_id>/analytics`
- **Description**: Get analytics data for a form
- **Headers**: `Authorization: Bearer <access_token>`
- **Query Parameters**:
  - `start_date` (optional): Start date for analytics
  - `end_date` (optional): End date for analytics
- **Responses**:
  - `200 OK`: Analytics data with charts and statistics
  - `401 Unauthorized`: Invalid or expired token
  - `403 Forbidden`: User doesn't have permission to view analytics
  - `404 Not Found`: Form doesn't exist

### Get Dashboard Analytics
- **Endpoint**: `GET /api/analytics/dashboard`
- **Description**: Get dashboard analytics for current user
- **Headers**: `Authorization: Bearer <access_token>`
- **Responses**:
  - `200 OK`: Dashboard analytics data
  - `401 Unauthorized`: Invalid or expired token

## Form Templates Endpoints

### Get Form Templates
- **Endpoint**: `GET /api/templates`
- **Description**: Get available form templates
- **Headers**: `Authorization: Bearer <access_token>`
- **Query Parameters**:
  - `public` (optional): Include public templates (default false)
- **Responses**:
  - `200 OK`: List of templates
  - `401 Unauthorized`: Invalid or expired token

### Create Form Template
- **Endpoint**: `POST /api/templates`
- **Description**: Create a new form template
- **Headers**: `Authorization: Bearer <access_token>`
- **Request Body**:
  ```json
  {
    "name": "string (required)",
    "description": "string (optional)",
    "is_public": "boolean (optional, default false)",
    "content": "object (required, form structure as JSON)"
  }
  ```
- **Responses**:
  - `201 Created`: Template created successfully
  - `400 Bad Request`: Validation errors
  - `401 Unauthorized`: Invalid or expired token

### Use Form Template
- **Endpoint**: `POST /api/templates/<template_id>/use`
- **Description**: Create a new form using a template
- **Headers**: `Authorization: Bearer <access_token>`
- **Request Body**:
  ```json
  {
    "title": "string (required, form title)",
    "description": "string (optional)"
  }
  ```
- **Responses**:
  - `201 Created`: Form created from template
  - `400 Bad Request`: Validation errors
  - `401 Unauthorized`: Invalid or expired token
  - `404 Not Found`: Template doesn't exist

## Error Response Format

All error responses follow this format:
```json
{
  "error": "error_code",
  "message": "Human-readable error message",
  "details": {
    "field": "specific field with error (if applicable)",
    "value": "value that caused the error (if applicable)"
  }
}
```

## Success Response Format

Success responses follow this format for list endpoints:
```json
{
  "data": [...],
  "pagination": {
    "page": 1,
    "limit": 10,
    "total": 100,
    "pages": 10
  }
}
```

For single resource endpoints:
```json
{
  "data": { ... }
}
```

For simple operations:
```json
{
  "message": "Operation completed successfully"
}