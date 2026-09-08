import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { useState } from "react"
import { OperationsService, type WorkspacePublic } from "@/client"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { ErrorNotice, StatusBadge } from "./shared"

export function Members({ workspace }: { workspace: WorkspacePublic }) {
  const cache = useQueryClient()
  const [userId, setUserId] = useState("")
  const [role, setRole] = useState<"member" | "admin">("member")
  const [offset, setOffset] = useState(0)
  const members = useQuery({
    queryKey: ["operations", "members", workspace.id, offset],
    queryFn: async () =>
      (
        await OperationsService.listMembers({
          path: { workspace_id: workspace.id },
          query: { offset, limit: 25 },
        })
      ).data,
  })
  const save = useMutation({
    mutationFn: () =>
      OperationsService.setMember({
        path: { workspace_id: workspace.id },
        body: { user_id: userId, role },
      }),
    onSuccess: async () => {
      setUserId("")
      await cache.invalidateQueries({ queryKey: ["operations"] })
    },
  })
  const remove = useMutation({
    mutationFn: (id: string) =>
      OperationsService.removeMember({
        path: { workspace_id: workspace.id, user_id: id },
      }),
    onSuccess: () => cache.invalidateQueries({ queryKey: ["operations"] }),
  })
  return (
    <section className="space-y-5">
      <h2 className="text-xl font-semibold">Workspace members</h2>
      <p className="text-sm text-muted-foreground">
        Members can run workflows and read workspace outputs. Admins manage
        workflows and members. Owners manage admin roles and limits.
      </p>
      {workspace.role !== "member" && (
        <form
          onSubmit={(e) => {
            e.preventDefault()
            save.mutate()
          }}
          className="flex flex-wrap items-end gap-3 rounded-lg border p-4"
        >
          <div className="min-w-64 flex-1 space-y-2">
            <Label htmlFor="member-id">Existing user ID</Label>
            <Input
              id="member-id"
              value={userId}
              onChange={(e) => setUserId(e.target.value)}
              placeholder="Member ID from their dashboard"
              required
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="member-role">Role</Label>
            <select
              className="h-10 rounded-md border bg-background px-3"
              id="member-role"
              value={role}
              onChange={(e) =>
                setRole(e.target.value === "admin" ? "admin" : "member")
              }
            >
              <option value="member">Member</option>
              {workspace.role === "owner" && (
                <option value="admin">Admin</option>
              )}
            </select>
          </div>
          <Button disabled={save.isPending}>Add or update member</Button>
        </form>
      )}
      <ErrorNotice error={members.error || save.error || remove.error} />
      <div className="divide-y rounded-lg border">
        {members.data?.map((m) => (
          <div
            key={m.user_id}
            className="flex flex-wrap items-center justify-between gap-3 p-4"
          >
            <code className="break-all text-xs">{m.user_id}</code>
            <div className="flex items-center gap-3">
              <StatusBadge status={m.role} />
              {m.role !== "owner" &&
                (workspace.role === "owner" ||
                  (workspace.role === "admin" && m.role === "member")) && (
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={remove.isPending}
                    onClick={() => remove.mutate(m.user_id)}
                  >
                    Remove
                  </Button>
                )}
            </div>
          </div>
        ))}
      </div>
      <div className="flex gap-3">
        <Button
          variant="outline"
          disabled={!offset}
          onClick={() => setOffset(offset - 25)}
        >
          Previous members
        </Button>
        <Button
          variant="outline"
          disabled={(members.data?.length ?? 0) < 25}
          onClick={() => setOffset(offset + 25)}
        >
          Next members
        </Button>
      </div>
    </section>
  )
}
