import { useSortable } from "@dnd-kit/react/sortable";

type SortableItemProps = {
  id: string;
  index: number;
};

export default function SortableItem({ id, index }: SortableItemProps) {
  const { ref } = useSortable({ id, index });

  return (
    <div
      ref={ref}
      className="item bg-green-100 text-green-800 text-center px-4 py-2 mb-8 text-xl rounded-full"
    >
      {id}
    </div>
  );
}
