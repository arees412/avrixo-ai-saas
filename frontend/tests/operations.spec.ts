import { expect, test } from "@playwright/test"
import { firstSuperuser, firstSuperuserPassword } from "./config"

test.use({ storageState: { cookies: [], origins: [] } })

test("login, create workspace and workflow, execute, inspect history", async ({
  page,
}) => {
  const slug = `e2e-${crypto.randomUUID()}`
  await page.goto("/login")
  await page.getByTestId("email-input").fill(firstSuperuser)
  await page.getByTestId("password-input").fill(firstSuperuserPassword)
  await page.getByRole("button", { name: "Log In", exact: true }).click()
  await expect(
    page.getByRole("heading", { name: "Operations dashboard" }),
  ).toBeVisible()
  await page.getByRole("link", { name: "Open workspaces", exact: true }).click()
  await page.getByLabel("Workspace name", { exact: true }).fill(slug)
  await page.getByLabel("Workspace slug", { exact: true }).fill(slug)
  await page
    .getByRole("button", { name: "Create workspace", exact: true })
    .click()
  await page
    .getByRole("link")
    .filter({ has: page.getByRole("heading", { name: slug, exact: true }) })
    .click()
  await page.getByRole("tab", { name: "AI Workflows", exact: true }).click()
  await page.getByRole("button", { name: "New workflow", exact: true }).click()
  await page.getByLabel("Workflow name", { exact: true }).fill("Support brief")
  await page.getByLabel("Model", { exact: true }).fill("test-model")
  await page
    .getByLabel("System instructions", { exact: true })
    .fill("Write a concise support brief.")
  await page.getByRole("button", { name: "Save workflow", exact: true }).click()
  await page
    .getByRole("link")
    .filter({
      has: page.getByRole("heading", { name: "Support brief", exact: true }),
    })
    .click()
  await page
    .getByLabel("Task input", { exact: true })
    .fill("Organize a customer onboarding request.")
  await page.getByRole("button", { name: "Run workflow", exact: true }).click()
  await expect(
    page.getByRole("heading", { name: "Execution detail", exact: true }),
  ).toBeVisible()
  await expect(
    page.getByText("Test provider: task completed.", { exact: true }),
  ).toBeVisible()
  await expect(page.getByText("completed", { exact: true })).toBeVisible()
  await expect(page.getByText("20", { exact: true })).toBeVisible()
  await page
    .getByRole("link", { name: "← Workspace history", exact: true })
    .click()
  await page
    .getByRole("tab", { name: "Execution History", exact: true })
    .click()
  await expect(
    page.getByText("Organize a customer onboarding request.", { exact: true }),
  ).toBeVisible()
})
