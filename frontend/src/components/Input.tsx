type InputProps = React.InputHTMLAttributes<HTMLInputElement> & {
  placeholder: string;
  value: string;
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
};

/**
 * Rounded text input with shared styling.
 *
 * @param props - Input placeholder, value, onChange, and native input attributes.
 * @returns A styled HTML input element.
 */
export default function Input({
  placeholder,
  value,
  onChange,
  ...props
}: InputProps) {
  return (
    <input
      className="border border-gray-300 rounded-full px-4 py-2 outline-none"
      placeholder={placeholder}
      value={value}
      onChange={onChange}
      {...props}
    />
  );
}
