import { useQuery } from "@tanstack/react-query"
import { Link } from "@tanstack/react-router"
import { useState } from "react"
import { OperationsService } from "@/client"
import { Button } from "@/components/ui/button"
import { ErrorNotice, StatusBadge } from "./shared"

export function History({ workspaceId }: { workspaceId: string }) {
  const [offset, setOffset] = useState(0)
  const history = useQuery({
    queryKey: ["operations", "history", workspaceId, offset],
    queryFn: async () =>
      (
        await OperationsService.listExecutions({
          path: { workspace_id: workspaceId },
          query: { limit: 25, offset },
        })
      ).data,
    refetchInterval: 5000,
  })
  return (
    <section className="space-y-5">
      <h2 className="text-xl font-semibold">Execution history</h2>
      <ErrorNotice error={history.error} />
      {history.isPending && <p role="status">Loading executions…</p>}
      <div className="divide-y rounded-xl border">
        {history.data?.map((e) => (
          <Link
            key={e.id}
            to="/executions/$executionId"
            params={{ executionId: e.id }}
            className="grid gap-3 p-5 hover:bg-muted/40 md:grid-cols-[1fr_auto_auto]"
          >
            <div>
              <p className="line-clamp-1 font-medium">{e.input}</p>
              <p className="mt-1 text-xs text-muted-foreground">
                {new Date(e.created_at).toLocaleString()} · {e.model}
              </p>
            </div>
            <p className="text-sm text-muted-foreground">
              {e.total_tokens ?? "Unreported"} tokens ·{" "}
              {e.latency_ms === null ? "In progress" : `${e.latency_ms} ms`}
            </p>
            <StatusBadge status={e.status} />
          </Link>
        ))}
      </div>
      {history.data?.length === 0 && (
        <p className="py-8 text-center text-muted-foreground">
          No executions yet on this page.
        </p>
      )}
      <div className="flex gap-3">
        <Button
          variant="outline"
          disabled={!offset}
          onClick={() => setOffset(offset - 25)}
        >
          Previous executions
        </Button>
        <Button
          variant="outline"
          disabled={(history.data?.length ?? 0) < 25}
          onClick={() => setOffset(offset + 25)}
        >
          Next executions
        </Button>
      </div>
    </section>
  )
}
