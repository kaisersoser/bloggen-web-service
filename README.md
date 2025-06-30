# Bloggen Web Service

This project is a web service that allows users to generate blog posts based on specified topics. It consists of a backend service built with Python and a frontend application built with React.

## Project Structure

```
bloggen-web-service
├── backend
│   ├── src
│   │   ├── main.py          # Contains the main logic for generating blogs
│   │   ├── api.py           # Defines the web service endpoints
│   │   └── utils.py         # Utility functions for the backend
│   ├── requirements.txt      # Python dependencies for the backend
│   └── README.md             # Documentation for the backend service
├── frontend
│   ├── src
│   │   ├── App.jsx          # Main component of the React application
│   │   ├── index.jsx        # Entry point for the React application
│   │   └── components
│   │       └── BlogForm.jsx # Form component for blog topic input
│   ├── package.json          # Configuration for the frontend application
│   └── README.md             # Documentation for the frontend application
└── README.md                 # Overall documentation for the project
```

## Backend Setup

1. Navigate to the `backend` directory.
2. Install the required Python packages:
   ```
   pip install -r requirements.txt
   ```
3. Run the backend service:
   ```
   python src/api.py
   ```

## Frontend Setup

1. Navigate to the `frontend` directory.
2. Install the required npm packages:
   ```
   npm install
   ```
3. Start the React application:
   ```
   npm start
   ```

## API Endpoints

- **POST /generate**: Generates a blog post based on the provided topic.
  - Request Body:
    ```json
    {
      "topic": "Your blog topic here"
    }
    ```
  - Response: Returns the generated blog file.

## Usage

1. Use the frontend application to input a blog topic.
2. Submit the form to call the backend service and generate the blog.
3. The generated blog will be returned and can be viewed or downloaded.

## Contributing

Contributions are welcome! Please feel free to submit a pull request or open an issue for any enhancements or bug fixes.