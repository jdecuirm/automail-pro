export function RouteLoadingSkeleton() {
  return (
    <div className="animate-pulse space-y-4 p-1">
      <div className="h-8 w-48 rounded-md bg-muted" />
      <div className="h-4 w-72 rounded bg-muted" />
      <div className="mt-6 space-y-3">
        {[0, 1, 2].map((i) => (
          <div key={i} className="h-20 rounded-lg bg-muted" />
        ))}
      </div>
    </div>
  );
}
