type ButtonProps = {
  label: string;
  onClick: () => void;
};

export default function Button({ label, onClick }: ButtonProps) {
  return (
    <button
      onClick={onClick}
      className="font-semibold bg-green-700 text-white px-6 py-3 rounded-full"
    >
      {label}
    </button>
  );
}
