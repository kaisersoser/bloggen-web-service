# Bloggen Web Service Frontend

This is the frontend part of the Bloggen web service, built using React. It allows users to generate blog posts by specifying a topic and interacting with the backend service.

## Getting Started

To get started with the frontend application, follow these steps:

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd bloggen-web-service/frontend
   ```

2. **Install dependencies**:
   Make sure you have Node.js installed. Then run:
   ```bash
   npm install
   ```

3. **Run the application**:
   Start the development server with:
   ```bash
   npm start
   ```
   This will launch the application in your default web browser.

## Folder Structure

- `src/`: Contains the source code for the React application.
  - `App.jsx`: The main component that manages the application state.
  - `index.jsx`: The entry point for the React application.
  - `components/`: Contains reusable components.
    - `BlogForm.jsx`: A form component for users to input the blog topic.

## Usage

Once the application is running, you can enter a blog topic in the form provided. Upon submission, the application will communicate with the backend service to generate the blog post based on the specified topic.

## API Integration

The frontend communicates with the backend API defined in `backend/src/api.py`. Ensure that the backend service is running to handle requests from the frontend.

## Contributing

If you would like to contribute to this project, please fork the repository and submit a pull request with your changes.

## License

This project is licensed under the MIT License. See the LICENSE file for more details.