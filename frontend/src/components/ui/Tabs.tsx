import Link from "next/link";

export type TabItem = { label: string; href: string; isActive: boolean };

export function Tabs({ items }: { items: TabItem[] }) {
  return (
    <nav aria-label="Sections" className="flex border-b border-border">
      <ul className="flex w-full">
        {items.map((item) => (
          <li key={item.label} className="flex-1">
            <Link
              href={item.href}
              aria-current={item.isActive ? "page" : undefined}
              className={`flex min-h-11 items-center justify-center px-4 text-sm font-medium ${
                item.isActive ? "border-b-2 border-accent text-foreground" : "text-muted"
              }`}
            >
              {item.label}
            </Link>
          </li>
        ))}
      </ul>
    </nav>
  );
}
