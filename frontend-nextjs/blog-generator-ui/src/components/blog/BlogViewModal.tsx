"use client"
import { useState, Children, cloneElement, useRef, useEffect, useCallback } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Download, Copy, FileText, FileImage, FileCode, CheckCircle, Maximize2 } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkUnwrapImages from 'remark-unwrap-images';
import { BlogData } from '@/types/blog';
import { exportBlog, BlogExportFormat } from '@/lib/exporters/blogExport';

interface BlogViewModalProps {
  blog: BlogData | null;
  isOpen: boolean;
  onClose: () => void;
}

export function BlogViewModal({ blog, isOpen, onClose }: BlogViewModalProps) {
  const [copySuccess, setCopySuccess] = useState(false);
  const [downloading, setDownloading] = useState<BlogExportFormat | null>(null);
  const [modalSize, setModalSize] = useState({ width: 0, height: 0 });
  const [isResizing, setIsResizing] = useState(false);
  const modalRef = useRef<HTMLDivElement>(null);
  const resizeRef = useRef<HTMLDivElement>(null);

  // Calculate A4 proportions based on screen size
  const calculateA4Size = useCallback(() => {
    const viewportWidth = window.innerWidth;
    const viewportHeight = window.innerHeight;
    
    // A4 ratio is 1:1.414
    const a4Ratio = 1.414;
    
    // Calculate ideal width (85% of viewport width, max 1200px)
    const idealWidth = Math.min(viewportWidth * 0.85, 1200);
    const idealHeight = idealWidth * a4Ratio;
    
    // Ensure it fits in viewport (90% max height)
    const maxHeight = viewportHeight * 0.9;
    
    if (idealHeight > maxHeight) {
      const adjustedHeight = maxHeight;
      const adjustedWidth = adjustedHeight / a4Ratio;
      return { width: adjustedWidth, height: adjustedHeight };
    }
    
    return { width: idealWidth, height: idealHeight };
  }, []);

  // Initialize modal size
  useEffect(() => {
    if (isOpen && modalSize.width === 0) {
      const size = calculateA4Size();
      setModalSize(size);
    }
  }, [isOpen, modalSize.width, calculateA4Size]);

  // Handle window resize
  useEffect(() => {
    const handleResize = () => {
      if (isOpen && !isResizing) {
        const size = calculateA4Size();
        setModalSize(size);
      }
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [isOpen, isResizing, calculateA4Size]);

  // Resize functionality
  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isResizing || !modalRef.current) return;
      
      const rect = modalRef.current.getBoundingClientRect();
      const newWidth = e.clientX - rect.left;
      const newHeight = e.clientY - rect.top;
      
      // Minimum size constraints
      const minWidth = 400;
      const minHeight = 300;
      
      // Maximum size constraints (90% of viewport)
      const maxWidth = window.innerWidth * 0.95;
      const maxHeight = window.innerHeight * 0.95;
      
      setModalSize({
        width: Math.max(minWidth, Math.min(newWidth, maxWidth)),
        height: Math.max(minHeight, Math.min(newHeight, maxHeight))
      });
    };

    const handleMouseUp = () => {
      setIsResizing(false);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };

    if (isResizing) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = 'nw-resize';
      document.body.style.userSelect = 'none';
    }

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isResizing]);

  const handleResizeStart = (e: React.MouseEvent) => {
    e.preventDefault();
    setIsResizing(true);
  };

  const handleResetSize = () => {
    const defaultSize = calculateA4Size();
    setModalSize(defaultSize);
  };

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

  const downloadFile = async (format: BlogExportFormat) => {
    if (!blog) return;
    setDownloading(format);
    try { await exportBlog({ format, blog }); }
    catch (e) { console.error('Export failed:', e); }
    finally { setDownloading(null); }
  };

  if (!blog) return null;

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent 
        ref={modalRef}
        className="overflow-hidden flex flex-col p-0 gap-0"
        style={{
          width: modalSize.width || 'auto',
          height: modalSize.height || 'auto',
          maxWidth: '95vw',
          maxHeight: '95vh',
          minWidth: '400px',
          minHeight: '300px'
        }}
      >
        <DialogHeader className="flex flex-row items-center justify-between space-y-0 pb-4 border-b p-6">
          <DialogTitle className="text-xl font-semibold truncate pr-4">
            {blog.topic}
          </DialogTitle>
          <div className="flex items-center space-x-2">
            {/* Reset Size Button */}
            <Button
              variant="ghost"
              size="sm"
              onClick={handleResetSize}
              className="p-2 opacity-60 hover:opacity-100 transition-opacity"
              title="Reset to default size (A4 ratio)"
            >
              <Maximize2 className="w-4 h-4" />
            </Button>

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
              
              <div className="absolute right-0 top-full mt-1 w-48 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-600 rounded-md shadow-lg opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 z-10">
                <div className="py-1">
                  <button
                    onClick={() => downloadFile('md')}
                    disabled={downloading === 'md'}
                    className="w-full px-4 py-2 text-left text-sm text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-700 flex items-center space-x-2 disabled:opacity-50"
                  >
                    <FileText className="w-4 h-4" />
                    <span>Markdown (.md)</span>
                  </button>
                  
                  <button
                    onClick={() => downloadFile('html')}
                    disabled={downloading === 'html'}
                    className="w-full px-4 py-2 text-left text-sm text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-700 flex items-center space-x-2 disabled:opacity-50"
                  >
                    <FileCode className="w-4 h-4" />
                    <span>HTML (.html)</span>
                  </button>
                  
                  <button
                    onClick={() => downloadFile('pdf')}
                    disabled={downloading === 'pdf'}
                    className="w-full px-4 py-2 text-left text-sm text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-700 flex items-center space-x-2 disabled:opacity-50"
                  >
                    <FileImage className="w-4 h-4" />
                    <span>PDF (Print)</span>
                  </button>
                  
                  <button
                    onClick={() => downloadFile('docx')}
                    disabled={downloading === 'docx'}
                    className="w-full px-4 py-2 text-left text-sm text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-700 flex items-center space-x-2 disabled:opacity-50"
                  >
                    <FileText className="w-4 h-4" />
                    <span>Word (.docx)</span>
                  </button>
                  
                  <button
                    onClick={() => downloadFile('rtf')}
                    disabled={downloading === 'rtf'}
                    className="w-full px-4 py-2 text-left text-sm text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-700 flex items-center space-x-2 disabled:opacity-50"
                  >
                    <FileText className="w-4 h-4" />
                    <span>RTF (.rtf)</span>
                  </button>
                </div>
              </div>
            </div>
            
            {/* Single close handled by dialog overlay (removed extra X button) */}
          </div>
        </DialogHeader>

        {/* Blog Content - Responsive Paper Style */}
        <div className="flex-1 overflow-y-auto px-6">
          <Card className="mx-auto my-6 shadow-lg bg-white" style={{ 
            width: '100%',
            maxWidth: '100%',
            minHeight: 'calc(100% - 3rem)'
          }}>
            <div className="p-8" style={{ 
              padding: '2cm',
              fontFamily: 'Georgia, "Times New Roman", serif',
              lineHeight: '1.6',
              color: '#333'
            }}>
              {/* Optional Hero Image (stored separately from markdown) */}
              {blog.heroImageUrl && (
                <figure className="mb-10 -mt-4">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={blog.heroImageUrl}
                    alt={blog.topic + ' hero image'}
                    className="w-full h-auto rounded-xl shadow-md object-cover max-h-[420px]"
                    loading="eager"
                    onError={(e) => {
                      (e.currentTarget as HTMLImageElement).src = '/placeholder-image.jpg'
                    }}
                  />
                  <figcaption className="mt-2 text-sm text-gray-500 italic">Hero image – AI generated / Unsplash fallback</figcaption>
                </figure>
              )}
              <div className="prose prose-lg max-w-none">
                <ReactMarkdown
                  remarkPlugins={[remarkGfm, remarkUnwrapImages]}
                  components={{
                    p: ({ node, children, ...props }) => {
                      const rawChildren = (node as any)?.children || [];
                      if (rawChildren.length === 0) return null;
                      const onlyImages = rawChildren.every((ch: any) => {
                        if (ch.type === 'image') return true;
                        if (ch.type === 'text') return (ch.value || '').trim() === '';
                        return false;
                      });
                      if (onlyImages) {
                        // Wrap each image element (already rendered inline) in a figure for block layout
                        const figures = Children.map(children, (child: any, idx) => {
                          if (!child) return null;
                          if (child.type === 'img' || (child.props && child.props.alt !== undefined)) {
                            const alt = child.props?.alt;
                            const title = child.props?.title;
                            return (
                              <figure key={idx} className="my-8 text-center">
                                {cloneElement(child, {
                                  className: (child.props?.className || '') + ' mx-auto rounded-lg shadow-md max-w-full h-auto',
                                  loading: 'lazy'
                                })}
                                {(title || alt) && (
                                  <figcaption className="mt-2 text-sm text-gray-500 italic">
                                    {title || alt}
                                  </figcaption>
                                )}
                              </figure>
                            );
                          }
                          return child;
                        });
                        return <>{figures}</>;
                      }
                      return <p className="mb-4 leading-relaxed text-gray-700" {...props}>{children}</p>;
                    },
                    img: ({ src, alt }) => {
                      const imageSrc = typeof src === 'string' ? src : '/placeholder-image.svg';
                      const external = imageSrc.startsWith('http');
                      const isInline = alt?.startsWith('inline:');
                      const finalAlt = isInline ? alt?.replace(/^inline:/, '') : alt;
                      return (
                        // eslint-disable-next-line @next/next/no-img-element
                        <img
                          src={imageSrc}
                          alt={finalAlt || 'Image'}
                          className={
                            isInline
                              ? 'inline-block align-text-bottom mx-1 h-6 w-6 object-contain'
                              : 'mx-auto block w-full max-w-full rounded-lg shadow-md object-cover'
                          }
                          loading={isInline ? 'lazy' : 'lazy'}
                          {...(external ? { referrerPolicy: 'no-referrer' } : {})}
                          onLoad={(e) => {
                            const el = e.currentTarget
                            el.dataset.loaded = 'true'
                          }}
                          onError={(e) => {
                            const el = e.currentTarget as HTMLImageElement
                            if (el.src.endsWith('placeholder-image.svg') || el.dataset.failed) return
                            el.dataset.failed = 'true'
                            el.src = '/placeholder-image.svg'
                          }}
                        />
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
        <div className="border-t pt-4 px-6 pb-4 text-sm text-gray-500 flex justify-between items-center">
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

        {/* Resize Handle */}
        <div
          ref={resizeRef}
          onMouseDown={handleResizeStart}
          className="absolute bottom-0 right-0 w-4 h-4 cursor-nw-resize opacity-50 hover:opacity-100 transition-opacity"
          style={{
            background: 'linear-gradient(-45deg, transparent 0%, transparent 30%, #666 30%, #666 40%, transparent 40%, transparent 60%, #666 60%, #666 70%, transparent 70%)',
          }}
          title="Drag to resize"
        />
      </DialogContent>
    </Dialog>
  );
}
