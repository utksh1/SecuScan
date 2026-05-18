import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import ConfirmationModal from '../components/ConfirmationModal'

describe('ConfirmationModal', () => {
    it('calls onCancel when cancel button clicked', () => {
        const onCancel = vi.fn()

        render(
            <ConfirmationModal
                open={true}
                title="Delete"
                description="Delete item?"
                confirmLabel="Delete"
                onConfirm={() => {}}
                onCancel={onCancel}
            />
        )

        fireEvent.click(screen.getByText('Cancel'))

        expect(onCancel).toHaveBeenCalled()
    })

    it('calls onConfirm when confirm button clicked', () => {
        const onConfirm = vi.fn()

        render(
            <ConfirmationModal
                open={true}
                title="Delete"
                description="Delete item?"
                confirmLabel="Delete"
                onConfirm={onConfirm}
                onCancel={() => {}}
            />
        )

        fireEvent.click(screen.getByText('Delete'))

        expect(onConfirm).toHaveBeenCalled()
    })
})