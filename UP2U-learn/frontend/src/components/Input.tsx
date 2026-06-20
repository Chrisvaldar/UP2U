type InputProps = {
  placeholder: string;
  value: string;
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
};

export default function Input({ placeholder, value, onChange }: InputProps) {
  return (
    <input
      className="border border-gray-300 rounded-full px-4 py-2 outline-none"
      placeholder={placeholder}
      value={value}
      onChange={onChange}
    />
  );
}
