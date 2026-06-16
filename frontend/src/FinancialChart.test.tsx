import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import type { ConceptTimeseriesPoint } from './api'
import FinancialChart from './FinancialChart'

describe('FinancialChart', () => {
  it('shows an empty state when there are no chartable values', () => {
    render(<FinancialChart series={[]} />)
    expect(screen.getByText(/no chartable values/i)).toBeInTheDocument()
  })

  it('renders a labelled chart region when given data', () => {
    const series: ConceptTimeseriesPoint[] = [
      { period_end: '2022-12-31', period_start: '2022-01-01', value: 100, unit: 'USD', dimensions: {} },
      { period_end: '2023-12-31', period_start: '2023-01-01', value: 200, unit: 'USD', dimensions: {} },
    ]
    render(<FinancialChart series={series} label="Revenue" />)
    expect(screen.getByRole('img', { name: /revenue trend chart/i })).toBeInTheDocument()
  })
})
