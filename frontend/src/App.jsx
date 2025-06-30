import React, { useState } from 'react';
import BlogForm from './components/BlogForm';

function App() {
    const [blogContent, setBlogContent] = useState(null);

    const handleBlogGeneration = async (topic) => {
        try {
            const response = await fetch('http://localhost:5000/generate-blog', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ topic }),
            });

            if (!response.ok) {
                throw new Error('Network response was not ok');
            }

            const data = await response.json();
            setBlogContent(data.blogContent);
        } catch (error) {
            console.error('Error generating blog:', error);
        }
    };

    return (
        <div>
            <h1>Blog Generator</h1>
            <BlogForm onGenerate={handleBlogGeneration} />
            {blogContent && (
                <div>
                    <h2>Generated Blog</h2>
                    <div>{blogContent}</div>
                </div>
            )}
        </div>
    );
}

export default App;