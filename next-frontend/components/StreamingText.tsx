"use client";

interface StreamingTextProps {
  content: string;
  showCursor?: boolean;
}

export default function StreamingText({
  content,
  showCursor = true,
}: StreamingTextProps) {
  if (!content && showCursor) {
    return (
      <div className="flex items-center gap-1 py-1">
        <span className="typing-dot" />
        <span className="typing-dot animation-delay-150" />
        <span className="typing-dot animation-delay-300" />
      </div>
    );
  }

  return (
    <p className="whitespace-pre-wrap text-[15px] leading-relaxed">
      {content}
      {showCursor && (
        <span className="stream-cursor ml-px inline-block h-[1.1em] w-[2px] translate-y-[2px] bg-green-500 align-text-bottom" />
      )}
    </p>
  );
}
