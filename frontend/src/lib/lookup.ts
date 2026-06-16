import { useQuery } from '@tanstack/react-query'
import { listCompanies } from './api'
import { cik10 } from './format'

/** Resolve the warehouse company id for a CIK (exact filter), cached. */
export function useCompanyIdByCik(cik: string) {
  const padded = cik10(cik)
  return useQuery({
    queryKey: ['company-id-by-cik', padded],
    queryFn: async () => {
      const res = await listCompanies({ cik: padded })
      return res.results[0]?.id ?? null
    },
    enabled: !!cik,
    staleTime: 10 * 60 * 1000,
  })
}
