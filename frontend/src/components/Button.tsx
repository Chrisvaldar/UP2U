export type ButtonProps = {
  label: string;
  onClick: () => void | Promise<void>;
  disabled?: boolean;
  variant?: "solid" | "outline";
};

/**
 * Styled button with solid or outline variants.
 *
 * @param props - Button label, click handler, disabled state, and variant.
 * @returns A rounded green button element.
 */
export default function Button({
  label,
  onClick,
  disabled,
  variant
}: ButtonProps) {
  const className =
    variant === "outline"
      ? "font-semibold border-2 border-green-700 text-green-700 px-6 py-3 rounded-full disabled:opacity-50 disabled:cursor-not-allowed"
      : "font-semibold bg-green-700 text-white px-6 py-3 rounded-full disabled:opacity-50 disabled:cursor-not-allowed";
  return (
    <button onClick={onClick} className={className} disabled={disabled}>
      {label}
    </button>
  );
}
