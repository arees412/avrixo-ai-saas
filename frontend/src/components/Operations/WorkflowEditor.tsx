import { useMutation, useQueryClient } from "@tanstack/react-query"
import { useState } from "react"
import {
  OperationsService,
  type WorkflowPublic,
  type WorkflowWrite,
} from "@/client"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { ErrorNotice } from "./shared"

export function WorkflowEditor({
  workspaceId,
  workflow,
  defaultModel,
  onDone,
}: {
  workspaceId: string
  workflow?: WorkflowPublic
  defaultModel?: string
  onDone: () => void
}) {
  const cache = useQueryClient()
  const [form, setForm] = useState<WorkflowWrite>({
    name: workflow?.name ?? "",
    description: workflow?.description ?? "",
    system_prompt: workflow?.system_prompt ?? "",
    model: workflow?.model ?? defaultModel ?? "",
    provider: "openai-compatible",
    temperature: workflow?.temperature ?? 0.7,
    max_output_tokens: workflow?.max_output_tokens ?? 1024,
    status: workflow?.status ?? "active",
  })
  const save = useMutation({
    mutationFn: () =>
      workflow
        ? OperationsService.updateWorkflow({
            path: { workflow_id: workflow.id },
            body: form,
          })
        : OperationsService.createWorkflow({
            path: { workspace_id: workspaceId },
            body: form,
          }),
    onSuccess: async () => {
      await cache.invalidateQueries({ queryKey: ["operations"] })
      onDone()
    },
  })
  return (
    <form
      onSubmit={(e) => {
        e.preventDefault()
        save.mutate()
      }}
      className="space-y-5 rounded-xl border p-6"
    >
      <h2 className="text-xl font-semibold">
        {workflow ? "Edit workflow" : "Create workflow"}
      </h2>
      <ErrorNotice error={save.error} />
      <div className="grid gap-5 md:grid-cols-2">
        <div className="space-y-2">
          <Label htmlFor="workflow-name">Workflow name</Label>
          <Input
            id="workflow-name"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            maxLength={100}
            required
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="workflow-model">Model</Label>
          <Input
            id="workflow-model"
            value={form.model}
            onChange={(e) => setForm({ ...form, model: e.target.value })}
            maxLength={120}
            required
          />
        </div>
      </div>
      <div className="space-y-2">
        <Label htmlFor="workflow-description">Description</Label>
        <Input
          id="workflow-description"
          value={form.description}
          onChange={(e) => setForm({ ...form, description: e.target.value })}
          maxLength={1000}
        />
      </div>
      <div className="space-y-2">
        <Label htmlFor="workflow-system">System instructions</Label>
        <Textarea
          id="workflow-system"
          value={form.system_prompt}
          onChange={(e) => setForm({ ...form, system_prompt: e.target.value })}
          rows={6}
          maxLength={16000}
          required
        />
      </div>
      <div className="grid gap-5 md:grid-cols-3">
        <div className="space-y-2">
          <Label htmlFor="workflow-provider">Provider</Label>
          <select
            className="h-10 w-full rounded-md border bg-background px-3"
            id="workflow-provider"
            value={form.provider}
            disabled
          >
            <option value="openai-compatible">OpenAI compatible</option>
          </select>
        </div>
        <div className="space-y-2">
          <Label htmlFor="workflow-temperature">Temperature</Label>
          <Input
            id="workflow-temperature"
            type="number"
            min={0}
            max={2}
            step={0.1}
            value={form.temperature}
            onChange={(e) =>
              setForm({ ...form, temperature: Number(e.target.value) })
            }
            required
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="workflow-tokens">Output token limit</Label>
          <Input
            id="workflow-tokens"
            type="number"
            min={1}
            max={8192}
            value={form.max_output_tokens}
            onChange={(e) =>
              setForm({ ...form, max_output_tokens: Number(e.target.value) })
            }
            required
          />
        </div>
      </div>
      <div className="space-y-2">
        <Label htmlFor="workflow-status">Status</Label>
        <select
          className="h-10 w-full rounded-md border bg-background px-3"
          id="workflow-status"
          value={form.status}
          onChange={(e) =>
            setForm({
              ...form,
              status: e.target.value === "active" ? "active" : "disabled",
            })
          }
        >
          <option value="active">Active</option>
          <option value="disabled">Disabled</option>
        </select>
      </div>
      <p className="text-xs text-muted-foreground">
        The deployment operator configures the endpoint and credentials.
        Workspaces select the model and generation settings.
      </p>
      <div className="flex gap-3">
        <Button type="submit" disabled={save.isPending}>
          {save.isPending ? "Saving…" : "Save workflow"}
        </Button>
        <Button type="button" variant="outline" onClick={onDone}>
          Cancel
        </Button>
      </div>
    </form>
  )
}
