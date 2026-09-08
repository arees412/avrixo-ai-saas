import { useQuery } from "@tanstack/react-query"
import { AxiosError } from "axios"
import type { ReactNode } from "react"
import { OperationsService } from "@/client"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent } from "@/components/ui/card"

export function PageTitle({
  title,
  subtitle,
  action,
}: {
  title: string
  subtitle: string
  action?: ReactNode
}) {
  return (
    <header className="flex flex-wrap items-start justify-between gap-4">
      <div>
        <p className="mb-2 text-xs font-semibold uppercase tracking-widest text-primary">
          Avrixo / AI Operations
        </p>
        <h1 className="text-3xl font-semibold tracking-tight">{title}</h1>
        <p className="mt-2 max-w-2xl text-muted-foreground">{subtitle}</p>
      </div>
      {action}
    </header>
  )
}

export function ErrorNotice({ error }: { error: unknown }) {
  if (!error) return null
  const detail =
    error instanceof AxiosError ? error.response?.data?.detail : null
  return (
    <p
      role="alert"
      className="rounded-lg border border-destructive/40 bg-destructive/5 p-4 text-sm text-destructive"
    >
      {typeof detail === "string"
        ? detail
        : "The request could not be completed. Check your connection and try again."}
    </p>
  )
}

export function StatusBadge({ status }: { status?: string }) {
  return (
    <Badge
      variant={
        status === "failed" || status === "disabled"
          ? "destructive"
          : "secondary"
      }
    >
      {status ?? "unknown"}
    </Badge>
  )
}

export function MetricsGrid({ workspaceId }: { workspaceId?: string }) {
  const stats = useQuery({
    queryKey: ["operations", "metrics", workspaceId],
    queryFn: async () =>
      (
        await OperationsService.metrics({
          query: { workspace_id: workspaceId },
        })
      ).data,
  })
  if (stats.isPending) return <p role="status">Loading activity…</p>
  if (stats.isError) return <ErrorNotice error={stats.error} />
  const d = stats.data
  const items = [
    ["Workflows", d.workflows],
    ["Executions", d.executions],
    ["Successful", d.successful_executions],
    ["Failed", d.failed_executions],
    ["Reported tokens", d.total_tokens],
  ] as const
  return (
    <section aria-label="Workspace activity" className="space-y-3">
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
        {items.map(([label, value]) => (
          <Card key={label}>
            <CardContent className="p-5">
              <p className="text-sm text-muted-foreground">{label}</p>
              <p className="mt-3 text-3xl font-semibold tabular-nums">
                {value.toLocaleString()}
              </p>
            </CardContent>
          </Card>
        ))}
      </div>
      <p className="text-xs text-muted-foreground">
        Database totals across your accessible workspaces. Token usage was
        reported for {d.executions_with_usage} of {d.executions} executions.
      </p>
    </section>
  )
}
