import React, { useState } from 'react';

const BlogForm = () => {
    const [topic, setTopic] = useState('');
    const [generatedBlog, setGeneratedBlog] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        setError(null);

        try {
            const response = await fetch('/api/generate-blog', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ topic }),
            });

            if (!response.ok) {
                throw new Error('Failed to generate blog');
            }

            const data = await response.json();
            setGeneratedBlog(data.blog);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div>
            <h1>Generate a Blog</h1>
            <form onSubmit={handleSubmit}>
                <input
                    type="text"
                    value={topic}
                    onChange={(e) => setTopic(e.target.value)}
                    placeholder="Enter blog topic"
                    required
                />
                <button type="submit" disabled={loading}>
                    {loading ? 'Generating...' : 'Generate Blog'}
                </button>
            </form>
            {error && <p style={{ color: 'red' }}>{error}</p>}
            {generatedBlog && (
                <div>
                    <h2>Generated Blog</h2>
                    <p>{generatedBlog}</p>
                </div>
            )}
        </div>
    );
};

export default BlogForm;