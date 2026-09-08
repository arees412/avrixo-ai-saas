import { useQuery } from "@tanstack/react-query"
import { createFileRoute, Link } from "@tanstack/react-router"
import { OperationsService } from "@/client"
import {
  ErrorNotice,
  PageTitle,
  StatusBadge,
} from "@/components/Operations/shared"

export const Route = createFileRoute("/_layout/executions/$executionId")({
  component: ExecutionPage,
  head: () => ({ meta: [{ title: "Execution detail | Avrixo AI SaaS" }] }),
})

function ExecutionPage() {
  const { executionId } = Route.useParams()
  const result = useQuery({
    queryKey: ["operations", "execution", executionId],
    queryFn: async () =>
      (
        await OperationsService.readExecution({
          path: { execution_id: executionId },
        })
      ).data,
    refetchInterval: (query) =>
      ["pending", "running"].includes(query.state.data?.status ?? "")
        ? 2000
        : false,
  })
  if (result.isPending) return <p role="status">Loading execution…</p>
  if (result.isError) return <ErrorNotice error={result.error} />
  const e = result.data
  return (
    <div className="space-y-7">
      <Link
        className="text-sm text-muted-foreground hover:underline"
        to="/workspaces/$workspaceId"
        params={{ workspaceId: e.workspace_id }}
      >
        ← Workspace history
      </Link>
      <PageTitle
        title="Execution detail"
        subtitle={`${new Date(e.created_at).toLocaleString()} · ${e.model}`}
        action={<StatusBadge status={e.status} />}
      />
      <dl className="grid gap-5 rounded-xl border p-6 sm:grid-cols-2 lg:grid-cols-4">
        {[
          ["Prompt tokens", e.prompt_tokens],
          ["Completion tokens", e.completion_tokens],
          ["Total tokens", e.total_tokens],
          ["Latency (ms)", e.latency_ms],
        ].map(([label, value]) => (
          <div key={label}>
            <dt className="text-sm text-muted-foreground">{label}</dt>
            <dd className="mt-2 text-xl font-semibold">
              {value ?? "Unreported"}
            </dd>
          </div>
        ))}
      </dl>
      {e.error_message && (
        <p
          role="alert"
          className="rounded-lg border border-destructive/40 p-4 text-destructive"
        >
          Execution failed: {e.error_message.split("_").join(" ")}. Review the
          provider configuration before starting a new run.
        </p>
      )}
      <div className="grid gap-6 lg:grid-cols-2">
        <section className="rounded-xl border p-6">
          <h2 className="text-lg font-semibold">Input</h2>
          <pre className="mt-4 whitespace-pre-wrap break-words font-sans text-sm">
            {e.input}
          </pre>
        </section>
        <section className="rounded-xl border p-6">
          <h2 className="text-lg font-semibold">Output</h2>
          <pre className="mt-4 whitespace-pre-wrap break-words font-sans text-sm">
            {e.output ??
              (["pending", "running"].includes(e.status)
                ? "Waiting for completion…"
                : "No output was stored.")}
          </pre>
        </section>
      </div>
      <p className="break-all text-xs text-muted-foreground">
        Execution {e.id} · {e.provider} · Started by{" "}
        {e.created_by ?? "deleted user"}
      </p>
      <Link
        className="text-sm text-primary hover:underline"
        to="/workflows/$workflowId"
        params={{ workflowId: e.workflow_id }}
      >
        Open workflow
      </Link>
    </div>
  )
}
