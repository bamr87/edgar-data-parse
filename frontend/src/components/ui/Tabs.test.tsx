import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { Tabs } from './Tabs'

const TABS = [
  { key: 'a', label: 'Alpha' },
  { key: 'b', label: 'Beta' },
  { key: 'c', label: 'Gamma' },
]

describe('Tabs', () => {
  it('renders tabs with the right roles + selection', () => {
    render(<Tabs tabs={TABS} value="a" onChange={() => {}} />)
    expect(screen.getByRole('tablist')).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: 'Alpha' })).toHaveAttribute('aria-selected', 'true')
    expect(screen.getByRole('tab', { name: 'Beta' })).toHaveAttribute('aria-selected', 'false')
  })

  it('activates on click', () => {
    const onChange = vi.fn()
    render(<Tabs tabs={TABS} value="a" onChange={onChange} />)
    fireEvent.click(screen.getByRole('tab', { name: 'Gamma' }))
    expect(onChange).toHaveBeenCalledWith('c')
  })

  it('moves with arrow keys (and wraps)', () => {
    const onChange = vi.fn()
    render(<Tabs tabs={TABS} value="a" onChange={onChange} />)
    const list = screen.getByRole('tablist')
    fireEvent.keyDown(list, { key: 'ArrowRight' })
    expect(onChange).toHaveBeenLastCalledWith('b')
    fireEvent.keyDown(list, { key: 'ArrowLeft' }) // from 'a' wraps to last
    expect(onChange).toHaveBeenLastCalledWith('c')
    fireEvent.keyDown(list, { key: 'End' })
    expect(onChange).toHaveBeenLastCalledWith('c')
    fireEvent.keyDown(list, { key: 'Home' })
    expect(onChange).toHaveBeenLastCalledWith('a')
  })

  it('uses a roving tabindex', () => {
    render(<Tabs tabs={TABS} value="b" onChange={() => {}} />)
    expect(screen.getByRole('tab', { name: 'Beta' })).toHaveAttribute('tabindex', '0')
    expect(screen.getByRole('tab', { name: 'Alpha' })).toHaveAttribute('tabindex', '-1')
  })
})
