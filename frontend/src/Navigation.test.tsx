import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, test } from "vitest";

import { Navigation } from "./Navigation";

afterEach(cleanup);

test("citizen navigation exposes the existing hash routes and active state", () => {
  render(<Navigation active="citizen" />);

  expect(screen.getByRole("link", { name: "Citizen Reporting" })).toHaveAttribute("href", "#/");
  expect(screen.getByRole("link", { name: "Operator Console" })).toHaveAttribute("href", "#/operator");
  expect(screen.getByRole("link", { name: "Citizen Reporting" })).toHaveAttribute("aria-current", "page");
});

test("operator navigation marks the operator destination as current", () => {
  render(<Navigation active="operator" />);

  expect(screen.getByRole("link", { name: "Operator Console" })).toHaveAttribute("aria-current", "page");
});
