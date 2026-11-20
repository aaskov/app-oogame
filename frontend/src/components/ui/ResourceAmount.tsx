export type ResourceKind = "metal" | "crystal" | "deuterium" | "energy";

const COLOR_CLASS: Record<ResourceKind, string> = {
  metal: "text-metal",
  crystal: "text-crystal",
  deuterium: "text-deuterium",
  energy: "text-energy",
};

function format(value: number) {
  return value.toLocaleString("en-US");
}

export function ResourceAmount({
  kind,
  label,
  amount,
  capacity,
}: {
  kind: ResourceKind;
  label: string;
  amount: number;
  capacity: number;
}) {
  const isFull = amount >= capacity;
  return (
    <div className="flex flex-col items-center gap-0.5">
      <dt className={`text-xs font-medium ${COLOR_CLASS[kind]}`}>{label}</dt>
      <dd className="text-sm font-semibold text-foreground">
        {format(amount)} / {format(capacity)}
      </dd>
      {isFull && <dd className="text-[10px] font-medium text-energy">Full</dd>}
    </div>
  );
}
