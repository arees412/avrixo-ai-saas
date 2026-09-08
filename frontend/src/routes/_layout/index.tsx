import { createFileRoute, Link } from "@tanstack/react-router"
import { MetricsGrid, PageTitle } from "@/components/Operations/shared"
import { Button } from "@/components/ui/button"
import useAuth from "@/hooks/useAuth"

export const Route = createFileRoute("/_layout/")({
  component: Dashboard,
  head: () => ({ meta: [{ title: "Dashboard | Avrixo AI SaaS" }] }),
})

function Dashboard() {
  const { user } = useAuth()
  return (
    <div className="space-y-8">
      <PageTitle
        title="Operations dashboard"
        subtitle={`Welcome, ${user?.full_name || user?.email || "back"}. Configure repeatable AI work and review what happened.`}
        action={
          <Button asChild>
            <Link to="/workspaces">Open workspaces</Link>
          </Button>
        }
      />
      <MetricsGrid />
      <section className="grid gap-6 lg:grid-cols-2">
        <div className="rounded-xl border p-6">
          <h2 className="text-lg font-semibold">
            From task to traceable result
          </h2>
          <ol className="mt-4 list-decimal space-y-3 pl-5 text-sm text-muted-foreground">
            <li>Create a workspace and add your team.</li>
            <li>
              Define a workflow with a model, instructions, and output limit.
            </li>
            <li>Run a task and inspect its output, status, and usage.</li>
          </ol>
        </div>
        <div className="rounded-xl border p-6">
          <h2 className="text-lg font-semibold">Your workspace identity</h2>
          <p className="mt-3 text-sm text-muted-foreground">
            Share this member ID with a workspace owner to be added to their
            team.
          </p>
          <code className="mt-4 block break-all rounded-md bg-muted p-3 text-xs">
            {user?.id}
          </code>
        </div>
      </section>
      <p className="text-xs text-muted-foreground">
        Avrixo customization built on FastAPI’s Full Stack FastAPI Template. See
        repository attribution for the inherited foundation.
      </p>
    </div>
  )
}
