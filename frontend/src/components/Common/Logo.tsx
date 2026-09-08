import { Link } from "@tanstack/react-router"
import { cn } from "@/lib/utils"

export function Logo({
  variant = "full",
  className,
  asLink = true,
}: {
  variant?: "full" | "icon" | "responsive"
  className?: string
  asLink?: boolean
}) {
  const content = (
    <span
      className={cn(
        "inline-flex items-center gap-2 font-semibold tracking-tight",
        className,
      )}
    >
      <span className="flex size-7 items-center justify-center rounded-md bg-primary text-sm text-primary-foreground">
        A
      </span>
      {variant !== "icon" && (
        <span
          className={
            variant === "responsive"
              ? "group-data-[collapsible=icon]:hidden"
              : ""
          }
        >
          Avrixo <span className="font-normal text-muted-foreground">AI</span>
        </span>
      )}
    </span>
  )
  return asLink ? (
    <Link to="/" aria-label="Avrixo AI home">
      {content}
    </Link>
  ) : (
    content
  )
}
