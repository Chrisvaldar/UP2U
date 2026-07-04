type ErrorMessageProps = {
  message: string;
  className?: string;
};

/**
 * Render a centered error message when text is present.
 *
 * @param props - Error message and optional extra class names.
 * @returns A red error paragraph, or null when message is empty.
 */
export default function ErrorMessage({ message, className = "" }: ErrorMessageProps) {
  if (!message) return null;

  return (
    <p className={`text-red-600 text-sm text-center ${className}`.trim()}>
      {message}
    </p>
  );
}
