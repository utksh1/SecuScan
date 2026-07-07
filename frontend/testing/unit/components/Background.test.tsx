import React from 'react'
import { render } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import Background from '../../../src/components/Background'

describe('Background Component', () => {
  it('renders without crashing with default props', () => {
    const { container } = render(<Background />)
    const wrapper = container.querySelector('.background')
    expect(wrapper).toBeInTheDocument()
    expect(wrapper).toHaveClass('background--idle')
  })

  it('renders with different state props', () => {
    const { container: activeContainer } = render(<Background state="active" />)
    expect(activeContainer.querySelector('.background')).toHaveClass('background--active')

    const { container: errorContainer } = render(<Background state="error" />)
    expect(errorContainer.querySelector('.background')).toHaveClass('background--error')
  })

  it('asserts decorative container and layers are aria-hidden', () => {
    const { container } = render(<Background />)

    // The main wrapper should be aria-hidden since it is decorative background
    const wrapper = container.querySelector('.background')
    expect(wrapper).toHaveAttribute('aria-hidden', 'true')

    // Confirm that the decorative internal elements exist as well
    expect(container.querySelector('.background-grid')).toBeInTheDocument()
    expect(container.querySelector('.background-scan')).toBeInTheDocument()
    expect(container.querySelector('.background-lines')).toBeInTheDocument()
  })
})
