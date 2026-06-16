/** Macro economic series (FRED bundles + observations). */
import { useState } from 'react'
import { useBundleObservations, useSeriesBundles } from '../lib/queries'
import { compact, date } from '../lib/format'
import { PageHeader } from '../components/PageHeader'
import {
  Card,
  CardHeader,
  EmptyState,
  IconGlobe,
  Query,
  Segmented,
} from '../components/ui'
import { TrendChart } from '../components/ui/Chart'

export function Macro() {
  const bundles = useSeriesBundles()
  const [picked, setPicked] = useState<string | null>(null)
  // Derive the active slug (default to the first bundle) without a setState effect.
  const slug = picked ?? bundles.data?.results[0]?.slug ?? null

  return (
    <div className="page">
      <PageHeader title="Macro Series" desc="Economic time series (e.g. FRED) registered as bundles, for macro context alongside company financials." />

      <Query q={bundles} isEmpty={(b) => b.results.length === 0} empty={<Card><EmptyState icon={<IconGlobe />} title="No series bundles" message="Load a bundle via load_series_bundle and sync it (FRED_API_KEY required)." /></Card>}>
        {(b) => (
          <div className="col gap-4">
            <Segmented
              value={slug ?? b.results[0].slug}
              options={b.results.map((x) => ({ value: x.slug, label: x.name }))}
              onChange={setPicked}
            />
            {slug && <BundleView slug={slug} />}
          </div>
        )}
      </Query>
    </div>
  )
}

function BundleView({ slug }: { slug: string }) {
  const obs = useBundleObservations(slug)
  return (
    <Query q={obs} isEmpty={(d) => d.observations.length === 0} empty={<Card><EmptyState title="No observations" message="This bundle has no synced observations yet." /></Card>}>
      {(d) => {
        // Group observations by series, sort ascending by date.
        const bySeries = new Map<string, { x: string; y: number | null }[]>()
        for (const o of d.observations) {
          const arr = bySeries.get(o.series) ?? []
          arr.push({ x: o.date, y: Number(o.value) })
          bySeries.set(o.series, arr)
        }
        const series = [...bySeries.entries()].map(([name, pts]) => ({ name, pts: pts.sort((a, b) => a.x.localeCompare(b.x)) }))
        return (
          <div className="grid grid-2">
            {series.map(({ name, pts }, i) => {
              const last = pts[pts.length - 1]
              return (
                <Card key={name}>
                  <CardHeader title={name} sub={last ? `Latest ${compact(last.y)} · ${date(last.x)}` : undefined} />
                  <div className="card-body">
                    <TrendChart height={200} data={pts} color={`var(--viz-${(i % 6) + 1})`} fmt={(v) => compact(v)} />
                  </div>
                </Card>
              )
            })}
          </div>
        )
      }}
    </Query>
  )
}
