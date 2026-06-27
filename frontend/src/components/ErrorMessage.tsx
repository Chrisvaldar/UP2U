type ErrorMessageProps = {
  message: string;
  className?: string;
};

export default function ErrorMessage({ message, className = "" }: ErrorMessageProps) {
  if (!message) return null;

  return (
    <p className={`text-red-600 text-sm text-center ${className}`.trim()}>
      {message}
    </p>
  );
}
