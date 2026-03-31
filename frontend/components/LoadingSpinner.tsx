export function LoadingSpinner({ size = 'md' }: { size?: 'sm' | 'md' | 'lg' }) {
  const sizeClasses = {
    sm: 'h-4 w-4',
    md: 'h-8 w-8',
    lg: 'h-12 w-12',
  };

  return (
    <div className="flex items-center justify-center p-8">
      <div className={`animate-spin rounded-full border-2 border-muted border-t-primary ${sizeClasses[size]}`} />
    </div>
  );
}

export function LoadingPage() {
  return (
    <div className="flex items-center justify-center min-h-[400px]">
      <div className="text-center">
        <LoadingSpinner size="lg" />
        <p className="mt-4 text-muted-foreground">Loading...</p>
      </div>
    </div>
  );
}

export function SkeletonCard() {
  return (
    <div className="rounded-xl border border-border bg-card p-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div className="space-y-2 flex-1">
          <div className="skeleton h-3 w-24 rounded" />
          <div className="skeleton h-8 w-16 rounded" />
        </div>
        <div className="skeleton h-12 w-12 rounded-xl" />
      </div>
    </div>
  );
}

export function SkeletonTable({ rows = 5 }: { rows?: number }) {
  return (
    <div className="rounded-xl border border-border bg-card animate-fade-in">
      <div className="p-4 border-b border-border">
        <div className="skeleton h-5 w-40 rounded" />
      </div>
      <div className="divide-y divide-border">
        {Array.from({ length: rows }).map((_, i) => (
          <div key={i} className="flex items-center gap-4 p-4">
            <div className="skeleton h-4 w-1/4 rounded" />
            <div className="skeleton h-4 w-1/3 rounded" />
            <div className="skeleton h-6 w-16 rounded-full" />
            <div className="skeleton h-4 w-20 rounded ml-auto" />
          </div>
        ))}
      </div>
    </div>
  );
}

export function SkeletonDashboard() {
  return (
    <div className="space-y-8 animate-fade-in">
      <div className="flex items-center justify-between">
        <div className="space-y-2">
          <div className="skeleton h-8 w-40 rounded" />
          <div className="skeleton h-4 w-64 rounded" />
        </div>
        <div className="skeleton h-10 w-36 rounded-xl" />
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {Array.from({ length: 4 }).map((_, i) => (
          <SkeletonCard key={i} />
        ))}
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <SkeletonTable rows={4} />
        <SkeletonTable rows={4} />
      </div>
    </div>
  );
}
