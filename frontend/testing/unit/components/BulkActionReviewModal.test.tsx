import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import BulkActionReviewModal from "../../../src/components/BulkActionReviewModal";

describe("BulkActionReviewModal", () => {
  const defaultProps = {
    isOpen: true,
    onClose: vi.fn(),
    onConfirm: vi.fn(),
    actionLabel: "Delete",
    selectedCount: 3,
  };

  it("renders modal when isOpen is true", () => {
    render(<BulkActionReviewModal {...defaultProps} />);
    expect(screen.getByRole("dialog", { hidden: true })).toBeInTheDocument();
  });

  it("does not render when isOpen is false", () => {
    render(<BulkActionReviewModal {...defaultProps} isOpen={false} />);
    expect(
      screen.queryByRole("dialog", { hidden: true }),
    ).not.toBeInTheDocument();
  });

  it("shows correct selected count", () => {
    render(<BulkActionReviewModal {...defaultProps} selectedCount={5} />);
    expect(screen.getByText(/5 items/i)).toBeInTheDocument();
  });

  it("calls onConfirm when confirm button clicked", () => {
    const onConfirm = vi.fn();
    render(<BulkActionReviewModal {...defaultProps} onConfirm={onConfirm} />);
    fireEvent.click(screen.getByText(/Yes, Delete/i));
    expect(onConfirm).toHaveBeenCalledTimes(1);
  });

  it("calls onClose when cancel button clicked", () => {
    const onClose = vi.fn();
    render(<BulkActionReviewModal {...defaultProps} onClose={onClose} />);
    fireEvent.click(screen.getByText(/Cancel/i));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("calls onClose when Escape key is pressed", () => {
    const onClose = vi.fn();
    render(<BulkActionReviewModal {...defaultProps} onClose={onClose} />);
    fireEvent.keyDown(screen.getByRole("dialog", { hidden: true }), {
      key: "Escape",
    });
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("shows singular item text for count of 1", () => {
    render(<BulkActionReviewModal {...defaultProps} selectedCount={1} />);
    const desc = screen.getByText((_, element) => {
      return (
        (element?.id === "bulk-action-desc" &&
          element.textContent?.includes("1 item") &&
          !element.textContent?.includes("1 items")) ||
        false
      );
    });
    expect(desc).toBeInTheDocument();
  });
});
