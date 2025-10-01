export default function SplitLayout({ left, right }) {
  return (
    <div className="flex-1 flex flex-col lg:flex-row gap-6 px-8 py-6 overflow-y-auto">
      <div className="flex-1 min-h-[420px] card overflow-hidden p-0">
        {left}
      </div>
      <aside className="right-rail">
        {Array.isArray(right) ? right : [right]}
      </aside>
    </div>
  );
}
