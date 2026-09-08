import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { createFileRoute, Link } from "@tanstack/react-router"
import { useState } from "react"
import { OperationsService } from "@/client"
import { History } from "@/components/Operations/History"
import { Members } from "@/components/Operations/Members"
import {
  ErrorNotice,
  MetricsGrid,
  PageTitle,
  StatusBadge,
} from "@/components/Operations/shared"
import { WorkflowEditor } from "@/components/Operations/WorkflowEditor"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"

export const Route = createFileRoute("/_layout/workspaces/$workspaceId")({
  component: WorkspacePage,
  head: () => ({ meta: [{ title: "Workspace | Avrixo AI SaaS" }] }),
})

function WorkspacePage() {
  const { workspaceId } = Route.useParams()
  const cache = useQueryClient()
  const [editing, setEditing] = useState(false)
  const [offset, setOffset] = useState(0)
  const workspace = useQuery({
    queryKey: ["operations", "workspace", workspaceId],
    queryFn: async () =>
      (
        await OperationsService.readWorkspace({
          path: { workspace_id: workspaceId },
        })
      ).data,
  })
  const flows = useQuery({
    queryKey: ["operations", "workflows", workspaceId, offset],
    queryFn: async () =>
      (
        await OperationsService.listWorkflows({
          path: { workspace_id: workspaceId },
          query: { offset, limit: 25 },
        })
      ).data,
  })
  const providers = useQuery({
    queryKey: ["operations", "providers"],
    queryFn: async () => (await OperationsService.providers()).data,
  })
  const limits = useMutation({
    mutationFn: (body: {
      daily_execution_limit: number
      max_concurrent_executions: number
    }) =>
      OperationsService.updateGovernance({
        path: { workspace_id: workspaceId },
        body,
      }),
    onSuccess: () => cache.invalidateQueries({ queryKey: ["operations"] }),
  })
  if (workspace.isPending) return <p role="status">Loading workspace…</p>
  if (workspace.isError) return <ErrorNotice error={workspace.error} />
  const w = workspace.data
  return (
    <div className="space-y-8">
      <Link
        className="text-sm text-muted-foreground hover:underline"
        to="/workspaces"
      >
        ← Workspaces
      </Link>
      <PageTitle title={w.name} subtitle={`/${w.slug} · ${w.role} access`} />
      <MetricsGrid workspaceId={workspaceId} />
      <Tabs defaultValue="overview">
        <TabsList className="mb-5 flex h-auto flex-wrap justify-start">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="workflows">AI Workflows</TabsTrigger>
          <TabsTrigger value="history">Execution History</TabsTrigger>
          <TabsTrigger value="members">Members</TabsTrigger>
        </TabsList>
        <TabsContent value="overview" className="space-y-5">
          <div className="rounded-xl border p-6">
            <h2 className="text-xl font-semibold">
              Provider & usage governance
            </h2>
            <p className="mt-3 text-sm text-muted-foreground">
              OpenAI-compatible provider:{" "}
              {providers.data?.[0]?.configured
                ? "Configured"
                : "Not configured"}
              . Each run has an output token limit. Daily and concurrent
              execution limits apply to the whole workspace.
            </p>
            <p className="mt-3 text-sm">
              {w.daily_execution_limit} executions per UTC day ·{" "}
              {w.max_concurrent_executions} concurrent
            </p>
            {w.role === "owner" && (
              <form
                className="mt-6 flex flex-wrap items-end gap-4"
                onSubmit={(e) => {
                  e.preventDefault()
                  const data = new FormData(e.currentTarget)
                  limits.mutate({
                    daily_execution_limit: Number(data.get("daily")),
                    max_concurrent_executions: Number(data.get("concurrent")),
                  })
                }}
              >
                <div className="space-y-2">
                  <Label htmlFor="daily-limit">Daily execution limit</Label>
                  <Input
                    id="daily-limit"
                    name="daily"
                    type="number"
                    min={1}
                    max={10000}
                    defaultValue={w.daily_execution_limit}
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="concurrent-limit">
                    Concurrent execution limit
                  </Label>
                  <Input
                    id="concurrent-limit"
                    name="concurrent"
                    type="number"
                    min={1}
                    max={20}
                    defaultValue={w.max_concurrent_executions}
                    required
                  />
                </div>
                <Button disabled={limits.isPending}>Save limits</Button>
              </form>
            )}
            <ErrorNotice error={limits.error || providers.error} />
            {limits.isSuccess && (
              <p role="status" className="mt-3 text-sm">
                Limits saved.
              </p>
            )}
          </div>
        </TabsContent>
        <TabsContent value="workflows" className="space-y-5">
          <div className="flex justify-between gap-3">
            <h2 className="text-xl font-semibold">AI Workflows</h2>
            {w.role !== "member" && (
              <Button onClick={() => setEditing(true)}>New workflow</Button>
            )}
          </div>
          {editing && (
            <WorkflowEditor
              workspaceId={workspaceId}
              defaultModel={providers.data?.[0]?.default_model}
              onDone={() => setEditing(false)}
            />
          )}
          <ErrorNotice error={flows.error} />
          <div className="grid gap-4 md:grid-cols-2">
            {flows.data?.map((f) => (
              <Link
                className="space-y-3 rounded-xl border p-6 hover:bg-muted/40"
                key={f.id}
                to="/workflows/$workflowId"
                params={{ workflowId: f.id }}
              >
                <div className="flex items-center justify-between gap-3">
                  <h3 className="text-lg font-semibold">{f.name}</h3>
                  <StatusBadge status={f.status} />
                </div>
                <p className="text-sm text-muted-foreground">
                  {f.description || "No description"}
                </p>
                <p className="text-xs text-muted-foreground">
                  {f.model} · up to {f.max_output_tokens} output tokens
                </p>
              </Link>
            ))}
          </div>
          {flows.data?.length === 0 && (
            <p className="py-6 text-center text-muted-foreground">
              No workflows on this page. A workspace manager can create one.
            </p>
          )}
          <div className="flex gap-3">
            <Button
              variant="outline"
              disabled={!offset}
              onClick={() => setOffset(offset - 25)}
            >
              Previous workflows
            </Button>
            <Button
              variant="outline"
              disabled={(flows.data?.length ?? 0) < 25}
              onClick={() => setOffset(offset + 25)}
            >
              Next workflows
            </Button>
          </div>
        </TabsContent>
        <TabsContent value="history">
          <History workspaceId={workspaceId} />
        </TabsContent>
        <TabsContent value="members">
          <Members workspace={w} />
        </TabsContent>
      </Tabs>
    </div>
  )
}
