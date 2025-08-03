"use client"
import { useState } from 'react';
import Image from 'next/image';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { 
  Download, 
  Copy, 
  FileText, 
  FileImage, 
  FileCode, 
  X,
  CheckCircle 
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { BlogData } from '@/types/blog';

interface BlogViewModalProps {
  blog: BlogData | null;
  isOpen: boolean;
  onClose: () => void;
}

export function BlogViewModal({ blog, isOpen, onClose }: BlogViewModalProps) {
  const [copySuccess, setCopySuccess] = useState(false);
  const [downloading, setDownloading] = useState<string | null>(null);

  const handleCopy = async () => {
    if (!blog?.content) return;
    
    try {
      await navigator.clipboard.writeText(blog.content);
      setCopySuccess(true);
      setTimeout(() => setCopySuccess(false), 2000);
    } catch (error) {
      console.error('Failed to copy content:', error);
    }
  };

  const generateHTML = (content: string, title: string) => {
    return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>${title}</title>
    <style>
        body {
            font-family: 'Georgia', 'Times New Roman', serif;
            line-height: 1.6;
            max-width: 800px;
            margin: 0 auto;
            padding: 40px 20px;
            color: #333;
        }
        h1, h2, h3, h4, h5, h6 {
            color: #2c3e50;
            margin-top: 2em;
            margin-bottom: 1em;
        }
        h1 {
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }
        img {
            max-width: 100%;
            height: auto;
            margin: 20px 0;
            border-radius: 8px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        }
        blockquote {
            border-left: 4px solid #3498db;
            padding-left: 20px;
            margin: 20px 0;
            background-color: #f8f9fa;
            padding: 15px 20px;
            border-radius: 4px;
        }
        code {
            background-color: #f1f1f1;
            padding: 2px 4px;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
        }
        pre {
            background-color: #f8f8f8;
            padding: 15px;
            border-radius: 5px;
            overflow-x: auto;
        }
        @media print {
            body { margin: 0; padding: 20px; }
            @page { size: A4; margin: 2cm; }
        }
    </style>
</head>
<body>
    ${content}
</body>
</html>`;
  };

  const downloadFile = async (format: 'pdf' | 'md' | 'html' | 'docx') => {
    if (!blog?.content) return;
    
    setDownloading(format);
    
    try {
      const filename = `${blog.topic.replace(/[^a-z0-9]/gi, '_').toLowerCase()}_blog`;
      
      switch (format) {
        case 'md':
          downloadText(blog.content, `${filename}.md`, 'text/markdown');
          break;
          
        case 'html':
          const htmlContent = generateHTML(blog.content, blog.topic);
          downloadText(htmlContent, `${filename}.html`, 'text/html');
          break;
          
        case 'pdf':
          await downloadPDF(blog.content, blog.topic);
          break;
          
        case 'docx':
          await downloadDocx(blog.content, blog.topic, filename);
          break;
      }
    } catch (error) {
      console.error(`Error downloading ${format}:`, error);
    } finally {
      setDownloading(null);
    }
  };

  const downloadText = (content: string, filename: string, mimeType: string) => {
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const downloadPDF = async (content: string, title: string) => {
    // For PDF generation, we'll use the browser's print functionality
    // Create a new window with the formatted content
    const htmlContent = generateHTML(content, title);
    const printWindow = window.open('', '_blank');
    if (printWindow) {
      printWindow.document.write(htmlContent);
      printWindow.document.close();
      
      // Wait for content to load then trigger print
      printWindow.onload = () => {
        setTimeout(() => {
          printWindow.print();
          printWindow.close();
        }, 500);
      };
    }
  };

  const downloadDocx = async (content: string, title: string, filename: string) => {
    // For Word document, we'll create a simple RTF file which Word can open
    const rtfContent = `{\\rtf1\\ansi\\deff0 {\\fonttbl {\\f0 Times New Roman;}}
\\f0\\fs24 {\\b ${title}}\\par\\par
${content.replace(/\n/g, '\\par ')}
}`;
    
    downloadText(rtfContent, `${filename}.rtf`, 'application/rtf');
  };

  if (!blog) return null;

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-6xl max-h-[90vh] overflow-hidden flex flex-col">
        <DialogHeader className="flex flex-row items-center justify-between space-y-0 pb-4 border-b">
          <DialogTitle className="text-xl font-semibold truncate pr-4">
            {blog.topic}
          </DialogTitle>
          <div className="flex items-center space-x-2">
            {/* Action Buttons */}
            <Button
              variant="outline"
              size="sm"
              onClick={handleCopy}
              className="flex items-center space-x-1"
            >
              {copySuccess ? (
                <CheckCircle className="w-4 h-4 text-green-600" />
              ) : (
                <Copy className="w-4 h-4" />
              )}
              <span>{copySuccess ? 'Copied!' : 'Copy'}</span>
            </Button>
            
            {/* Download Dropdown */}
            <div className="relative group">
              <Button variant="outline" size="sm" className="flex items-center space-x-1">
                <Download className="w-4 h-4" />
                <span>Download</span>
              </Button>
              
              <div className="absolute right-0 top-full mt-1 w-48 bg-white border border-gray-200 rounded-md shadow-lg opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 z-10">
                <div className="py-1">
                  <button
                    onClick={() => downloadFile('md')}
                    disabled={downloading === 'md'}
                    className="w-full px-4 py-2 text-left text-sm hover:bg-gray-50 flex items-center space-x-2 disabled:opacity-50"
                  >
                    <FileText className="w-4 h-4" />
                    <span>Markdown (.md)</span>
                  </button>
                  
                  <button
                    onClick={() => downloadFile('html')}
                    disabled={downloading === 'html'}
                    className="w-full px-4 py-2 text-left text-sm hover:bg-gray-50 flex items-center space-x-2 disabled:opacity-50"
                  >
                    <FileCode className="w-4 h-4" />
                    <span>HTML (.html)</span>
                  </button>
                  
                  <button
                    onClick={() => downloadFile('pdf')}
                    disabled={downloading === 'pdf'}
                    className="w-full px-4 py-2 text-left text-sm hover:bg-gray-50 flex items-center space-x-2 disabled:opacity-50"
                  >
                    <FileImage className="w-4 h-4" />
                    <span>PDF (Print)</span>
                  </button>
                  
                  <button
                    onClick={() => downloadFile('docx')}
                    disabled={downloading === 'docx'}
                    className="w-full px-4 py-2 text-left text-sm hover:bg-gray-50 flex items-center space-x-2 disabled:opacity-50"
                  >
                    <FileText className="w-4 h-4" />
                    <span>Word (.rtf)</span>
                  </button>
                </div>
              </div>
            </div>
            
            <Button variant="ghost" size="sm" onClick={onClose}>
              <X className="w-4 h-4" />
            </Button>
          </div>
        </DialogHeader>

        {/* Blog Content - A4 Paper Style */}
        <div className="flex-1 overflow-y-auto">
          <Card className="mx-auto my-6 shadow-lg" style={{ 
            width: '210mm', 
            minHeight: '297mm',
            maxWidth: '100%',
            backgroundColor: 'white'
          }}>
            <div className="p-8" style={{ 
              padding: '2cm',
              fontFamily: 'Georgia, "Times New Roman", serif',
              lineHeight: '1.6',
              color: '#333'
            }}>
              <div className="prose prose-lg max-w-none">
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  components={{
                    img: ({ src, alt, title }) => {
                      const imageSrc = typeof src === 'string' ? src : '/placeholder-image.svg';
                      const isExternalImage = imageSrc.startsWith('http') || imageSrc.startsWith('https');
                      
                      return (
                        <div className="my-8 text-center">
                          <div className="relative inline-block max-w-full">
                            <Image
                              src={imageSrc}
                              alt={alt || 'Blog image'}
                              width={800}
                              height={400}
                              className="rounded-lg shadow-md max-w-full h-auto"
                              style={{ maxHeight: '400px', objectFit: 'cover' }}
                              unoptimized={isExternalImage}
                              loading="lazy"
                              onError={(e) => {
                                e.currentTarget.src = '/placeholder-image.svg';
                              }}
                            />
                          </div>
                          {title && (
                            <em className="block text-sm text-gray-500 mt-2 italic">
                              {title}
                            </em>
                          )}
                        </div>
                      );
                    },
                    h1: ({ children, ...props }) => (
                      <h1 className="text-3xl font-bold mb-6 mt-8 pb-3 border-b-2 border-blue-500 text-gray-900" {...props}>
                        {children}
                      </h1>
                    ),
                    h2: ({ children, ...props }) => (
                      <h2 className="text-2xl font-semibold mb-4 mt-8 text-gray-800" {...props}>
                        {children}
                      </h2>
                    ),
                    h3: ({ children, ...props }) => (
                      <h3 className="text-xl font-semibold mb-3 mt-6 text-gray-800" {...props}>
                        {children}
                      </h3>
                    ),
                    h4: ({ children, ...props }) => (
                      <h4 className="text-lg font-semibold mb-2 mt-4 text-gray-800" {...props}>
                        {children}
                      </h4>
                    ),
                    p: ({ children, ...props }) => (
                      <p className="mb-4 leading-relaxed text-gray-700" {...props}>
                        {children}
                      </p>
                    ),
                    ul: ({ children, ...props }) => (
                      <ul className="mb-4 ml-6 list-disc space-y-1 text-gray-700" {...props}>
                        {children}
                      </ul>
                    ),
                    ol: ({ children, ...props }) => (
                      <ol className="mb-4 ml-6 list-decimal space-y-1 text-gray-700" {...props}>
                        {children}
                      </ol>
                    ),
                    li: ({ children, ...props }) => (
                      <li className="leading-relaxed" {...props}>
                        {children}
                      </li>
                    ),
                    blockquote: ({ children, ...props }) => (
                      <blockquote className="border-l-4 border-blue-500 pl-4 py-3 my-4 bg-blue-50 rounded-r-lg italic text-gray-700" {...props}>
                        {children}
                      </blockquote>
                    ),
                    code: ({ children, ...props }) => (
                      <code className="bg-gray-100 px-2 py-1 rounded text-sm font-mono text-gray-800" {...props}>
                        {children}
                      </code>
                    ),
                    pre: ({ children, ...props }) => (
                      <pre className="bg-gray-100 p-4 rounded-lg overflow-x-auto my-4 border" {...props}>
                        {children}
                      </pre>
                    ),
                    strong: ({ children, ...props }) => (
                      <strong className="font-bold text-gray-900" {...props}>
                        {children}
                      </strong>
                    ),
                    em: ({ children, ...props }) => (
                      <em className="italic text-gray-700" {...props}>
                        {children}
                      </em>
                    ),
                    a: ({ children, href, ...props }) => (
                      <a 
                        href={href} 
                        className="text-blue-600 hover:text-blue-800 underline"
                        target="_blank"
                        rel="noopener noreferrer"
                        {...props}
                      >
                        {children}
                      </a>
                    ),
                  }}
                >
                  {blog.content || 'No content available'}
                </ReactMarkdown>
              </div>
            </div>
          </Card>
        </div>

        {/* Footer with blog info */}
        <div className="border-t pt-4 text-sm text-gray-500 flex justify-between items-center">
          <div>
            Created: {new Date(blog.createdAt).toLocaleDateString()}
            {blog.completedAt && (
              <span className="ml-4">
                Completed: {new Date(blog.completedAt).toLocaleDateString()}
              </span>
            )}
          </div>
          <div className="text-xs">
            Status: <span className="capitalize">{blog.status}</span>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
