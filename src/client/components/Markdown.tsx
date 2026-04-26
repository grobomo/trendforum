import { useMemo } from 'react';
import { marked } from 'marked';
import DOMPurify from 'dompurify';

marked.setOptions({
  breaks: true,
  gfm: true,
});

interface MarkdownProps {
  content: string;
  className?: string;
}

export function Markdown({ content, className = '' }: MarkdownProps) {
  const html = useMemo(() => {
    const raw = marked.parse(content, { async: false }) as string;
    return DOMPurify.sanitize(raw, {
      ALLOWED_TAGS: ['p', 'br', 'strong', 'em', 'code', 'pre', 'a', 'ul', 'ol', 'li', 'blockquote', 'h1', 'h2', 'h3', 'del'],
      ALLOWED_ATTR: ['href', 'target', 'rel'],
    });
  }, [content]);

  return (
    <div
      className={`prose prose-invert prose-sm max-w-none
        prose-p:my-1 prose-pre:bg-input prose-pre:border prose-pre:border-border
        prose-code:text-accent prose-code:bg-input prose-code:px-1 prose-code:rounded
        prose-a:text-blue-400 prose-a:no-underline hover:prose-a:underline
        prose-blockquote:border-border prose-blockquote:text-muted
        ${className}`}
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}
