# Bloggen Web Service Backend

This is the backend service for the Bloggen web application. It provides an API to generate blog posts based on user-defined topics.

## Setup Instructions

1. **Clone the repository:**
   ```
   git clone <repository-url>
   cd bloggen-web-service/backend
   ```

2. **Create a virtual environment (optional but recommended):**
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

3. **Install the required dependencies:**
   ```
   pip install -r requirements.txt
   ```

## Usage

To run the backend service, execute the following command:

```
python src/main.py
```

The service will start and listen for incoming requests.

## API Endpoints

### Generate Blog

- **Endpoint:** `/api/generate`
- **Method:** `POST`
- **Request Body:**
  ```json
  {
    "topic": "Your blog topic here"
  }
  ```
- **Response:**
  - On success: Returns the generated blog file.
  - On error: Returns an error message.

## File Structure

- `src/main.py`: Contains the main logic for the backend service.
- `src/api.py`: Defines the web service endpoints.
- `src/utils.py`: Contains utility functions for the backend.
- `requirements.txt`: Lists the Python dependencies required for the backend service.

## Contributing

Feel free to submit issues or pull requests for improvements or bug fixes.