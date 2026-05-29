import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ConfirmModal } from '../../../src/components/ConfirmModal';
import { describe, it, expect, vi, beforeEach } from 'vitest';

describe('ConfirmModal Accessibility', () => {
  const defaultProps = {
    isOpen: true,
    title: 'Test Title',
    message: 'Test Message',
    onConfirm: vi.fn(),
    onCancel: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('focuses on confirm button when modal opens', () => {
    render(<ConfirmModal {...defaultProps} />);
    const confirmButton = screen.getByText('Confirm');
    expect(confirmButton).toHaveFocus();
  });

  it('traps Tab key focus within modal', async () => {
    const user = userEvent.setup();
    render(<ConfirmModal {...defaultProps} />);
    
    const confirmButton = screen.getByText('Confirm');
    const cancelButton = screen.getByText('Cancel');
    
    expect(confirmButton).toHaveFocus();
    
    await user.tab();
    expect(cancelButton).toHaveFocus();
    
    await user.tab();
    expect(confirmButton).toHaveFocus();
  });

  it('closes with Escape key', () => {
    render(<ConfirmModal {...defaultProps} />);
    fireEvent.keyDown(document, { key: 'Escape' });
    expect(defaultProps.onCancel).toHaveBeenCalled();
  });

  it('has correct ARIA attributes', () => {
    render(<ConfirmModal {...defaultProps} />);
    const dialog = screen.getByRole('dialog');
    expect(dialog).toHaveAttribute('aria-modal', 'true');
    expect(dialog).toHaveAttribute('aria-labelledby', 'modal-title');
    expect(dialog).toHaveAttribute('aria-describedby', 'modal-description');
  });

  it('does not confirm with Enter when focus is on a button', async () => {
    const user = userEvent.setup();
    render(<ConfirmModal {...defaultProps} />);
    
    const cancelButton = screen.getByText('Cancel');
    await user.tab();
    expect(cancelButton).toHaveFocus();
    
    fireEvent.keyDown(cancelButton, { key: 'Enter' });
    expect(defaultProps.onConfirm).not.toHaveBeenCalled();
  });
});
