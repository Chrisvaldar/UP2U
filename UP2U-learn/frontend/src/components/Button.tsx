type ButtonProps = {
  label: string;
  onClick: () => void;
  disabled?: boolean;
};

export default function Button({ label, onClick, disabled }: ButtonProps) {
  return (
    <button
      onClick={onClick}
      className="font-semibold bg-green-700 text-white px-6 py-3 rounded-full"
      disabled={disabled}
    >
      {label}
    </button>
  );
}
