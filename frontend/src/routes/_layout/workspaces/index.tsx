import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { createFileRoute, Link } from "@tanstack/react-router"
import { useState } from "react"
import { OperationsService } from "@/client"
import {
  ErrorNotice,
  PageTitle,
  StatusBadge,
} from "@/components/Operations/shared"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"

export const Route = createFileRoute("/_layout/workspaces/")({
  component: Workspaces,
  head: () => ({ meta: [{ title: "Workspaces | Avrixo AI SaaS" }] }),
})

function Workspaces() {
  const cache = useQueryClient()
  const [name, setName] = useState("")
  const [slug, setSlug] = useState("")
  const [offset, setOffset] = useState(0)
  const list = useQuery({
    queryKey: ["operations", "workspaces", offset],
    queryFn: async () =>
      (await OperationsService.listWorkspaces({ query: { limit: 25, offset } }))
        .data,
  })
  const create = useMutation({
    mutationFn: () =>
      OperationsService.createWorkspace({ body: { name, slug } }),
    onSuccess: async () => {
      setName("")
      setSlug("")
      await cache.invalidateQueries({ queryKey: ["operations"] })
    },
  })
  return (
    <div className="space-y-8">
      <PageTitle
        title="Workspaces"
        subtitle="Separate your teams, workflows, and execution history."
      />
      <form
        onSubmit={(e) => {
          e.preventDefault()
          create.mutate()
        }}
        className="grid items-end gap-4 rounded-xl border p-6 md:grid-cols-[1fr_1fr_auto]"
      >
        <div className="space-y-2">
          <Label htmlFor="workspace-name">Workspace name</Label>
          <Input
            id="workspace-name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            maxLength={100}
            required
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="workspace-slug">Workspace slug</Label>
          <Input
            id="workspace-slug"
            value={slug}
            onChange={(e) => setSlug(e.target.value)}
            pattern="[a-z0-9]+(-[a-z0-9]+)*"
            minLength={3}
            maxLength={63}
            placeholder="support-operations"
            required
          />
        </div>
        <Button type="submit" disabled={create.isPending}>
          {create.isPending ? "Creating…" : "Create workspace"}
        </Button>
      </form>
      <ErrorNotice error={create.error || list.error} />
      {list.isPending ? (
        <p role="status">Loading workspaces…</p>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {list.data?.map((w) => (
            <Link
              className="rounded-xl border p-6 transition-colors hover:bg-muted/40"
              key={w.id}
              to="/workspaces/$workspaceId"
              params={{ workspaceId: w.id }}
            >
              <div className="flex items-center justify-between gap-2">
                <h2 className="text-xl font-semibold">{w.name}</h2>
                <StatusBadge status={w.role} />
              </div>
              <p className="mt-2 text-sm text-muted-foreground">/{w.slug}</p>
              <p className="mt-6 text-xs text-muted-foreground">
                {w.daily_execution_limit} executions per UTC day ·{" "}
                {w.max_concurrent_executions} concurrent
              </p>
            </Link>
          ))}
        </div>
      )}
      {list.data?.length === 0 && (
        <p className="rounded-xl border border-dashed p-10 text-center text-muted-foreground">
          No workspaces on this page. Create one to begin.
        </p>
      )}
      <div className="flex gap-3">
        <Button
          variant="outline"
          disabled={offset === 0}
          onClick={() => setOffset(Math.max(0, offset - 25))}
        >
          Previous
        </Button>
        <Button
          variant="outline"
          disabled={(list.data?.length ?? 0) < 25}
          onClick={() => setOffset(offset + 25)}
        >
          Next
        </Button>
      </div>
    </div>
  )
}
