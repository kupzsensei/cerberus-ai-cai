import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

const MarkdownRenderer = ({ content, ...props }) => {
  // Clean the content by removing <think>...</think> blocks and trimming whitespace.
  const cleanedContent = content ? content.replace(/[\s\S]*?<\/think>/g, "").trim() : "";

  return (
    <ReactMarkdown remarkPlugins={[remarkGfm]} {...props}>
      {cleanedContent}
    </ReactMarkdown>
  );
};

export default MarkdownRenderer;