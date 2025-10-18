// Enhanced HTML export with perfect BlogViewModal visual matching
import { BlogData } from '@/types/blog';
import { BLOG_STYLING } from './blogStyles';

export function generateEnhancedHTML(blog: BlogData): string {
  const title = blog.topic || 'Blog Post';
  const content = blog.content || 'No content available';
  const heroImageUrl = blog.heroImageUrl;
  const createdAt = new Date(blog.createdAt).toLocaleDateString();
  const completedAt = blog.completedAt ? new Date(blog.completedAt).toLocaleDateString() : null;

  return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>${escapeHtml(title)}</title>
    <style>
        ${generateEnhancedCSS()}
    </style>
</head>
<body>
    <div class="blog-container">
        <div class="blog-paper">
            ${heroImageUrl ? generateHeroImageHTML(heroImageUrl, title) : ''}
            <div class="blog-content">
                ${processMarkdownToHTML(content)}
            </div>
            <div class="blog-footer">
                <div class="blog-meta">
                    <span>Created: ${createdAt}</span>
                    ${completedAt ? `<span class="meta-separator">Completed: ${completedAt}</span>` : ''}
                </div>
                <div class="blog-status">
                    Status: <span class="status-value">${blog.status}</span>
                </div>
            </div>
        </div>
    </div>
</body>
</html>`;
}

function generateEnhancedCSS(): string {
  return `
    /* Reset and base styles */
    * {
        margin: 0;
        padding: 0;
        box-sizing: border-box;
    }

    body {
        font-family: ${BLOG_STYLING.TYPOGRAPHY.FONT_FAMILY};
        line-height: ${BLOG_STYLING.TYPOGRAPHY.LINE_HEIGHT};
        color: ${BLOG_STYLING.TYPOGRAPHY.BASE_COLOR};
        background-color: #f5f5f5;
        padding: 2rem 1rem;
    }

    /* Blog container with A4 proportions */
    .blog-container {
        max-width: ${BLOG_STYLING.PAGE.A4_WIDTH_MM}mm;
        margin: 0 auto;
        background: ${BLOG_STYLING.PAGE.BACKGROUND};
        box-shadow: ${BLOG_STYLING.PAGE.SHADOW};
        border-radius: 8px;
        overflow: hidden;
    }

    .blog-paper {
        padding: ${BLOG_STYLING.PAGE.PADDING};
        min-height: ${BLOG_STYLING.PAGE.A4_HEIGHT_MM}mm;
        background: ${BLOG_STYLING.PAGE.BACKGROUND};
    }

    /* Hero image styling */
    .hero-figure {
        margin-bottom: ${BLOG_STYLING.HERO_IMAGE.marginBottom};
        margin-top: ${BLOG_STYLING.HERO_IMAGE.marginTop};
        text-align: center;
    }

    .hero-image {
        width: ${BLOG_STYLING.HERO_IMAGE.width};
        height: ${BLOG_STYLING.HERO_IMAGE.height};
        max-height: ${BLOG_STYLING.HERO_IMAGE.maxHeight};
        object-fit: ${BLOG_STYLING.HERO_IMAGE.objectFit};
        border-radius: ${BLOG_STYLING.HERO_IMAGE.borderRadius};
        box-shadow: ${BLOG_STYLING.HERO_IMAGE.boxShadow};
    }

    .hero-caption {
        margin-top: ${BLOG_STYLING.CAPTION.marginTop};
        font-size: ${BLOG_STYLING.CAPTION.fontSize};
        color: ${BLOG_STYLING.CAPTION.color};
        font-style: ${BLOG_STYLING.CAPTION.fontStyle};
        text-align: ${BLOG_STYLING.CAPTION.textAlign};
    }

    /* Typography */
    h1 {
        font-size: ${BLOG_STYLING.TYPOGRAPHY.H1.fontSize};
        font-weight: ${BLOG_STYLING.TYPOGRAPHY.H1.fontWeight};
        margin-bottom: ${BLOG_STYLING.TYPOGRAPHY.H1.marginBottom};
        margin-top: ${BLOG_STYLING.TYPOGRAPHY.H1.marginTop};
        padding-bottom: ${BLOG_STYLING.TYPOGRAPHY.H1.paddingBottom};
        border-bottom: ${BLOG_STYLING.TYPOGRAPHY.H1.borderBottom};
        color: ${BLOG_STYLING.TYPOGRAPHY.H1.color};
    }

    h2 {
        font-size: ${BLOG_STYLING.TYPOGRAPHY.H2.fontSize};
        font-weight: ${BLOG_STYLING.TYPOGRAPHY.H2.fontWeight};
        margin-bottom: ${BLOG_STYLING.TYPOGRAPHY.H2.marginBottom};
        margin-top: ${BLOG_STYLING.TYPOGRAPHY.H2.marginTop};
        color: ${BLOG_STYLING.TYPOGRAPHY.H2.color};
    }

    h3 {
        font-size: ${BLOG_STYLING.TYPOGRAPHY.H3.fontSize};
        font-weight: ${BLOG_STYLING.TYPOGRAPHY.H3.fontWeight};
        margin-bottom: ${BLOG_STYLING.TYPOGRAPHY.H3.marginBottom};
        margin-top: ${BLOG_STYLING.TYPOGRAPHY.H3.marginTop};
        color: ${BLOG_STYLING.TYPOGRAPHY.H3.color};
    }

    h4 {
        font-size: ${BLOG_STYLING.TYPOGRAPHY.H4.fontSize};
        font-weight: ${BLOG_STYLING.TYPOGRAPHY.H4.fontWeight};
        margin-bottom: ${BLOG_STYLING.TYPOGRAPHY.H4.marginBottom};
        margin-top: ${BLOG_STYLING.TYPOGRAPHY.H4.marginTop};
        color: ${BLOG_STYLING.TYPOGRAPHY.H4.color};
    }

    p {
        margin-bottom: ${BLOG_STYLING.TEXT.PARAGRAPH.marginBottom};
        line-height: ${BLOG_STYLING.TEXT.PARAGRAPH.lineHeight};
        color: ${BLOG_STYLING.TEXT.PARAGRAPH.color};
    }

    strong {
        font-weight: ${BLOG_STYLING.TEXT.STRONG.fontWeight};
        color: ${BLOG_STYLING.TEXT.STRONG.color};
    }

    em {
        font-style: ${BLOG_STYLING.TEXT.EMPHASIS.fontStyle};
        color: ${BLOG_STYLING.TEXT.EMPHASIS.color};
    }

    a {
        color: ${BLOG_STYLING.TEXT.LINK.color};
        text-decoration: ${BLOG_STYLING.TEXT.LINK.textDecoration};
    }

    a:hover {
        color: ${BLOG_STYLING.TEXT.LINK_HOVER.color};
    }

    /* Lists */
    ul {
        margin-bottom: ${BLOG_STYLING.LISTS.UL.marginBottom};
        margin-left: ${BLOG_STYLING.LISTS.UL.marginLeft};
        list-style-type: ${BLOG_STYLING.LISTS.UL.listStyleType};
        color: ${BLOG_STYLING.LISTS.UL.color};
    }

    ol {
        margin-bottom: ${BLOG_STYLING.LISTS.OL.marginBottom};
        margin-left: ${BLOG_STYLING.LISTS.OL.marginLeft};
        list-style-type: ${BLOG_STYLING.LISTS.OL.listStyleType};
        color: ${BLOG_STYLING.LISTS.OL.color};
    }

    li {
        line-height: ${BLOG_STYLING.LISTS.LI.lineHeight};
        margin-bottom: ${BLOG_STYLING.LISTS.LI.marginBottom};
    }

    /* Content images */
    .content-image {
        margin-top: ${BLOG_STYLING.CONTENT_IMAGE.marginTop};
        margin-bottom: ${BLOG_STYLING.CONTENT_IMAGE.marginBottom};
        border-radius: ${BLOG_STYLING.CONTENT_IMAGE.borderRadius};
        box-shadow: ${BLOG_STYLING.CONTENT_IMAGE.boxShadow};
        max-width: ${BLOG_STYLING.CONTENT_IMAGE.maxWidth};
        height: ${BLOG_STYLING.CONTENT_IMAGE.height};
        display: ${BLOG_STYLING.CONTENT_IMAGE.display};
        margin-left: auto;
        margin-right: auto;
    }

    .content-figure {
        margin: ${BLOG_STYLING.CONTENT_IMAGE.marginTop} 0 ${BLOG_STYLING.CONTENT_IMAGE.marginBottom} 0;
        text-align: center;
    }

    .content-caption {
        margin-top: ${BLOG_STYLING.CAPTION.marginTop};
        font-size: ${BLOG_STYLING.CAPTION.fontSize};
        color: ${BLOG_STYLING.CAPTION.color};
        font-style: ${BLOG_STYLING.CAPTION.fontStyle};
    }

    /* Blockquotes */
    blockquote {
        border-left: ${BLOG_STYLING.BLOCKQUOTE.borderLeft};
        padding-left: ${BLOG_STYLING.BLOCKQUOTE.paddingLeft};
        padding-top: ${BLOG_STYLING.BLOCKQUOTE.paddingTop};
        padding-bottom: ${BLOG_STYLING.BLOCKQUOTE.paddingBottom};
        margin-top: ${BLOG_STYLING.BLOCKQUOTE.marginTop};
        margin-bottom: ${BLOG_STYLING.BLOCKQUOTE.marginBottom};
        background-color: ${BLOG_STYLING.BLOCKQUOTE.backgroundColor};
        border-radius: ${BLOG_STYLING.BLOCKQUOTE.borderRadius};
        font-style: ${BLOG_STYLING.BLOCKQUOTE.fontStyle};
        color: ${BLOG_STYLING.BLOCKQUOTE.color};
    }

    /* Code */
    code {
        background-color: ${BLOG_STYLING.CODE.INLINE.backgroundColor};
        padding: ${BLOG_STYLING.CODE.INLINE.paddingTop} ${BLOG_STYLING.CODE.INLINE.paddingLeft};
        border-radius: ${BLOG_STYLING.CODE.INLINE.borderRadius};
        font-size: ${BLOG_STYLING.CODE.INLINE.fontSize};
        font-family: ${BLOG_STYLING.CODE.INLINE.fontFamily};
        color: ${BLOG_STYLING.CODE.INLINE.color};
    }

    pre {
        background-color: ${BLOG_STYLING.CODE.BLOCK.backgroundColor};
        padding: ${BLOG_STYLING.CODE.BLOCK.padding};
        border-radius: ${BLOG_STYLING.CODE.BLOCK.borderRadius};
        overflow-x: ${BLOG_STYLING.CODE.BLOCK.overflowX};
        margin: ${BLOG_STYLING.CODE.BLOCK.marginTop} 0 ${BLOG_STYLING.CODE.BLOCK.marginBottom} 0;
        border: ${BLOG_STYLING.CODE.BLOCK.border};
    }

    pre code {
        background: none;
        padding: 0;
        border-radius: 0;
    }

    /* Footer */
    .blog-footer {
        border-top: 1px solid #e5e7eb;
        padding-top: 1rem;
        margin-top: 3rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-size: 0.875rem;
        color: #6b7280;
    }

    .meta-separator {
        margin-left: 1rem;
    }

    .status-value {
        text-transform: capitalize;
    }

    /* Print styles for PDF generation */
    @media print {
        body {
            background: white;
            padding: 0;
        }
        
        .blog-container {
            box-shadow: none;
            border-radius: 0;
            max-width: none;
        }
        
        @page {
            size: A4;
            margin: ${BLOG_STYLING.PAGE.PADDING};
        }
    }

    /* Responsive design */
    @media (max-width: 768px) {
        body {
            padding: 1rem 0.5rem;
        }
        
        .blog-paper {
            padding: 1.5rem;
        }
        
        .blog-footer {
            flex-direction: column;
            gap: 0.5rem;
            align-items: flex-start;
        }
    }
  `;
}

function generateHeroImageHTML(imageUrl: string, title: string): string {
  return `
    <figure class="hero-figure">
        <img src="${escapeHtml(imageUrl)}" alt="${escapeHtml(title)} hero image" class="hero-image" />
        <figcaption class="hero-caption">Hero image – AI generated / Unsplash fallback</figcaption>
    </figure>
  `;
}

function processMarkdownToHTML(content: string): string {
  // Basic markdown to HTML conversion (simplified for demonstration)
  // In a real implementation, you'd use a proper markdown parser like marked.js
  
  const html = content
    // Headers
    .replace(/^### (.*$)/gim, '<h3>$1</h3>')
    .replace(/^## (.*$)/gim, '<h2>$1</h2>')
    .replace(/^# (.*$)/gim, '<h1>$1</h1>')
    
    // Bold and italic
    .replace(/\*\*\*(.*)\*\*\*/gim, '<strong><em>$1</em></strong>')
    .replace(/\*\*(.*)\*\*/gim, '<strong>$1</strong>')
    .replace(/\*(.*)\*/gim, '<em>$1</em>')
    
    // Links
    .replace(/\[([^\]]+)\]\(([^)]+)\)/gim, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>')
    
    // Images (with figure wrapper)
    .replace(/!\[([^\]]*)\]\(([^)]+)(?:\s+"([^"]*)")?\)/gim, (match, alt, src, title) => {
      const titleAttr = title ? ` title="${escapeHtml(title)}"` : '';
      const caption = title || alt;
      
      if (alt.startsWith('inline:')) {
        return `<img src="${escapeHtml(src)}" alt="${escapeHtml(alt.replace('inline:', ''))}"${titleAttr} style="display: inline; height: 1.5rem; width: 1.5rem; margin: 0 0.25rem;" />`;
      }
      
      return `
        <figure class="content-figure">
            <img src="${escapeHtml(src)}" alt="${escapeHtml(alt)}" class="content-image"${titleAttr} />
            ${caption ? `<figcaption class="content-caption">${escapeHtml(caption)}</figcaption>` : ''}
        </figure>
      `;
    })
    
    // Code blocks
    .replace(/```[\s\S]*?```/gim, (match) => {
      const code = match.replace(/```/g, '').trim();
      return `<pre><code>${escapeHtml(code)}</code></pre>`;
    })
    
    // Inline code
    .replace(/`([^`]+)`/gim, '<code>$1</code>')
    
    // Blockquotes
    .replace(/^> (.*$)/gim, '<blockquote>$1</blockquote>')
    
    // Lists (basic implementation)
    .replace(/^\* (.*$)/gim, '<li>$1</li>')
    .replace(/^(\d+)\. (.*$)/gim, '<li>$2</li>')
    
    // Paragraphs (split by double newlines)
    .split('\n\n')
    .map(paragraph => {
      paragraph = paragraph.trim();
      if (!paragraph) return '';
      if (paragraph.startsWith('<')) return paragraph; // Already HTML
      if (paragraph.includes('<li>')) {
        // Handle lists
        if (paragraph.match(/^\d+\./m)) {
          return `<ol>${paragraph}</ol>`;
        } else {
          return `<ul>${paragraph}</ul>`;
        }
      }
      return `<p>${paragraph.replace(/\n/g, '<br>')}</p>`;
    })
    .join('\n');

  return html;
}

function escapeHtml(text: string): string {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}