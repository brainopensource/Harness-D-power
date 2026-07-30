import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { App } from "./App.js";

describe("App shell", () => {
  it("renders SAGIHA", () => {
    render(<App />);
    expect(screen.getByText("SAGIHA")).toBeInTheDocument();
  });
});
