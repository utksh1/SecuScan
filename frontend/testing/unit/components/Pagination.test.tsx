import { render, screen } from "@testing-library/react";
import Pagination from "../../../src/components/Pagination";

describe("Pagination", () => {
  const defaultProps = {
    page: 1,
    total: 100,
    limit: 10,
    loading: false,
    onPrev: vi.fn(),
    onNext: vi.fn(),
  };

  // Range math tests
  it("shows correct start and end for first page", () => {
    render(<Pagination {...defaultProps} page={1} total={100} limit={10} />);
    expect(screen.getByText("1–10")).toBeInTheDocument();
  });

  it("shows correct start and end for middle page", () => {
    render(<Pagination {...defaultProps} page={3} total={100} limit={10} />);
    expect(screen.getByText("21–30")).toBeInTheDocument();
  });

  it("shows correct end on last page with partial results", () => {
    render(<Pagination {...defaultProps} page={5} total={42} limit={10} />);
    expect(screen.getByText("41–42")).toBeInTheDocument();
  });

  it("shows 0 start and 0 end when total is 0", () => {
    render(<Pagination {...defaultProps} page={1} total={0} limit={10} />);
    expect(screen.getByText("0–0")).toBeInTheDocument();
  });

  // Disabled state tests
  it("disables prev button on first page", () => {
    render(<Pagination {...defaultProps} page={1} />);
    expect(screen.getByText("Prev_Page").closest("button")).toBeDisabled();
  });

  it("enables next button when not on last page", () => {
    render(<Pagination {...defaultProps} page={1} total={100} limit={10} />);
    expect(screen.getByText("Next_Page").closest("button")).not.toBeDisabled();
  });

  it("disables next button on last page", () => {
    render(<Pagination {...defaultProps} page={10} total={100} limit={10} />);
    expect(screen.getByText("Next_Page").closest("button")).toBeDisabled();
  });

  it("disables both buttons when total is 0", () => {
    render(<Pagination {...defaultProps} page={1} total={0} limit={10} />);
    expect(screen.getByText("Prev_Page").closest("button")).toBeDisabled();
    expect(screen.getByText("Next_Page").closest("button")).toBeDisabled();
  });

  it("disables both buttons when loading", () => {
    render(<Pagination {...defaultProps} loading={true} />);
    expect(screen.getByText("Prev_Page").closest("button")).toBeDisabled();
    expect(screen.getByText("Next_Page").closest("button")).toBeDisabled();
  });
})
