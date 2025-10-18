// Blog styling constants extracted from BlogViewModal for consistent export formatting
// This ensures exported documents match the visual appearance of the modal display

export const BLOG_STYLING = {
  // A4 Paper dimensions and layout
  PAGE: {
    A4_WIDTH_MM: 210,
    A4_HEIGHT_MM: 297,
    A4_RATIO: 1.414,
    PADDING: '2cm',
    BACKGROUND: 'white',
    SHADOW: '0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)', // shadow-lg
  },

  // Typography from BlogViewModal
  TYPOGRAPHY: {
    FONT_FAMILY: 'Georgia, "Times New Roman", serif',
    LINE_HEIGHT: '1.6',
    BASE_COLOR: '#333',
    
    // Heading styles (extracted from ReactMarkdown components)
    H1: {
      fontSize: '1.875rem', // text-3xl
      fontWeight: 'bold',
      marginBottom: '1.5rem', // mb-6
      marginTop: '2rem', // mt-8
      paddingBottom: '0.75rem', // pb-3
      borderBottom: '2px solid #3b82f6', // border-b-2 border-blue-500
      color: '#111827' // text-gray-900
    },
    H2: {
      fontSize: '1.5rem', // text-2xl
      fontWeight: '600', // font-semibold
      marginBottom: '1rem', // mb-4
      marginTop: '2rem', // mt-8
      color: '#1f2937' // text-gray-800
    },
    H3: {
      fontSize: '1.25rem', // text-xl
      fontWeight: '600',
      marginBottom: '0.75rem', // mb-3
      marginTop: '1.5rem', // mt-6
      color: '#1f2937'
    },
    H4: {
      fontSize: '1.125rem', // text-lg
      fontWeight: '600',
      marginBottom: '0.5rem', // mb-2
      marginTop: '1rem', // mt-4
      color: '#1f2937'
    }
  },

  // Hero image styling
  HERO_IMAGE: {
    marginBottom: '2.5rem', // mb-10
    marginTop: '-1rem', // -mt-4
    borderRadius: '0.75rem', // rounded-xl
    boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)', // shadow-md
    objectFit: 'cover',
    maxHeight: '420px',
    width: '100%',
    height: 'auto'
  },

  // Content image styling
  CONTENT_IMAGE: {
    marginTop: '2rem', // my-8
    marginBottom: '2rem',
    borderRadius: '0.5rem', // rounded-lg
    boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)', // shadow-md
    maxWidth: '100%',
    height: 'auto',
    display: 'block',
    margin: '0 auto'
  },

  // Text elements
  TEXT: {
    PARAGRAPH: {
      marginBottom: '1rem', // mb-4
      lineHeight: '1.625', // leading-relaxed
      color: '#374151' // text-gray-700
    },
    STRONG: {
      fontWeight: 'bold',
      color: '#111827' // text-gray-900
    },
    EMPHASIS: {
      fontStyle: 'italic',
      color: '#374151' // text-gray-700
    },
    LINK: {
      color: '#2563eb', // text-blue-600
      textDecoration: 'underline'
    },
    LINK_HOVER: {
      color: '#1d4ed8' // hover:text-blue-800
    }
  },

  // Lists
  LISTS: {
    UL: {
      marginBottom: '1rem', // mb-4
      marginLeft: '1.5rem', // ml-6
      listStyleType: 'disc',
      color: '#374151' // text-gray-700
    },
    OL: {
      marginBottom: '1rem',
      marginLeft: '1.5rem',
      listStyleType: 'decimal',
      color: '#374151'
    },
    LI: {
      lineHeight: '1.625', // leading-relaxed
      marginBottom: '0.25rem'
    }
  },

  // Special elements
  BLOCKQUOTE: {
    borderLeft: '4px solid #3b82f6', // border-l-4 border-blue-500
    paddingLeft: '1rem', // pl-4
    paddingTop: '0.75rem', // py-3
    paddingBottom: '0.75rem',
    marginTop: '1rem', // my-4
    marginBottom: '1rem',
    backgroundColor: '#eff6ff', // bg-blue-50
    borderRadius: '0 0.5rem 0.5rem 0', // rounded-r-lg
    fontStyle: 'italic',
    color: '#374151'
  },

  CODE: {
    INLINE: {
      backgroundColor: '#f3f4f6', // bg-gray-100
      paddingLeft: '0.5rem', // px-2
      paddingRight: '0.5rem',
      paddingTop: '0.25rem', // py-1
      paddingBottom: '0.25rem',
      borderRadius: '0.25rem', // rounded
      fontSize: '0.875rem', // text-sm
      fontFamily: 'ui-monospace, SFMono-Regular, "SF Mono", Monaco, Consolas, "Liberation Mono", "Courier New", monospace',
      color: '#1f2937' // text-gray-800
    },
    BLOCK: {
      backgroundColor: '#f3f4f6',
      padding: '1rem', // p-4
      borderRadius: '0.5rem', // rounded-lg
      overflowX: 'auto',
      marginTop: '1rem', // my-4
      marginBottom: '1rem',
      border: '1px solid #d1d5db'
    }
  },

  // Figure captions
  CAPTION: {
    marginTop: '0.5rem', // mt-2
    fontSize: '0.875rem', // text-sm
    color: '#6b7280', // text-gray-500
    fontStyle: 'italic',
    textAlign: 'center'
  }
} as const;

// CSS generation helpers
export function generateInlineStyles(element: keyof typeof BLOG_STYLING.TEXT | 'h1' | 'h2' | 'h3' | 'h4' | 'p' | 'blockquote' | 'code'): string {
  const styles: Record<string, any> = {};
  
  switch (element) {
    case 'h1':
      Object.assign(styles, BLOG_STYLING.TYPOGRAPHY.H1);
      break;
    case 'h2':
      Object.assign(styles, BLOG_STYLING.TYPOGRAPHY.H2);
      break;
    case 'h3':
      Object.assign(styles, BLOG_STYLING.TYPOGRAPHY.H3);
      break;
    case 'h4':
      Object.assign(styles, BLOG_STYLING.TYPOGRAPHY.H4);
      break;
    case 'p':
      Object.assign(styles, BLOG_STYLING.TEXT.PARAGRAPH);
      break;
    case 'blockquote':
      Object.assign(styles, BLOG_STYLING.BLOCKQUOTE);
      break;
    case 'code':
      Object.assign(styles, BLOG_STYLING.CODE.INLINE);
      break;
  }

  return Object.entries(styles)
    .map(([key, value]) => {
      const cssKey = key.replace(/([A-Z])/g, '-$1').toLowerCase();
      return `${cssKey}: ${value}`;
    })
    .join('; ');
}

// Convert pixel/rem values to points for Word documents (1 point = 1.33 pixels)
export function pxToPoints(px: string | number): number {
  const pxValue = typeof px === 'string' ? parseFloat(px.replace('px', '').replace('rem', '').replace('em', '')) : px;
  if (typeof px === 'string' && px.includes('rem')) {
    return (pxValue * 16) / 1.33; // Convert rem to px then to points
  }
  return pxValue / 1.33;
}

// Convert CSS color hex to RGB values for Word documents
export function hexToRgb(hex: string): { r: number; g: number; b: number } | null {
  const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  return result ? {
    r: parseInt(result[1], 16),
    g: parseInt(result[2], 16),
    b: parseInt(result[3], 16)
  } : null;
}