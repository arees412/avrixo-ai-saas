import { useMutation, useQuery } from "@tanstack/react-query"
import { createFileRoute, Link, useNavigate } from "@tanstack/react-router"
import { useState } from "react"
import { OperationsService } from "@/client"
import {
  ErrorNotice,
  PageTitle,
  StatusBadge,
} from "@/components/Operations/shared"
import { WorkflowEditor } from "@/components/Operations/WorkflowEditor"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"

export const Route = createFileRoute("/_layout/workflows/$workflowId")({
  component: WorkflowPage,
  head: () => ({ meta: [{ title: "Run workflow | Avrixo AI SaaS" }] }),
})

function createRequestKey() {
  const bytes = crypto.getRandomValues(new Uint8Array(16))
  return Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0")).join(
    "",
  )
}

function WorkflowPage() {
  const { workflowId } = Route.useParams()
  const navigate = useNavigate()
  const [editing, setEditing] = useState(false)
  const [input, setInput] = useState("")
  const [requestKey, setRequestKey] = useState(createRequestKey)
  const flow = useQuery({
    queryKey: ["operations", "workflow", workflowId],
    queryFn: async () =>
      (
        await OperationsService.readWorkflow({
          path: { workflow_id: workflowId },
        })
      ).data,
  })
  const workspace = useQuery({
    queryKey: ["operations", "workspace", flow.data?.workspace_id],
    enabled: !!flow.data,
    queryFn: async () =>
      (
        await OperationsService.readWorkspace({
          path: { workspace_id: flow.data!.workspace_id },
        })
      ).data,
  })
  const run = useMutation({
    retry: false,
    mutationFn: async () =>
      (
        await OperationsService.executeWorkflow({
          path: { workflow_id: workflowId },
          body: { input, idempotency_key: requestKey },
        })
      ).data,
    onSuccess: (result) =>
      navigate({
        to: "/executions/$executionId",
        params: { executionId: result.id },
      }),
  })
  if (flow.isPending) return <p role="status">Loading workflow…</p>
  if (flow.isError) return <ErrorNotice error={flow.error} />
  const f = flow.data
  return (
    <div className="space-y-7">
      <Link
        className="text-sm text-muted-foreground hover:underline"
        to="/workspaces/$workspaceId"
        params={{ workspaceId: f.workspace_id }}
      >
        ← Workspace
      </Link>
      <PageTitle
        title={f.name}
        subtitle={
          f.description ||
          "Configure a repeatable task, then inspect each result."
        }
        action={
          workspace.data && workspace.data.role !== "member" ? (
            <Button variant="outline" onClick={() => setEditing(!editing)}>
              Edit workflow
            </Button>
          ) : undefined
        }
      />
      {editing ? (
        <WorkflowEditor
          workspaceId={f.workspace_id}
          workflow={f}
          onDone={() => setEditing(false)}
        />
      ) : (
        <>
          <div className="flex flex-wrap gap-3 text-sm">
            <StatusBadge status={f.status} />
            <span>
              {f.provider} / {f.model}
            </span>
            <span className="text-muted-foreground">
              Temperature {f.temperature} · {f.max_output_tokens} output tokens
              maximum
            </span>
          </div>
          <details className="rounded-lg border p-4">
            <summary className="cursor-pointer font-medium">
              System instructions
            </summary>
            <p className="mt-3 whitespace-pre-wrap text-sm text-muted-foreground">
              {f.system_prompt}
            </p>
          </details>
          <form
            className="space-y-4 rounded-xl border p-6"
            onSubmit={(e) => {
              e.preventDefault()
              run.mutate()
            }}
          >
            <h2 className="text-xl font-semibold">Run workflow</h2>
            <Label htmlFor="task-input">Task input</Label>
            <Textarea
              id="task-input"
              placeholder="Describe the task to process…"
              rows={8}
              maxLength={32000}
              required
              disabled={run.isPending}
              value={input}
              onChange={(e) => {
                setInput(e.target.value)
                setRequestKey(createRequestKey())
              }}
            />
            <p className="text-xs text-muted-foreground">
              Input is sent to your configured AI provider and stored with the
              output for workspace members to review.
            </p>
            <ErrorNotice error={run.error || workspace.error} />
            <Button
              type="submit"
              disabled={run.isPending || f.status !== "active"}
            >
              {run.isPending ? "Executing…" : "Run workflow"}
            </Button>
            {run.isPending && (
              <p role="status" className="text-sm text-muted-foreground">
                Waiting for the provider. This may take up to two minutes.
              </p>
            )}
          </form>
        </>
      )}
    </div>
  )
}
