type ButtonProps = {
  label: string;
  onClick: () => void;
  disabled?: boolean;
  variant?: string;
};

export default function Button({
  label,
  onClick,
  disabled,
  variant
}: ButtonProps) {
  const className =
    variant === "outline"
      ? "font-semibold border-2 border-green-700 text-green-700 px-6 py-3 rounded-full"
      : "font-semibold bg-green-700 text-white px-6 py-3 rounded-full";
  return (
    <button onClick={onClick} className={className} disabled={disabled}>
      {label}
    </button>
  );
}
