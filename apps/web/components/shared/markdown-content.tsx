"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

type MarkdownContentProps = {
  content: string;
};

export function MarkdownContent({ content }: MarkdownContentProps): React.JSX.Element {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        h2: ({ children }) => (
          <h2 className="mt-8 mb-4 text-xl font-semibold tracking-tight first:mt-0">
            {children}
          </h2>
        ),
        h3: ({ children }) => (
          <h3 className="mt-6 mb-3 text-lg font-medium tracking-tight">{children}</h3>
        ),
        p: ({ children }) => (
          <p className="mb-4 leading-relaxed text-muted-foreground last:mb-0">{children}</p>
        ),
        ul: ({ children }) => (
          <ul className="mb-4 ml-6 list-disc space-y-1 text-muted-foreground">{children}</ul>
        ),
        ol: ({ children }) => (
          <ol className="mb-4 ml-6 list-decimal space-y-1 text-muted-foreground">{children}</ol>
        ),
        li: ({ children }) => <li className="leading-relaxed">{children}</li>,
        table: ({ children }) => (
          <div className="mb-4 overflow-x-auto">
            <table className="w-full text-sm">{children}</table>
          </div>
        ),
        thead: ({ children }) => (
          <thead className="border-b">{children}</thead>
        ),
        th: ({ children }) => (
          <th className="px-3 py-2 text-left font-medium text-muted-foreground">{children}</th>
        ),
        td: ({ children }) => (
          <td className="px-3 py-2 text-muted-foreground">{children}</td>
        ),
        code: ({ children, className }) => {
          const isBlock = className?.startsWith("language-");
          if (isBlock) {
            return (
              <code className={`${className} block`}>{children}</code>
            );
          }
          return (
            <code className="rounded bg-muted px-1.5 py-0.5 font-mono text-sm">{children}</code>
          );
        },
        pre: ({ children }) => (
          <pre className="mb-4 overflow-x-auto rounded-lg bg-muted p-4 font-mono text-sm">
            {children}
          </pre>
        ),
        a: ({ href, children }) => (
          <a
            href={href}
            className="text-primary underline underline-offset-4 hover:text-primary/80"
            target="_blank"
            rel="noopener noreferrer"
          >
            {children}
          </a>
        ),
        hr: () => <hr className="my-6 border-border" />,
        strong: ({ children }) => (
          <strong className="font-semibold text-foreground">{children}</strong>
        ),
        blockquote: ({ children }) => (
          <blockquote className="mb-4 border-l-2 border-border pl-4 italic text-muted-foreground">
            {children}
          </blockquote>
        ),
      }}
    >
      {content}
    </ReactMarkdown>
  );
}
