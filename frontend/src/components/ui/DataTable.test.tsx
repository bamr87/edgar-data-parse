import { render, screen, fireEvent } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { DataTable, type Column } from './DataTable'

type Row = { id: number; name: string; value: number }
const rows: Row[] = [
  { id: 1, name: 'Alpha', value: 30 },
  { id: 2, name: 'Beta', value: 10 },
  { id: 3, name: 'Gamma', value: 20 },
]
const columns: Column<Row>[] = [
  { key: 'name', header: 'Name', render: (r) => r.name },
  { key: 'value', header: 'Value', align: 'right', render: (r) => r.value, sortable: true, sortValue: (r) => r.value },
]

describe('DataTable', () => {
  it('renders rows and headers', () => {
    render(<DataTable rows={rows} columns={columns} rowKey={(r) => r.id} />)
    expect(screen.getByText('Alpha')).toBeInTheDocument()
    expect(screen.getByText('Gamma')).toBeInTheDocument()
    expect(screen.getByText('Value')).toBeInTheDocument()
  })

  it('fires onRowClick', () => {
    const onRowClick = vi.fn()
    render(<DataTable rows={rows} columns={columns} rowKey={(r) => r.id} onRowClick={onRowClick} />)
    fireEvent.click(screen.getByText('Beta'))
    expect(onRowClick).toHaveBeenCalledWith(rows[1])
  })

  it('sorts when a sortable header is clicked', () => {
    render(<DataTable rows={rows} columns={columns} rowKey={(r) => r.id} />)
    fireEvent.click(screen.getByText('Value')) // desc first
    const cells = screen.getAllByRole('cell').map((c) => c.textContent)
    // First data row should be the highest value (30 -> Alpha)
    expect(cells[0]).toBe('Alpha')
  })
})
